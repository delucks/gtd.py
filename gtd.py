#!/usr/bin/env python
'''entrypoint to gtd.py, written with click'''
import re
import os
import sys
import yaml
import click
import shutil
import requests
import readline  # noqa
import webbrowser
from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenRequestDenied
from todo.input import prompt_for_confirmation, BoardTool, CardTool
from todo.display import Display
from todo.exceptions import GTDException
from todo.misc import Colors, DevNullRedirect, WORKFLOW_TEXT, get_banner, VALID_URL_REGEX
from todo.configuration import Configuration
from todo import __version__

pass_config = click.make_pass_decorator(Configuration)


def filtering_command(f):
    '''Add common options to a click function that will filter Trello cards'''
    f = click.option('-t', '--tags', default=None, help='Filter cards by this comma-separated list of tag names')(f)
    f = click.option('--no-tags', is_flag=True, default=False, help='Only show cards which have no tags')(f)
    f = click.option('-m', '--match', help='Filter cards to this regex on their title', default=None)(f)
    f = click.option('-l', '--listname', help='Only show cards from this list', default=None)(f)
    f = click.option('--attachments', is_flag=True, help='Only show cards which have attachments', default=None)(f)
    f = click.option('--has-due', is_flag=True, help='Only show cards which have due dates', default=None)(f)
    return f


def json_option(f):
    return click.option('-j', '--json', is_flag=True, default=False, help='Output as JSON')(f)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(__version__)
@click.option('-b', '--board', default=None, help='Name of the board to work with for this session')
@click.option('--no-color', is_flag=True, default=False, help='Disable ANSI terminal color?')
@click.option('--no-banner', is_flag=True, default=False, help='Disable banner printing?')
@click.pass_context
def cli(ctx, board, no_color, no_banner):
    '''gtd.py'''
    try:
        config = Configuration.from_file()
    except GTDException:
        click.echo('Could not find a valid config file for gtd.')
        if click.confirm('Would you like to create it interactively?'):
            ctx.invoke(onboard)
            click.secho('Re-run your command', fg='green')
            raise GTDException(0)
        else:
            click.secho('Put your config file in one of the following locations:', fg='red')
            for l in Configuration.all_config_locations():
                print('  ' + l)
            raise
    if board is not None:
        config.board = board
    if no_color:
        config.color = False
    if no_banner:
        config.banner = False
    ctx.color = config.color
    ctx.obj = config


@cli.command()
@click.option('-w', '--workflow', is_flag=True, default=False, help='Show a Getting Things Done workflow')
@click.option('-b', '--banner', is_flag=True, default=False, help='Show a random banner')
def info(workflow, banner):
    '''Learn more about gtd.py'''
    if workflow:
        click.secho(WORKFLOW_TEXT, fg='yellow')
        raise GTDException(0)
    elif banner:
        print(get_banner())
    else:
        print('gtd.py version {c}{0}{r}'.format(__version__, c=Colors.green, r=Colors.reset))
        print('{c}https://github.com/delucks/gtd.py/{r}\nPRs welcome\n'.format(c=Colors.green, r=Colors.reset))


@cli.command()
@click.option('-e', '--edit', is_flag=True, help='Open $EDITOR on the configuration file')
def config(edit):
    '''Show/modify user configuration'''
    if edit:
        try:
            click.edit(filename=Configuration.find_config_file())
        except GTDException:
            # There is no configuration file
            click.secho("Could not find config file! Please run onboard if you haven't already", fg='red')
    else:
        print(Configuration.from_file())


# onboard {{{


@cli.command(short_help='Obtain Trello API credentials')
@click.option('-n', '--no-open', is_flag=True, default=False, help='Do not automatically open URLs in a web browser')
def onboard(no_open, output_path=None):
    '''Obtain Trello API credentials and put them into your config file.
    This is invoked automatically the first time you attempt to do an operation which requires authentication.
    The configuration file is put in an appropriate place for your operating system. If you want to change it later,
    you can use `gtd config -e` to open it in $EDITOR.
    '''
    output_file = output_path or Configuration.suggest_config_location()  # Use platform detection
    user_api_key_url = 'https://trello.com/app-key'
    request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
    authorize_url = 'https://trello.com/1/OAuthAuthorizeToken'
    access_token_url = 'https://trello.com/1/OAuthGetAccessToken'
    # First, open the URL that allows the user to get an auth token. Tell them to copy both into the program
    click.echo('Welcome to gtd.py! To get started, open the following URL in your web browser:')
    click.echo('  ' + user_api_key_url)
    click.echo('When you arrive at that page, log in and copy the "Key" displayed in a text box.')
    if not no_open:
        with DevNullRedirect():
            webbrowser.open_new_tab(user_api_key_url)
    api_key = click.prompt('Please enter the value for "Key"', confirmation_prompt=True)
    click.echo('Now scroll to the bottom of the page and copy the "Secret" shown in a text box.')
    api_secret = click.prompt('Please enter the value for "Secret"', confirmation_prompt=True)
    # Then, work on getting OAuth credentials for the user so they are permanently authorized to use this program
    click.echo('We will now get the OAuth credentials necessary to use this program...')
    # The following code is cannibalized from trello.util.create_oauth_token from the py-trello project.
    # Rewriting because it does not support opening the auth URLs using webbrowser.open and since we're using
    # click, a lot of the input methods used in that script are simplistic compared to what's available to us.
    # Thank you to the original authors!
    '''Step 1: Get a request token. This is a temporary token that is used for
    having the user authorize an access token and to sign the request to obtain
    said access token.'''
    session = OAuth1Session(client_key=api_key, client_secret=api_secret)
    try:
        response = session.fetch_request_token(request_token_url)
    except TokenRequestDenied:
        click.secho('Invalid API key/secret provided: {0} / {1}'.format(api_key, api_secret), fg='red')
        sys.exit(1)
    resource_owner_key, resource_owner_secret = response.get('oauth_token'), response.get('oauth_token_secret')
    '''Step 2: Redirect to the provider. Since this is a CLI script we do not
    redirect. In a web application you would redirect the user to the URL
    below.'''
    user_confirmation_url = '{authorize_url}?oauth_token={oauth_token}&scope={scope}&expiration={expiration}&name={name}'.format(
        authorize_url=authorize_url,
        oauth_token=resource_owner_key,
        expiration='never',
        scope='read,write',
        name='gtd.py'
    )
    click.echo('Visit the following URL in your web browser to authorize gtd.py to access your account:')
    click.echo('  ' + user_confirmation_url)
    if not no_open:
        with DevNullRedirect():
            webbrowser.open_new_tab(user_confirmation_url)
    '''After the user has granted access to you, the consumer, the provider will
    redirect you to whatever URL you have told them to redirect to. You can
    usually define this in the oauth_callback argument as well.'''
    while not click.confirm('Have you authorized gtd.py?', default=False):
        pass
    oauth_verifier = click.prompt('What is the Verification code?').strip()
    '''Step 3: Once the consumer has redirected the user back to the oauth_callback
    URL you can request the access token the user has approved. You use the
    request token to sign this request. After this is done you throw away the
    request token and use the access token returned. You should store this
    access token somewhere safe, like a database, for future use.'''
    session = OAuth1Session(client_key=api_key, client_secret=api_secret,
                            resource_owner_key=resource_owner_key, resource_owner_secret=resource_owner_secret,
                            verifier=oauth_verifier)
    access_token = session.fetch_access_token(access_token_url)
    final_output_data = {
        'oauth_token': access_token['oauth_token'],
        'oauth_token_secret': access_token['oauth_token_secret'],
        'api_key': api_key,
        'api_secret': api_secret,
        'color': True,
        'banner': False
    }
    # Ensure we have a folder to put this in, if it's in a nested config location
    output_folder = os.path.dirname(output_file)
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
        click.echo('Created folder {0} to hold your configuration'.format(output_folder))
    # Try to be safe about not destroying existing credentials
    if os.path.exists(output_file):
        if click.confirm('{0} exists already, would you like to back it up?'.format(output_file), default=True):
            shutil.move(output_file, output_file + '.backup')
        if not click.confirm('Overwrite the existing file?', default=False):
            return
    with open(output_file, 'w') as f:
        f.write(yaml.safe_dump(final_output_data, default_flow_style=False))
    click.echo('Credentials saved in "{0}"- you can now use gtd.py!'.format(output_file))
    click.echo('Use the "config" command to view or edit your configuration file')


# onboard }}}
# show {{{


@cli.group(short_help='Display cards, tags, or lists on this board')
def show():
    '''Display cards, tags, or lists on this board.'''
    pass


@show.command('lists')
@json_option
@click.option('-a', '--show-all', is_flag=True, default=False, help='Show open & archived lists')
@pass_config
def show_lists(config, json, show_all):
    '''Display all lists on this board'''
    _, board = BoardTool.start(config)
    display = Display(config.color)
    if config.banner and not json:
        display.banner()
    list_filter = 'all' if show_all else 'open'
    list_names = [l.name for l in board.get_lists(list_filter)]
    display.show_raw(list_names, use_json=json)


@show.command('tags')
@json_option
@pass_config
def show_tags(config, json):
    '''Display all tags on this board'''
    _, board = BoardTool.start(config)
    display = Display(config.color)
    if config.banner and not json:
        display.banner()
    tag_names = [t.name for t in board.get_labels()]
    display.show_raw(tag_names, use_json=json)


@show.command('cards')
@filtering_command
@json_option
@click.option('--tsv', is_flag=True, default=False, help='Output as tab-separated values')
@pass_config
def show_cards(config, json, tsv, tags, no_tags, match, listname, attachments, has_due):
    '''Display cards
    The show command prints a table of all the cards with fields that will fit on the terminal you're using.
    You can change this formatting by passing one of --tsv or --json, which will output as a tab-separated value sheet or JSON.
    This command along with the batch & review commands share a flexible argument scheme for getting card information.
    Mutually exclusive arguments include -t/--tags & --no-tags along with -j/--json & --tsv
    '''
    _, board = BoardTool.start(config)
    display = Display(config.color)
    if config.banner and not json:
        display.banner()
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    display.show_cards(cards, use_json=json, tsv=tsv)


# show }}}
# delete {{{


@cli.group()
def delete():
    '''Archive/delete cards, tags, or lists'''
    pass


@delete.command('list')
@click.argument('name')
@click.option('-n', '--noninteractive', is_flag=True, default=False, help='Do not prompt before deleting')
@pass_config
def delete_lists(config, name, noninteractive):
    '''Delete lists containing the substring <name>
    '''
    _, board = BoardTool.start(config)
    lists = [l for l in board.get_lists('open') if name in l.name]
    if noninteractive:
        [l.set_closed() for l in lists]
    else:
        for l in lists:
            if prompt_for_confirmation('Close this list?'):
                l.set_closed()
                click.secho('Closed!', fg='green')


@delete.command('cards')
@click.option('-f', '--force', is_flag=True, default=False, help='Delete the card rather than archiving it')
@click.option('-n', '--noninteractive', is_flag=True, default=False, help='Do not prompt before deleting')
@filtering_command
@pass_config
def delete_cards(config, force, noninteractive, tags, no_tags, match, listname, attachments, has_due):
    '''Delete a set of cards specified
    '''
    _, board = BoardTool.start(config)
    display = Display(config.color)
    if config.banner and not json:
        display.banner()
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    method = 'delete' if force else 'archive'
    if noninteractive:
        if force:
            [c.delete() for c in cards]
        else:
            [c.set_closed(True) for c in cards]
    else:
        for card in cards:
            display.show_card(card)
            if prompt_for_confirmation('Delete this card?'):
                if force:
                    card.delete()
                else:
                    card.set_closed(True)
                click.secho('Card {}d!'.format(method), fg='red')


# delete }}}
# add {{{


@cli.group()
def add():
    '''Add a new card, tag, or list'''
    pass


@add.command('card', short_help='Add a new card')
@click.argument('title', required=False)
@click.option('-m', '--message', help='Description for the new card')
@click.option('-e', '--edit', is_flag=True, help="Edit the card as soon as it's created")
@pass_config
def add_card(config, title, message, edit):
    '''Add a new card. If no title is provided, $EDITOR will be opened so you can write one.'''
    connection, board = BoardTool.start(config)
    inbox = BoardTool.get_inbox_list(connection, config)
    if not title:
        title = click.edit(require_save=True, text='<Title here>')
        if title is None:  # No changes were made in $EDITOR
            click.secho('No title entered for the new card!', fg='red')
            raise GTDException(1)
        else:
            title = title.strip()
    returned = inbox.add_card(name=title, desc=message)
    if edit:
        display = Display(config.color)
        list_lookup = BoardTool.list_lookup(board)
        label_lookup = BoardTool.label_lookup(board)
        CardTool.smart_menu(returned, display.show_card, list_lookup, label_lookup, Colors.yellow)
    else:
        click.secho('Successfully added card {0}!'.format(returned), fg='green')


@add.command('tag')
@click.argument('tagname')
@click.option('-c', '--color', help='color to create this tag with', default='black')
@pass_config
def add_tag(config, tagname, color):
    '''Add a new tag'''
    connection, board = BoardTool.start(config)
    label = board.add_label(tagname, color)
    click.secho('Successfully added tag {0}!'.format(label), color='green')


@add.command('list')
@click.argument('listname')
@pass_config
def add_list(config, listname):
    '''Add a new list'''
    connection, board = BoardTool.start(config)
    l = board.add_list(listname)
    click.secho('Successfully added list {0}!'.format(l), color='green')


@cli.command(short_help='egrep through titles of cards')
@click.argument('pattern', required=False)
@click.option('-i', '--insensitive', is_flag=True, help='Ignore case')
@click.option('-c', '--count', is_flag=True, help='Output the count of matching cards')
@click.option('-e', '--regexp', help='Specify multiple patterns to match against the titles of cards', multiple=True)
@pass_config
def grep(config, pattern, insensitive, count, regexp):
    '''egrep through titles of cards on this board. This command attemps to replicate a couple of grep flags
    faithfully, so if you're a power-user of grep this command will feel familiar.
    '''
    if not (pattern or regexp):
        click.secho('No pattern provided to grep: use either the argument or -e', fg='red')
        raise GTDException(1)
    # Merge together the different regex arguments
    final_pattern = '|'.join(regexp) if regexp else ''
    if pattern and final_pattern:
        final_pattern = final_pattern + '|' + pattern
    elif pattern:
        final_pattern = pattern
    flags = re.I if insensitive else 0
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(
        board,
        title_regex=final_pattern,
        regex_flags=flags
    )
    if count:
        print(sum(1 for _ in cards))
        raise GTDException(0)
    display = Display(config.color)
    if config.banner:
        display.banner()
    display.show_cards(cards)


# add }}}
# batch {{{


@cli.group(short_help='Perform one action on many cards')
def batch():
    '''Perform one action on many cards at once. These commands are all interactive; they will prompt you before taking destructive action.
    If your combination of flags result in no cards matching, no output will be produced. You can tell this is not an error by the 0 return code.
    '''
    pass


@batch.command('move')
@filtering_command
@pass_config
def batch_move(config, tags, no_tags, match, listname, attachments, has_due):
    '''Change the list of each card selected'''
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    display = Display(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        display.show_card(card)
        if prompt_for_confirmation('Want to move this one?', True):
            CardTool.move_to_list(card)


@batch.command('tag')
@filtering_command
@pass_config
def batch_tag(config, tags, no_tags, match, listname, attachments, has_due):
    '''Change tags on each card selected'''
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    display = Display(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        display.show_card(card)
        CardTool.add_labels(card)


@batch.command('due')
@filtering_command
@pass_config
def batch_due(config, tags, no_tags, match, listname, attachments, has_due):
    '''Set due date for all cards selected'''
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    display = Display(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        display.show_card(card)
        if prompt_for_confirmation('Set due date?'):
            CardTool.set_due_date(card)


@batch.command('attach')
@pass_config
def batch_attach(config):
    '''Extract HTTP links from card titles'''
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(board, title_regex=VALID_URL_REGEX)
    display = Display(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        display.show_card(card)
        if prompt_for_confirmation('Attach title?', True):
            CardTool.title_to_link(card)


# batch }}}


@cli.command(short_help='Use a smart shell-like menu')
@filtering_command
@pass_config
def review(config, tags, no_tags, match, listname, attachments, has_due):
    '''show a smart, command-line based menu for each card selected.
    This menu will prompt you to add tags to untagged cards, to attach the title
    of cards which have a link in the title, and gives you all the other functionality combined.
    '''
    connection, board = BoardTool.start(config)
    cards = BoardTool.filter_cards(
        board,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due
    )
    list_lookup = BoardTool.list_lookup(board)
    label_lookup = BoardTool.label_lookup(board)
    display = Display(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        CardTool.smart_menu(card, display.show_card, list_lookup, label_lookup, Colors.yellow)
    click.echo('All done, have a great day!')


def main():
    try:
        cli()
    except requests.exceptions.ConnectionError:
        click.secho('[FATAL] Connection lost to the Trello API!', fg='red')
        sys.exit(1)
    except GTDException as e:
        if e.errno == 0:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()

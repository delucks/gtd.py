#!/usr/bin/env python
'''entrypoint to gtd.py, written with click'''
import re
import os
import sys
import json
import shutil
import readline  # noqa
import webbrowser

import yaml
import click
import requests
import prettytable
from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenRequestDenied
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter

from todo.card import Card, CardView
from todo.input import prompt_for_confirmation
from todo.display import Display
from todo.exceptions import GTDException
from todo.misc import (
    Colors,
    DevNullRedirect,
    WORKFLOW_TEXT,
    get_banner,
    VALID_URL_REGEX,
    return_on_eof,
    build_name_lookup,
)
from todo.configuration import Configuration
from todo import __version__
from todo.connection import TrelloConnection


class CLIContext:
    '''CLIContext is a container for the commonly used objects in each gtd command.
    It is passed around as an argument injected by click after the cli() function runs.
    Any reference to "ctx" as a parameter in this file is an instance of CLIContext.

    config: todo.configuration.Configuration
    connection: todo.connection.TrelloConnection
    display: todo.display.Display
    '''

    def __init__(self, config: Configuration):
        self.config = config
        self.connection = TrelloConnection(config)
        self.display = Display(config, self.connection)
        self.board = self.connection.main_board()
        # Cached state for card_repl
        self._list_choices = build_name_lookup(self.connection.main_board().get_lists('open'))
        self._label_choices = build_name_lookup(self.connection.main_board().get_labels(limit=200))

    def card_repl(self, card: dict) -> bool:
        '''card_repl displays a command-prompt based UI for modifying a card, with tab-completion and suggestions.
        It is the logic behind "gtd review" and the "-e" flag in "gtd add"

        It makes assumptions about what a user might want to do with a card:
        - Are there attachments? Maybe you want to open them.
        - Does there appear to be a URL in the title? You might want to attach it.
        - Are there no tags? Maybe you want to add some.

        Returns:
            boolean: move forwards or backwards in the deck of cards
        '''
        on = Colors.yellow if self.config.color else ''
        off = Colors.reset if self.config.color else ''
        self.display.show_card(card)
        if self.config.prompt_for_open_attachments and card['badges']['attachments']:
            if prompt_for_confirmation(f'{on}Open attachments?{off}', False):
                with DevNullRedirect():
                    for url in [a['url'] for a in card.fetch_attachments() if a['url']]:
                        webbrowser.open(url)
        if re.search(VALID_URL_REGEX, card['name']):
            if prompt_for_confirmation(f'{on}Link in title detected, want to attach it & rename?{off}', True):
                card.title_to_link()
        if self.config.prompt_for_untagged_cards and not card['labels']:
            print(f'{on}No tags on this card yet, want to add some?{off}')
            card.add_labels(self._label_choices)
        commands = {
            'archive': 'mark this card as closed',
            'attach': 'add, delete, or open attachments',
            'change-list': 'move this to a different list on the same board',
            'comment': 'add a comment to this card',
            'delete': 'permanently delete this card',
            'duedate': 'add a due date or change the due date',
            'description': 'change the description of this card (desc)',
            'help': 'display this help output (h)',
            'move': 'move to a different board and list (m)',
            'next': 'move to the next card (n)',
            'open': 'open all links on this card (o)',
            'prev': 'go back to the previous card (p)',
            'print': 're-display this card',
            'rename': 'change title of this card',
            'tag': 'add or remove tags on this card (t)',
            'unarchive': 'mark this card as open',
            'quit': 'exit program',
        }
        command_completer = FuzzyWordCompleter(commands.keys())
        while True:
            user_input = prompt('gtd.py > ', completer=command_completer)
            if user_input in ['q', 'quit']:
                raise GTDException(0)
            elif user_input in ['n', 'next']:
                return True
            elif user_input in ['p', 'prev']:
                return False
            elif user_input == 'print':
                card.fetch()
                self.display.show_card(card)
            elif user_input in ['o', 'open']:
                with DevNullRedirect():
                    for url in [a['url'] for a in card.fetch_attachments() if a['url'] is not None]:
                        webbrowser.open(url)
            elif user_input in ['desc', 'description']:
                card.change_description()
            elif user_input == 'delete':
                card.delete()
                print('Card deleted')
                return True
            elif user_input == 'attach':
                card.manipulate_attachments()
            elif user_input == 'archive':
                card.set_closed(True)
                print('Card archived')
                return True
            elif user_input == 'unarchive':
                card.set_closed(False)
                print('Card returned to board')
            elif user_input in ['t', 'tag']:
                card.add_labels(self._label_choices)
            elif user_input == 'rename':
                # TODO optional form 'rename New name of card'
                card.rename()
            elif user_input == 'duedate':
                card.set_due_date()
            elif user_input in ['h', 'help']:
                for cname, cdesc in commands.items():
                    print('{0:<16}| {1}{2}{3}'.format(cname, on, cdesc, off))
            elif user_input == 'change-list':
                if card.move_to_list(self._list_choices):
                    return True
            elif user_input in ['m', 'move']:
                self.move_between_boards(card)
            elif user_input == 'comment':
                # TODO Optional form 'comment Contents of a comment'
                new_comment = click.edit(text='<Comment here>', require_save=True)
                if new_comment:
                    card.comment(new_comment)
                else:
                    click.secho('Change the text & save to post the comment', fg='red')
            else:
                print(f'{on}{user_input}{off} is not a command, type "{on}help{off}" to view available commands')

    @return_on_eof
    def move_between_boards(self, card: Card) -> None:
        boards_by_name = self.connection.boards_by_name()
        board_name = prompt('gtd.py > move > board name? ', completer=FuzzyWordCompleter(boards_by_name.keys()))
        board_id = boards_by_name[board_name]['id']
        lists_json = self.connection.trello.fetch_json(f'/boards/{board_id}/lists?cards=none&filter=open&fields=name')
        name_to_listid = {l['name']: l['id'] for l in lists_json}
        list_name = prompt(
            f'gtd.py > move > {board_name} > list name? ', completer=FuzzyWordCompleter(name_to_listid.keys()),
        )
        card.change_board(board_id, list_id=name_to_listid[list_name])
        click.secho(f'Changed list to {list_name} on {board_name}', fg='green')


pass_context = click.make_pass_decorator(CLIContext)


def validate_fields(command_context, param, value):
    valid = Display.valid_fields()
    possible = value.split(',') if value else []
    for field in possible:
        if field not in valid:
            raise click.BadParameter(f'Field {field} is not a valid field! Use {",".join(valid)}')
    return possible


def validate_sort(command_context, param, value):
    if value and value not in Display.valid_fields():
        raise click.BadParameter(f'Sort parameter {value} is not a valid field!')
    return value


def sorting_fields_command(f):
    f = click.option('--fields', callback=validate_fields, help='[Table] display only these fields')(f)
    f = click.option('--by', default='activity', callback=validate_sort, help='[Table] sort by this field')(f)
    return f


def card_filtering_command(f):
    '''Add common options to a click function that will filter Trello cards'''
    f = click.option('-t', '--tags', default=None, help='Filter cards by this comma-separated list of tag names')(f)
    f = click.option('--no-tags', is_flag=True, default=None, help='Only show cards which have no tags')(f)
    f = click.option('-m', '--match', help='Filter cards to this regex on their title', default=None)(f)
    f = click.option('-l', '--listname', help='Only show cards from this list', default=None)(f)
    f = click.option('--attachments', is_flag=True, help='Only show cards which have attachments', default=None)(f)
    f = click.option('--has-due', is_flag=True, help='Only show cards which have due dates', default=None)(f)
    f = click.option(
        '-s',
        '--status',
        default='visible',
        help='Show cards in this state',
        type=click.Choice(['all', 'closed', 'open', 'visible']),
    )(f)
    return f


def json_option(f):
    return click.option('-j', '--json', 'use_json', is_flag=True, default=False, help='Output JSON')(f)


def tsv_option(f):
    return click.option('--tsv', is_flag=True, default=False, help='Output tab-separated values')(f)


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(__version__)
@click.option('-b', '--board', default=None, help='Name of the board to work with for this session')
@click.option('--color/--no-color', default=None, help='Use ANSI terminal colors')
@click.option('--banner/--no-banner', default=None, help='Print a gtd.py ascii art banner')
@click.pass_context
def cli(top_level_context, board, color, banner):
    '''gtd.py'''
    try:
        config = Configuration.from_file()
    except GTDException:
        click.echo('Could not find a valid config file for gtd.')
        if click.confirm('Would you like to create it interactively?'):
            top_level_context.invoke(onboard)
            click.secho('Please re-run your command to pick up the credentials', fg='green')
        else:
            print('Put your config file in one of the following locations:')
            for l in Configuration.all_config_locations():
                print('  ' + l)
        raise
    # CLI arguments always take precedence over config
    if board is not None:
        config.board = board
    if color is not None:
        config.color = color
    if banner is not None:
        config.banner = banner
    # Click's internal setting
    top_level_context.color = config.color
    top_level_context.obj = CLIContext(config)


@cli.command()
@click.option('-w', '--workflow', is_flag=True, default=False, help='Show a Getting Things Done workflow')
@click.option('-b', '--banner', is_flag=True, default=False, help='Show a random banner')
@pass_context
def info(ctx, workflow, banner):
    '''Learn more about gtd.py'''
    if workflow:
        click.secho(WORKFLOW_TEXT, fg='yellow')
        raise GTDException(0)
    elif banner:
        print(get_banner(use_color=ctx.config.color))
    else:
        on = Colors.green if ctx.config.color else ''
        off = Colors.reset if ctx.config.color else ''
        print(f'gtd.py version {on}{__version__}{off}')
        print(f'Visit {on}https://github.com/delucks/gtd.py/{off} for more information')


@cli.command()
@click.pass_context
def help(top_level_context):
    '''Show this message and exit.'''
    print(cli.get_help(top_level_context))


@cli.command()
@click.option('-e', '--edit', is_flag=True, help='Open $EDITOR on the configuration file')
def config(edit):
    '''Show or modify user configuration'''
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
        click.secho('Invalid API key/secret provided: {api_key} / {api_secret}', fg='red')
        sys.exit(1)
    resource_owner_key, resource_owner_secret = response.get('oauth_token'), response.get('oauth_token_secret')
    '''Step 2: Redirect to the provider. Since this is a CLI script we do not
    redirect. In a web application you would redirect the user to the URL
    below.'''
    user_confirmation_url = (
        f'{authorize_url}?oauth_token={resource_owner_key}&scope=read,write&expiration=never&name=gtd.py'
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
    session = OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=oauth_verifier,
    )
    access_token = session.fetch_access_token(access_token_url)
    final_output_data = {
        'oauth_token': access_token['oauth_token'],
        'oauth_token_secret': access_token['oauth_token_secret'],
        'api_key': api_key,
        'api_secret': api_secret,
        'color': True,
        'banner': False,
    }
    # Ensure we have a folder to put this in, if it's in a nested config location
    output_folder = os.path.dirname(output_file)
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
        click.echo(f'Created folder {output_folder} to hold your configuration')
    # Try to be safe about not destroying existing credentials
    if os.path.exists(output_file):
        if click.confirm(f'{output_file} exists already, would you like to back it up?', default=True):
            shutil.move(output_file, output_file + '.backup')
        if not click.confirm('Overwrite the existing file?', default=False):
            return
    with open(output_file, 'w') as f:
        f.write(yaml.safe_dump(final_output_data, default_flow_style=False))
    click.echo(f'Credentials saved in "{output_file}"- you can now use gtd.py!')
    click.echo('Use the "config" command to view or edit your configuration file')


# onboard }}}
# show {{{


@cli.group()
def show():
    '''Display cards, tags, lists, or boards'''
    pass


@show.command('boards')
@json_option
@tsv_option
@click.option('--by', default='activity', help='Choose field to sort (when not using json output)')
@click.option('-a', '--show-all', is_flag=True, default=False, help='Show closed boards')
@pass_context
def show_boards(ctx, use_json, tsv, by, show_all):
    '''Show all boards your account can access'''
    if show_all:
        boards = ctx.connection.trello.fetch_json('/members/me/boards/?filter=all')
    else:
        boards = ctx.connection.boards
    if use_json:
        print(json.dumps(boards, sort_keys=True, indent=2))
        return
    else:
        ctx.display.banner()
    # Set up a table to hold our boards
    board_columns = ['name', 'activity', 'members', 'permission', 'url']
    if by not in board_columns:
        click.secho(f'Field {by} is not a valid field: {",".join(board_columns)}', fg='red')
        raise GTDException(1)
    table = prettytable.PrettyTable()
    table.field_names = board_columns
    table.align = 'l'
    if tsv:
        table.set_style(prettytable.PLAIN_COLUMNS)
    else:
        table.hrules = prettytable.FRAME
    for b in boards:
        table.add_row(
            [
                b['name'],
                b['dateLastActivity'] or '',
                len(b['memberships']),
                b['prefs']['permissionLevel'],
                b['shortUrl'],
            ]
        )
    try:
        table[0]
    except IndexError:
        click.secho('You have no boards!', fg='red')
    print(table.get_string(sortby=by))


@show.command('lists')
@json_option
@click.option('-a', '--show-all', is_flag=True, default=False, help='Show open & archived lists')
@pass_context
def show_lists(ctx, use_json, show_all):
    '''Display all lists on this board'''
    status_filter = 'all' if show_all else 'open'
    lists_json = ctx.connection.main_lists(status_filter=status_filter, force=True)
    if use_json:
        print(json.dumps(lists_json, sort_keys=True, indent=2))
        return
    ctx.display.banner()
    for list_struct in lists_json:
        print(f'{list_struct["name"]} ({list_struct["id"]})')


@show.command('tags')
@json_option
@click.option('-l', '--listname', default=None, help='Only show the tags present on this list')
@pass_context
def show_tags(ctx, use_json, listname):
    '''Display all tags on this board'''
    if listname:
        # Assemble a set of all tags on each card
        tags = set()
        lists_json = ctx.connection.trello.fetch_json(
            f'/boards/{ctx.board.id}/lists',
            query_params={'filter': 'open', 'fields': 'id,name', 'cards': 'open', 'card_fields': 'labels'},
        )
        for list_obj in lists_json:
            if re.search(listname, list_obj['name']):
                for card in list_obj['cards']:
                    for label in card['labels']:
                        tags.add(label['name'])
        tag_names = list(tags)
    else:
        tag_names = [t.name for t in ctx.board.get_labels()]
    if use_json:
        print(json.dumps(tag_names, sort_keys=True, indent=2))
        return
    ctx.display.banner()
    for tag in tag_names:
        print(tag)


@show.command('cards')
@card_filtering_command
@json_option
@tsv_option
@sorting_fields_command
@pass_context
def show_cards(ctx, use_json, tsv, tags, no_tags, match, listname, attachments, has_due, status, by, fields):
    '''Display cards
    The show command prints a table of all the cards with fields that will fit on the terminal you're using.
    You can change this formatting by passing one of --tsv or --json, which will output as a tab-separated value sheet
    or JSON. This command along with the batch & review commands share a flexible argument scheme for getting card
    information. Mutually exclusive arguments include -t/--tags & --no-tags along with -j/--json & --tsv
    '''
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    if use_json:
        print(cards.json())
    else:
        ctx.display.banner()
        ctx.display.show_cards(cards, tsv=tsv, sort=by, table_fields=fields)


@show.command('soon')
@json_option
@tsv_option
@pass_context
def show_soon(ctx, use_json, tsv):
    cards = CardView.create(ctx, status='visible', has_due_date=True)
    if use_json:
        print(cards.json())
    else:
        ctx.display.banner()
        ctx.display.show_cards(cards, tsv=tsv, sort='due')


# show }}}
# delete {{{


@cli.group()
def delete():
    '''Archive/delete cards, tags, or lists'''
    pass


@delete.command('list')
@click.argument('name')
@click.option('-n', '--noninteractive', is_flag=True, default=False, help='Do not prompt before deleting')
@pass_context
def delete_list(ctx, name, noninteractive):
    '''Delete a list by name'''
    lists = [l for l in ctx.board.get_lists('open') if l.name == name]
    if not lists:
        click.secho(f'No such list {name}', fg='red')
    for l in lists:
        if noninteractive or prompt_for_confirmation(f'Close list "{l.name}"?'):
            l.close()
            click.secho(f'Closed {l.name}!', fg='green')


@delete.command('tag')
@click.argument('name')
@click.option('-n', '--noninteractive', is_flag=True, default=False, help='Do not prompt before deleting')
@pass_context
def delete_tag(ctx, name, noninteractive):
    '''Delete a tag by name'''
    tags = [l for l in ctx.board.get_labels() if l.name == name]
    if not tags:
        click.secho(f'No such tag {name}', fg='red')
    for t in tags:
        if noninteractive or prompt_for_confirmation(f'Delete tag "{t.name}"?'):
            ctx.board.delete_label(t.id)
            click.secho(f'Deleted {t.name}!', fg='green')


@delete.command('cards')
@click.option('-f', '--force', is_flag=True, default=False, help='Delete the card rather than archiving it')
@click.option('-n', '--noninteractive', is_flag=True, default=False, help='Do not prompt before deleting')
@card_filtering_command
@pass_context
def delete_cards(ctx, force, noninteractive, tags, no_tags, match, listname, attachments, has_due, status):
    '''Delete a set of cards specified
    '''
    ctx.display.banner()
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    method = 'delete' if force else 'archive'
    if noninteractive:
        if force:
            [c.delete() for c in cards]
        else:
            [c.set_closed(True) for c in cards]
    else:
        for card in cards:
            ctx.display.show_card(card)
            if prompt_for_confirmation('Delete this card?'):
                if force:
                    card.delete()
                else:
                    card.set_closed(True)
                click.secho(f'Card {method}d!', fg='red')


# delete }}}
# add {{{


@cli.group()
def add():
    '''Add a new card, tag, list or board'''
    pass


@add.command('card', short_help='Add a new card')
@click.argument('title', required=False)
@click.option('-m', '--message', help='Description for the new card')
@click.option('-e', '--edit', is_flag=True, help="Edit the card as soon as it's created")
@click.option('-l', '--listname', default=None, help='List to place this card in. Defaults to inbox_list')
@pass_context
def add_card(ctx, title, message, edit, listname):
    '''Add a new card. If no title is provided, $EDITOR will be opened so you can write one.'''
    connection = ctx.connection
    if listname is None:
        inbox = connection.inbox_list()
    else:
        pattern = re.compile(listname, flags=re.I)
        target_lists = filter(lambda x: pattern.search(x.name), ctx.board.get_lists('open'))
        try:
            inbox = next(target_lists)
        except StopIteration:
            click.secho(f'No list names matched by {listname}', fg='red')
            raise GTDException(1)
    if not title:
        title = click.edit(require_save=True, text='<Title here>')
        if title is None:  # No changes were made in $EDITOR
            click.secho('No title entered for the new card!', fg='red')
            raise GTDException(1)
        else:
            title = title.strip()
    returned = inbox.add_card(name=title, desc=message)
    if edit:
        ctx.card_repl(returned)
    else:
        click.secho(f'Successfully added card "{returned.name}"!', fg='green')


@add.command('tag')
@click.argument('tagname')
@click.option('-c', '--color', help='color to create this tag with', default='black')
@pass_context
def add_tag(ctx, tagname, color):
    '''Add a new tag'''
    label = ctx.board.add_label(tagname, color)
    click.secho(f'Created tag "{label.name}"', color='green')


@add.command('list')
@click.argument('listname')
@pass_context
def add_list(ctx, listname):
    '''Add a new list'''
    new_list = ctx.board.add_list(listname)
    click.secho(f'Created list "{new_list}"', color='green')


@add.command('board')
@click.argument('boardname')
@pass_context
def add_board(ctx, boardname):
    '''Add a new board'''
    connection = ctx.connection
    if connection.trello.add_board(boardname):
        click.secho(f'Board {boardname} created', fg='green')


@cli.command(short_help='egrep through titles of cards')
@click.argument('pattern', required=False)
@click.option('-i', '--insensitive', is_flag=True, help='Ignore case')
@click.option('-c', '--count', is_flag=True, help='Output the count of matching cards')
@click.option('-e', '--regexp', help='Specify multiple patterns to match against the titles of cards', multiple=True)
@sorting_fields_command
@json_option
@pass_context
def grep(ctx, pattern, insensitive, count, regexp, by, fields, use_json):
    '''egrep through titles of cards on this board. This command attemps to replicate a couple of grep flags
    faithfully, so if you're a power-user of grep this command will feel familiar.
    One deviation from grep is the --json flag, which outputs all matching cards in full JSON format.
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
    cards = CardView.create(ctx, status='visible', title_regex=final_pattern, regex_flags=flags)
    if count:
        print(sum(1 for _ in cards))
        return
    if use_json:
        print(cards.json())
    else:
        ctx.display.banner()
        ctx.display.show_cards(cards, sort=by, table_fields=fields)


# add }}}
# batch {{{


@cli.group(short_help='Perform one action on many cards')
def batch():
    '''Perform one action on many cards at once. These commands are all interactive; they will prompt you before taking destructive action.
    If your combination of flags result in no cards matching, no output will be produced. You can tell this is not an error by the 0 return code.
    '''
    pass


@batch.command('move')
@card_filtering_command
@pass_context
def batch_move(ctx, tags, no_tags, match, listname, attachments, has_due, status):
    '''Change the list of each card selected'''
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    ctx.display.banner()
    for card in cards:
        ctx.display.show_card(card)
        if prompt_for_confirmation('Want to move this one?', True):
            card.move_to_list(ctx._list_choices)


@batch.command('tag')
@card_filtering_command
@pass_context
def batch_tag(ctx, tags, no_tags, match, listname, attachments, has_due, status):
    '''Change tags on each card selected'''
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    ctx.display.banner()
    for card in cards:
        ctx.display.show_card(card)
        card.add_labels(ctx._label_choices)


@batch.command('due')
@card_filtering_command
@pass_context
def batch_due(ctx, tags, no_tags, match, listname, attachments, has_due, status):
    '''Set due date for all cards selected'''
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    ctx.display.banner()
    for card in cards:
        ctx.display.show_card(card)
        if prompt_for_confirmation('Set due date?'):
            card.set_due_date()


@batch.command('attach')
@pass_context
def batch_attach(ctx):
    '''Extract HTTP links from card titles'''
    cards = CardView.create(ctx, status='visible', title_regex=VALID_URL_REGEX)
    ctx.display.banner()
    for card in cards:
        ctx.display.show_card(card)
        if prompt_for_confirmation('Attach title?', True):
            card.title_to_link()


# batch }}}


@cli.command(short_help='Use a smart repl-like menu')
@card_filtering_command
@pass_context
def review(ctx, tags, no_tags, match, listname, attachments, has_due, status):
    '''show a smart, command-line based menu for each card selected.
    This menu will prompt you to add tags to untagged cards, to attach the title
    of cards which have a link in the title, and gives you all the other functionality combined.
    '''
    cards = CardView.create(
        ctx,
        status=status,
        tags=tags,
        no_tags=no_tags,
        title_regex=match,
        list_regex=listname,
        has_attachments=attachments,
        has_due_date=has_due,
    )
    ctx.display.banner()
    card = cards.current()
    while card is not None:
        if ctx.card_repl(card):
            card = cards.next()
        else:
            card = cards.prev()


def main():
    try:
        cli()
    except requests.exceptions.ConnectionError:
        click.secho('[FATAL] Connection lost to the Trello API!', fg='red')
        sys.exit(1)
    except GTDException as e:
        sys.exit(e.errno)


if __name__ == '__main__':
    main()

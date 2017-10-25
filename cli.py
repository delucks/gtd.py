#!/usr/bin/env python
'''entrypoint to gtd.py, written with click'''
import re
import sys
import click
import requests
import readline  # noqa
from gtd.input import prompt_for_confirmation, BoardTool, CardTool
from gtd.display import JSONDisplay, TextDisplay, TableDisplay
from gtd.exceptions import GTDException
from gtd.misc import Colors
from gtd import __version__


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def cli():
    '''gtd.py'''
    pass


@cli.command()
@click.pass_context
def help(ctx):
    '''Show this help message and exit.'''
    click.echo(ctx.parent.get_help())


@cli.command()
def version():
    '''Display the running version of gtd.py'''
    click.echo('gtd.py version {0}'.format(__version__))


@cli.command()
def workflow():
    '''show the recommended workflow'''
    click.echo(
        '1. Collect absolutely everything that can take your attention into "Inbound"\n'
        '2. Filter:\n'
        '    Nonactionable -> Static Reference or Delete\n'
        '    Takes < 2 minutes -> Do now, then Delete\n'
        '    Not your responsibility -> "Holding" or "Blocked" with follow-up\n'
        '    Something to communicate -> messaging lists\n'
        '    Your responsibility -> Your lists\n'
        '3. Write "final" state of each task and "next" state of each task\n'
        '4. Categorize inbound items into lists based on action type required (call x, talk to x, meet x...)\n'
        '5. Reviews:\n'
        '    Daily -> Go through "Inbound" and "Doing"\n'
        '    Weekly -> Additionally, go through "Holding", "Blocked", and messaging lists\n'
        '6. Do\n'
        '\n'
        'The goal is to get everything except the current task out of your head\n'
        'and into a trusted system external to your mind.'
    )


@cli.command()
@click.argument('showtype', type=click.Choice(['lists', 'tags', 'cards']))
@click.option('-j', '--json', is_flag=True, default=False, help='output as JSON')
@click.option('-t', '--tags', default=None)
@click.option('--no-tags', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--listname', help='filter cards to this list', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments', default=None)
@click.option('--has-due', is_flag=True, help='select cards which have due dates', default=None)
def show(showtype, json, tags, no_tags, match, listname, attachments, has_due):
    '''filter and display cards'''
    config, _, board = BoardTool.start()
    if json:
        display = JSONDisplay(config.color)
    else:
        li, la = BoardTool.list_and_label_length(board)
        display = TableDisplay(config.color, li, la)
    if config.banner:
        display.banner()
    if showtype == 'lists':
        lnames = [l.name.decode('utf8') for l in board.get_lists('open')]
        with display:
            display.show_list(lnames)
    elif showtype == 'tags':
        tnames = [t.name.decode('utf8') for t in board.get_labels()]
        with display:
            display.show_list(tnames)
    else:
        cards = BoardTool.filter_cards(
            board,
            tags=tags,
            no_tags=no_tags,
            title_regex=match,
            list_regex=listname,
            has_attachments=attachments,
            has_due_date=has_due
        )
        with display:
            for card in cards:
                display.show(card, True)


@cli.command()
@click.argument('add_type', type=click.Choice(['tag', 'card', 'list']))
@click.argument('title')
@click.option('-m', '--message', help='description for a new card')
@click.option('--edit', is_flag=True)
def add(add_type, title, message, edit):
    '''add a new card, tag, or list'''
    config, connection, board = BoardTool.start()
    display = TextDisplay(config.color)
    if add_type == 'tag':
        label = board.add_label(title, 'black')
        click.echo('Successfully added tag {0}!'.format(label))
    elif add_type == 'list':
        l = board.add_list(title)
        click.echo('Successfully added list {0}!'.format(l))
    else:
        inbox = BoardTool.get_inbox_list(connection, config)
        returned = inbox.add_card(name=title, desc=message)
        if edit:
            if config.color:
                CardTool.review_card(returned, display.show, BoardTool.list_lookup(board), BoardTool.label_lookup(board), Colors.green)
            else:
                CardTool.review_card(returned, display.show, BoardTool.list_lookup(board), BoardTool.label_lookup(board))
        else:
            click.echo('Successfully added card {0}!'.format(returned))


@cli.command()
@click.argument('pattern')
@click.option('-i', '--insensitive', is_flag=True, help='ignore case')
def grep(pattern, insensitive):
    '''egrep through titles of cards'''
    flags = re.I if insensitive else 0
    config, connection, board = BoardTool.start()
    cards = BoardTool.filter_cards(
        board,
        title_regex=pattern,
        regex_flags=flags
    )
    li, la = BoardTool.list_and_label_length(board)
    display = TableDisplay(config.color, li, la)
    if config.banner:
        display.banner()
    with display:
        for card in cards:
            display.show(card, True)


@cli.command()
@click.argument('batchtype')
@click.option('-t', '--tags', default=None)
@click.option('--no-tags', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--listname', help='use cards from lists with names matching this regular expression', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments', default=None)
@click.option('--has-due', is_flag=True, help='select cards which have due dates', default=None)
def batch(batchtype, tags, no_tags, match, listname, attachments, has_due):
    '''perform one action on many cards'''
    config, connection, board = BoardTool.start()
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

    display = TextDisplay(config.color)
    if config.banner:
        display.banner()
    with display:
        if batchtype == 'move':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    CardTool.move_to_list(card, list_lookup)
        elif batchtype == 'delete':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Should we delete this card?'):
                    card.delete()
                    click.echo('Card deleted!')
        elif batchtype == 'due':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Set due date?'):
                    CardTool.set_due_date(card)
        else:
            for card in cards:
                display.show(card)
                CardTool.add_labels(card, label_lookup)
    click.echo('Batch completed, have a great day!')


@cli.command()
@click.option('-t', '--tags', default=None)
@click.option('--no-tags', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--listname', help='use cards from lists with names matching this regular expression', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments', default=None)
@click.option('--has-due', is_flag=True, help='select cards which have due dates', default=None)
@click.option('--daily', help='daily review mode')
def review(tags, no_tags, match, listname, attachments, has_due, daily):
    '''open a menu for each card selected'''
    if daily:
        click.echo('Welcome to daily review mode!\nThis combines all "Doing" lists so you can review what you should be doing soon.\n')
        listname = 'Doing'
    config, connection, board = BoardTool.start()
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
    display = TextDisplay(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        CardTool.smart_menu(card, display.show, list_lookup, label_lookup, Colors.yellow)
        #if config.color:
        #    CardTool.review_card(card, display.show, list_lookup, label_lookup, Colors.green)
        #else:
        #    CardTool.review_card(card, display.show, list_lookup, label_lookup)
    click.echo('All done, have a great day!')


if __name__ == '__main__':
    try:
        cli()
    except requests.exceptions.ConnectionError:
        print('[FATAL] Connection lost to the Trello API!')
        sys.exit(1)
    except GTDException as e:
        if e.errno == 0:
            sys.exit(0)
        else:
            print('Quitting due to error')
            sys.exit(1)

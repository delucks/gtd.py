#!/usr/bin/env python
'''entrypoint to gtd.py, written with click'''
import re
import sys
import readline  # noqa

import click

from gtd.input import prompt_for_confirmation, BoardTool, CardTool
from gtd.display import JSONDisplay, TextDisplay, TableDisplay
from gtd.exceptions import GTDException
from gtd.connection import TrelloConnection
from gtd.config import ConfigParser
from gtd.misc import Colors
from gtd import __version__


def init_and_filter(tag, no_tag, match, listname, attachments, has_due, flags=0):
    '''set up the interaction backend and filter cards by the users' selected
    flags'''
    config = ConfigParser().config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    if listname:
        pattern = re.compile(listname, flags=re.I)
        target_lists = filter(
            lambda x: pattern.search(x.name.decode('utf8')),
            wrapper.main_board.get_lists('open')
        )
    else:
        target_lists = []
    selected_tag = wrapper.magic_value if no_tag else tag if tag else None
    cards = wrapper.get_cards(
        target_lists=target_lists,
        tag=selected_tag,
        title_regex=match,
        has_attachments=attachments,
        has_due_date=has_due,
        regex_flags=flags
    )
    return config, wrapper, cards


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
@click.option('-t', '--tag', default=None)
@click.option('--no-tag', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--list', help='filter cards to this list', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments')
@click.option('--has-due', is_flag=True, help='select cards which have due dates')
def show(showtype, json, tag, no_tag, match, list, attachments, has_due):
    '''filter and display cards'''
    config, wrapper, cards = init_and_filter(tag, no_tag, match, list, attachments, has_due)
    if json:
        display = JSONDisplay(config.color)
    else:
        max_list_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')], key=len))
        max_label_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_labels()], key=len))
        display = TableDisplay(config.color, max_list_len, max_label_len)
    if config.banner:
        display.banner()
    if showtype == 'lists':
        lnames = [l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')]
        with display:
            display.show_list(lnames)
    elif showtype == 'tags':
        tnames = [t.name.decode('utf8') for t in wrapper.main_board.get_labels()]
        with display:
            display.show_list(tnames)
    else:
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
    config = ConfigParser().config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    display = TextDisplay(config.color)
    if add_type == 'tag':
        label = wrapper.main_board.add_label(title, 'black')
        click.echo('Successfully added tag {0}!'.format(label))
    elif add_type == 'list':
        l = wrapper.main_board.add_list(title)
        click.echo('Successfully added list {0}!'.format(l))
    else:
        returned = wrapper.main_list.add_card(name=title, desc=message)
        if edit:
            if config.color:
                CardTool.review_card(returned, display.show, wrapper.list_lookup, wrapper.label_lookup, Colors.green)
            else:
                CardTool.review_card(returned, display.show, wrapper.list_lookup, wrapper.label_lookup)
        else:
            click.echo('Successfully added card {0}!'.format(returned))


@cli.command()
@click.argument('pattern')
@click.option('-i', '--insensitive', is_flag=True, help='ignore case')
def grep(pattern, insensitive):
    '''egrep through titles of cards'''
    flags = re.I if insensitive else 0
    config, wrapper, cards = init_and_filter([], None, pattern, None, None, None, flags)
    max_list_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')], key=len))
    max_label_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_labels()], key=len))
    display = TableDisplay(config.color, max_list_len, max_label_len)
    if config.banner:
        display.banner()
    with display:
        for card in cards:
            display.show(card, True)


@cli.command()
@click.argument('batchtype')
@click.option('--tag', default=None)
@click.option('--no-tag', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--listname', help='use cards from lists with names matching this regular expression', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments')
@click.option('--has-due', is_flag=True, help='select cards which have due dates')
def batch(batchtype, tag, no_tag, match, listname, attachments, has_due):
    '''perform one action on many cards'''
    config, wrapper, cards = init_and_filter(tag, no_tag, match, listname, attachments, has_due)
    display = TextDisplay(config.color)
    if config.banner:
        display.banner()
    with display:
        if batchtype == 'move':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    CardTool.move_to_list(card, wrapper.list_lookup)
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
                CardTool.add_labels(card, wrapper.label_lookup)
    click.echo('Batch completed, have a great day!')


@cli.command()
@click.option('--tag', default=None)
@click.option('--no-tag', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--listname', help='use cards from lists with names matching this regular expression', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments')
@click.option('--has-due', is_flag=True, help='select cards which have due dates')
@click.option('--daily', help='daily review mode')
def review(tag, no_tag, match, listname, attachments, has_due, daily):
    '''open a menu for each card selected'''
    if daily:
        click.echo('Welcome to daily review mode!\nThis combines all "Doing" lists so you can review what you should be doing soon.\n')
        listname = 'Doing'
    config, wrapper, cards = init_and_filter(tag, no_tag, match, listname, attachments, has_due)
    display = TextDisplay(config.color)
    if config.banner:
        display.banner()
    for card in cards:
        if config.color:
            CardTool.review_card(card, display.show, wrapper.list_lookup, wrapper.label_lookup, Colors.green)
        else:
            CardTool.review_card(card, display.show, wrapper.list_lookup, wrapper.label_lookup)
    click.echo('All done, have a great day!')


if __name__ == '__main__':
    try:
        cli()
    except GTDException as e:
        if e.errno == 0:
            sys.exit(0)
        else:
            print('Quitting due to error')
            sys.exit(1)

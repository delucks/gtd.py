#!/usr/bin/env python
'''rewritten using click'''
import sys
import readline  # noqa

import click

from gtd.input import prompt_for_confirmation, BoardTool
from gtd.display import JSONDisplay, TextDisplay, TableDisplay
from gtd.exceptions import GTDException
from gtd.connection import TrelloConnection
from gtd.config import ConfigParser
from gtd import __version__


@click.group(context_settings={'help_option_names':['-h','--help']}, invoke_without_command=True)
@click.option('--tag', default=None)
@click.option('--no-tag', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--list', help='filter cards to this list', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments')
@click.option('--has-due', is_flag=True, help='select cards which have due dates')
@click.pass_context
def cli(ctx, tag, no_tag, match, list, attachments, has_due):
    '''todo.py'''
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    elif ctx.invoked_subcommand in ['show', 'batch', 'review']:
        config = ConfigParser().config
        ctx.obj['config'] = config
        conn = TrelloConnection(config)
        ctx.obj['connection'] = conn
        wrapper = BoardTool(conn)
        ctx.obj['wrapper'] = wrapper
        target_lists = [wrapper.main_list] if config.list else []  # TODO make the conversion from str -> trello.List here more clear
        tag = wrapper.magic_value if no_tag else tag if tag else None
        ctx.obj['tag'] = tag
        ctx.obj['cards'] = wrapper.get_cards(
            target_lists=target_lists,
            tag=tag,
            title_regex=match,
            has_attachments=attachments,
            has_due_date=has_due
        )
    else:
        print(ctx.invoked_subcommand)


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
@click.option('--tag', default=None)
@click.option('--no-tag', is_flag=True, default=False)
@click.option('-m', '--match', help='filter cards to this regex on their title', default=None)
@click.option('-l', '--list', help='filter cards to this list', default=None)
@click.option('--attachments', is_flag=True, help='select cards which have attachments')
@click.option('--has-due', is_flag=True, help='select cards which have due dates')
def show(showtype, json, tag, no_tag, match, list, attachments, has_due):
    '''filter and display cards'''
    config = ConfigParser(parse_args=False).config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    target_lists = [wrapper.main_list] if list else []
    selected_tag = wrapper.magic_value if no_tag else tag if tag else None
    cards = wrapper.get_cards(
                target_lists=target_lists,
                tag=selected_tag,
                title_regex=match,
                has_attachments=attachments,
                has_due_date=has_due
            )
    if json:
        display = JSONDisplay(config.color)
    else:
        max_list_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')], key=len))
        max_label_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_labels()], key=len))
        display = TableDisplay(config.color, max_list_len, max_label_len)
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
    config = ConfigParser(parse_args=False).config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    display = TextDisplay(config.color)
    click.echo(add_type, title, message, edit)
    if add_type == 'tag':
        label = wrapper.main_board.add_label(title, 'black')
        print('Successfully added tag {0}!'.format(label))
    elif add_type == 'list':
        l = wrapper.main_board.add_list(title)
        print('Successfully added list {0}!'.format(l))
    else:
        returned = wrapper.main_list.add_card(name=title, desc=message)
        if edit:
            display.review_card(returned, wrapper)
        else:
            print('Successfully added card {0}!'.format(returned))


@cli.command()
@click.argument('pattern')
def grep(pattern):
    '''search for a pattern through the titles of all cards on the board'''
    config = ConfigParser(parse_args=False).config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    max_list_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')], key=len))
    max_label_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_labels()], key=len))
    display = TableDisplay(config.color, max_list_len, max_label_len)
    with display:
        for card in wrapper.get_cards(title_regex=pattern):
            display.show(card, True)


@cli.command()
@click.argument('batchtype')
@click.pass_context
def batch(batchtype, ctx):
    display = TextDisplay(ctx['config'].color)
    cards = ctx['cards']
    wrapper = ctx['wrapper']
    with display:
        if batchtype == 'move':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    wrapper.move_to_list(card)
        elif batchtype == 'delete':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Should we delete this card?'):
                    card.delete()
                    print('Card deleted!')
        elif batchtype == 'due':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Set due date?'):
                    wrapper.set_due_date(card)
        else:
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to tag this one?'):
                    wrapper.add_labels(card)
    click.echo('Batch completed, have a great day!')


if __name__ == '__main__':
    cli(obj={})

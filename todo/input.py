'''This is most of the user interface and helper functions'''
import re
import sys
import tty
import click
import string
import trello
import shutil
import termios
import itertools
import webbrowser
from functools import partial

import arrow
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter, FuzzyWordCompleter

from todo.misc import get_title_of_webpage, Colors, DevNullRedirect, VALID_URL_REGEX
from todo.exceptions import GTDException
from todo.connection import TrelloConnection


def parse_user_date_input(user_input):
    accepted_formats = ['MMM D YYYY', 'MM/DD/YYYY', 'DD/MM/YYYY']
    for fmt in accepted_formats:
        try:
            input_datetime = arrow.get(user_input, fmt)
            return input_datetime
        except arrow.parser.ParserError:
            continue
        except ValueError:
            continue
    return None


def prompt_for_confirmation(message, default=False):
    while True:
        options = ' (Y/n)' if default else ' (y/N)'
        print(message.strip() + options, end='', flush=True)
        choice = getch()
        print()
        if choice == 'y' or choice == 'n' or choice == '\r':
            break
        else:
            print('Input was not y, nor was it n. Enter is OK')
    return choice == 'y' if choice != '\r' else default


def getch():
    '''override terminal settings to read a single character from stdin'''
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x03':
            raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def single_select(options):
    '''A faster selection interface.
    Assigns a one-char identifier to each option and reads only one
    character from stdin. Return the option assigned to that identifier.
    Downside: you can only have 30ish options

    :param iterable options: choices you want the user to select between
    '''
    lookup = {}
    preferred_keys = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"]
    remainder = list(set(string.ascii_lowercase) - set(preferred_keys))
    all_keys = preferred_keys + remainder
    for idx, chunk in enumerate(options):
        assigned = all_keys[idx]
        lookup[assigned] = idx
        print('[{0}] {1}'.format(assigned, chunk))
    print('Press the character corresponding to your choice, selection will happen immediately. Enter to cancel')
    result = lookup.get(getch(), None)
    if result is not None:
        return list(options)[int(result)]
    else:
        return None


def tags_on_card(card, tags):
    '''Take in a comma-sep list of tag names, and ensure that
    each is on this card'''
    if card.labels:
        user_tags = set(tags.split(','))
        card_tags = set([l.name for l in card.labels])
        return user_tags.issubset(card_tags)
    else:
        return False


def triple_column_print(iterable):
    chunk_count = 3
    max_width = shutil.get_terminal_size().columns
    chunk_size = (max_width - 4) // chunk_count
    args = [iter(iterable)] * chunk_count
    for triplet in itertools.zip_longest(fillvalue='', *args):
        print('  {0:<{width}}{1:^{width}}{2:>{width}}  '.format(width=chunk_size, *triplet))


class CardTool:
    '''This static class holds functionality to do atomic modifications on certain cards.
    These methods are used inside of the user interaction parts of the codebase as a way of doing the same operation across
    different UI components.
    '''

    # TODO add type hints
    @staticmethod
    def add_labels(card, label_choices=None):
        '''Give the user a way to toggle labels on this card by their
        name rather than by a numeric selection interface. Using
        prompt_toolkit, we have automatic completion which makes
        things substantially faster without having to do a visual
        lookup against numeric IDs
        :param trello.Card card: the card to modify
        :param dict label_choices: str->trello.Label, the names and objects of labels on this board
        '''
        print('Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit')
        label_choices = label_choices or BoardTool.label_lookup(card.board)
        label_completer = FuzzyWordCompleter(label_choices.keys())
        while True:
            userinput = prompt('tag > ', completer=label_completer).strip()
            if userinput == '':
                break
            elif userinput == 'ls':
                triple_column_print(label_choices.keys())
            elif userinput not in label_choices.keys():
                if prompt_for_confirmation(
                    'Unrecognized tag name {0}, would you like to create it?'.format(userinput), False
                ):
                    label = card.board.add_label(userinput, 'black')
                    card.add_label(label)
                    click.echo(
                        'Successfully added tag {0} to board {1} and card {2}!'.format(
                            label.name, card.board.name, card.name
                        )
                    )
                    label_choices = BoardTool.label_lookup(card.board)
                    label_completer = FuzzyWordCompleter(label_choices.keys())
            else:
                label_obj = label_choices[userinput]
                try:
                    card.add_label(label_obj)
                    print('Added tag {0}'.format(Colors.green + userinput + Colors.reset))
                except trello.exceptions.ResourceUnavailable:
                    # This label already exists on the card so remove it
                    card.remove_label(label_obj)
                    print('Removed tag {0}'.format(Colors.red + userinput + Colors.reset))

    @staticmethod
    def smart_menu(
        card,
        f_display,
        list_choices,
        label_choices,
        color=None,
        prompt_for_open_attachments=False,
        prompt_for_untagged_cards=True,
    ):
        '''smart_menu is the logic behind "gtd review". It makes assumptions about what a user might want to do with a card:
        - Are there attachments? Maybe you want to open them.
        - Does there appear to be a URL in the title? You might want to attach it.
        - Are there no tags? Maybe you want to add some.
        Then gives you a nice tab-completed menu that lets you do all common operations on a card.
        '''
        on = Colors.yellow if color else ''
        off = Colors.reset if color else ''
        card.fetch()
        f_display(card)
        if card.get_attachments() and prompt_for_open_attachments:
            if prompt_for_confirmation('{0}Open attachments?{1}'.format(on, off), False):
                with DevNullRedirect():
                    for url in [a.url for a in card.get_attachments() if a.url is not None]:
                        webbrowser.open(url)
        if re.search(VALID_URL_REGEX, card.name):
            if prompt_for_confirmation(
                '{0}Link in title detected, want to attach it & rename?{1}'.format(on, off), True
            ):
                CardTool.title_to_link(card)
        if not card.labels and prompt_for_untagged_cards:
            print('{0}No tags on this card yet, want to add some?{1}'.format(on, off))
            CardTool.add_labels(card, label_choices)
        commands = {
            'archive': 'mark this card as closed',
            'attach': 'add, delete, or open attachments',
            'comment': 'add a comment to this card',
            'delete': 'permanently delete this card',
            'duedate': 'add a due date or change the due date',
            'description': 'change the description of this card (desc)',
            'help': 'display this help output (h)',
            'move': 'move to a different list (m)',
            'next': 'move on to the next card (n)',
            'open': 'open all links on this card (o)',
            'print': 'display this card (p)',
            'rename': 'change title of this card',
            'tag': 'add or remove tags on this card (t)',
            'quit': 'exit program',
        }
        command_completer = FuzzyWordCompleter(commands.keys())
        while True:
            user_input = prompt('gtd.py > ', completer=command_completer)
            if user_input in ['q', 'quit']:
                raise GTDException(0)
            elif user_input in ['n', 'next']:
                break
            elif user_input in ['p', 'print']:
                card.fetch()
                f_display(card)
            elif user_input in ['o', 'open']:
                with DevNullRedirect():
                    for url in [a.url for a in card.get_attachments() if a.url is not None]:
                        webbrowser.open(url)
            elif user_input in ['desc', 'description']:
                if CardTool.change_description(card):
                    print('Description changed!')
            elif user_input == 'delete':
                card.delete()
                print('Card deleted')
                break
            elif user_input == 'attach':
                CardTool.manipulate_attachments(card)
            elif user_input == 'archive':
                card.set_closed(True)
                print('Card archived')
                break
            elif user_input in ['t', 'tag']:
                CardTool.add_labels(card, label_choices)
            elif user_input == 'rename':
                CardTool.rename(card)
            elif user_input == 'duedate':
                CardTool.set_due_date(card)
            elif user_input in ['h', 'help']:
                for cname, cdesc in commands.items():
                    print('{0:<16}| {1}{2}{3}'.format(cname, on, cdesc, off))
            elif user_input in ['m', 'move']:
                if CardTool.move_to_list(card, list_choices):
                    break
            elif user_input == 'comment':
                new_comment = click.edit(text='<Comment here>', require_save=True)
                if new_comment:
                    card.comment(new_comment)
                else:
                    click.secho('Change the text & save to post the comment', fg='red')
            else:
                print(
                    '{0}{1}{2} is not a command, type "{0}help{2}" to view available commands'.format(
                        on, user_input, off
                    )
                )

    @staticmethod
    def title_to_link(card):
        # This assumes your link is in card.name somewhere
        sp = card.name.split()
        links = [n for n in sp if VALID_URL_REGEX.search(n)]
        existing_attachments = [a.name for a in card.get_attachments()]
        user_parameters = {'oldname': card.name}
        for idx, link_name in enumerate(links):
            # Attach this link
            if link_name not in existing_attachments:
                card.attach(url=link_name)
            # Get the URL & title of the link for the user to access in the renaming interface
            user_parameters['link{}'.format(idx)] = link_name
            possible_title = get_title_of_webpage(link_name)
            if possible_title:
                user_parameters['title{}'.format(idx)] = possible_title
        # Give the user a default title without the link, but allow them to use the title of the page from a link as a var instead
        reconstructed = ' '.join([n for n in sp if not VALID_URL_REGEX.search(n)])
        CardTool.rename(card, variables=user_parameters, default=reconstructed)

    @staticmethod
    def manipulate_attachments(card):
        '''Give the user a CRUD interface for attachments on this card'''
        print('Enter a URL, "delete", "open", "print", or Enter to exit')
        user_input = 'Nothing really'
        attachment_completer = WordCompleter(['delete', 'print', 'open', 'http://', 'https://'], ignore_case=True)
        while user_input != '':
            user_input = prompt('attach > ', completer=attachment_completer).strip()
            if re.search(VALID_URL_REGEX, user_input):
                # attach this link
                card.attach(url=user_input)
                print('Attached {0}'.format(user_input))
            elif user_input in ['delete', 'open']:
                attachment_opts = {a.name: a for a in card.get_attachments()}
                if not attachment_opts:
                    print('No attachments')
                    continue
                dest = single_select(attachment_opts.keys())
                if dest is not None:
                    target = attachment_opts[dest]
                    if user_input == 'delete':
                        card.remove_attachment(target.id)
                    elif user_input == 'open':
                        with DevNullRedirect():
                            webbrowser.open(target.url)
            elif user_input == 'print':
                existing_attachments = card.get_attachments()
                if existing_attachments:
                    print('Attachments:')
                    for a in existing_attachments:
                        print('  ' + a.name)

    @staticmethod
    def rename(card, default=None, variables={}):
        if variables:
            print('You can use the following variables in your new card title:')
            for k, v in variables.items():
                print('  ${}: {}'.format(k, v))
        suggestion = variables.get('title0', None) or card.name
        newname = input('Input new name for this card (blank for "{0}"): '.format(default or suggestion)).strip()
        if newname:
            for k, v in variables.items():
                expansion = '${}'.format(k)
                if expansion in newname:
                    newname = newname.replace(expansion, v)
            card.set_name(newname)
        else:
            # If there wasn't a default set for the card name, leave the card name unchanged
            card.set_name(default or suggestion)

    @staticmethod
    def set_due_date(card):
        '''prompt for the date to set this card due as'''

        def validate_date(text):
            return re.match(r'\d{2}\/\d{2}\/\d{4}', text) or re.match(r'[A-Z][a-z]{2} \d{2} \d{4}', text)

        validator = Validator.from_callable(
            validate_date,
            error_message='Enter a date in format "Jun 15 2018", "06/15/2018" or "15/06/2018". Ctrl+C to go back',
            move_cursor_to_end=True,
        )
        while True:
            try:
                user_input = prompt('date > ', validator=validator, validate_while_typing=True)
            except KeyboardInterrupt:
                return
            result = parse_user_date_input(user_input)
            if result is None:
                print('Invalid date format!')
            else:
                break
        card.set_due(result)
        card.fetch()  # Needed to pick up the new due date
        print('Due date set')
        return result

    @staticmethod
    def move_to_list(card, list_choices=None):
        '''Select labels to add to this card
        :param trello.Card card: the card to modify
        :param dict list_choices: str->trello.List, the names and objects of lists on this board
        '''
        list_choices = list_choices or BoardTool.list_lookup(card.board)
        dest = single_select(sorted(list_choices.keys()))
        if dest is not None:
            destination_list = list_choices[dest]
            card.change_list(destination_list.id)
            print('Moved to {0}'.format(destination_list.name))
            return destination_list
        else:
            print('Skipping!')
            return None

    @staticmethod
    def change_description(card):
        old_desc = card.desc or ''
        new_desc = click.edit(text=old_desc)
        if new_desc is not None:
            card.set_description(new_desc)
        return new_desc


class BoardTool:
    '''modeled after the last successful static class rewrite, this one will
    take in a top-level API connection (trello.Trello) with just about every method
    and return something useful to the program, like an iterable of cards or something else
    this should replace the existing BoardTool class and the init_and_filter method, which is really just
    doing some boilerplate that can be handled in this class
    '''

    @staticmethod
    def start(config):
        connection = TrelloConnection(config)
        board = BoardTool.get_main_board(connection, config)
        return connection, board

    @staticmethod
    def take_cards_from_lists(board, list_regex):
        pattern = re.compile(list_regex, flags=re.I)
        target_lists = filter(lambda x: pattern.search(x.name), board.get_lists('open'))
        for cardlist in target_lists:
            for card in cardlist.list_cards():
                yield card

    @staticmethod
    def create_card_filters(**kwargs):
        '''takes in arguments that relate to how cards should be filtered, and outputs
        a number of callables that are used in filtering an iterable of cards
        '''
        # Regular expression on trello.Card.name
        title_regex = kwargs.get('title_regex', None)
        regex_flags = kwargs.get('regex_flags', 0)

        def search_for_regex(card):
            try:
                return re.search(title_regex, card.name, regex_flags)
            except re.error as e:
                click.secho('Invalid regular expression "{1}" passed: {0}'.format(str(e), title_regex), fg='red')
                raise GTDException(1)

        # boolean queries about whether the card has things
        has_attachments = kwargs.get('has_attachments', None)
        no_tags = kwargs.get('no_tags', False)
        has_due_date = kwargs.get('has_due_date', None)
        # comma-separated string of tags to filter on
        tags = kwargs.get('tags', None)
        # custom user-supplied callable functions to filter a card on
        filter_funcs = kwargs.get('filter_funcs', None)
        # Parse arguments into callables
        filters = []
        if tags:
            filters.append(partial(tags_on_card, tags=tags))
        if no_tags:
            filters.append(lambda c: not c.labels)
        if title_regex:
            filters.append(search_for_regex)
        if filter_funcs:
            if callable(filter_funcs):
                filters.append(filter_funcs)
            elif type(filter_funcs) is list and all(callable(x) for x in filter_funcs):
                filters.extend(filter_funcs)
        if has_attachments is not None:
            filters.append(lambda c: c.get_attachments())
        if has_due_date:
            filters.append(lambda c: c.due_date)
        return filters

    @staticmethod
    def filter_cards(board, **kwargs):
        list_regex = kwargs.get('list_regex', None)
        filters = BoardTool.create_card_filters(**kwargs)
        # create a generator of cards to filter
        if list_regex is not None:
            cardsource = BoardTool.take_cards_from_lists(board, list_regex)
        else:
            cardsource = board.get_cards('open')
        for card in cardsource:
            if all(x(card) for x in filters):
                yield card

    @staticmethod
    def get_main_board(connection, config):
        '''use the configuration to get the main board & return it
        This function avoids py-trello's connection.list_boards() function as it produces O(N) network calls.
        This function is guaranteed to only produce 1 network call, in the trello.Board initialization below.
        '''
        # connection.boards is a response from the trello API unpacked as a list of dicts
        if config.board is None:
            # If no board name is passed, default to the first board
            board_json = connection.boards[0]
        else:
            possible = [b for b in connection.boards if b['name'] == config.board]
            if possible:
                board_json = possible[0]
            else:
                board_json = connection.boards[0]
        return trello.Board.from_json(connection.trello, json_obj=board_json)

    @staticmethod
    def get_inbox_list(connection, config):
        '''use the configuration to get the main board & list from
        Trello, return the list where new cards should go.
        '''
        board = BoardTool.get_main_board(connection, config)
        if getattr(config, 'inbox_list', False):
            return [l for l in board.open_lists() if l.name == config.inbox_list][0]
        else:
            return board.open_lists()[0]

    @staticmethod
    def list_lookup(board):
        return {o.name: o for o in board.get_lists('open')}

    @staticmethod
    def label_lookup(board):
        return {o.name: o for o in board.get_labels(limit=1000)}

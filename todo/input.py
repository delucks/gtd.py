'''user interface, user interaction functions'''
import re
import sys
import tty
import string
import trello
import shutil
import termios
import datetime
import itertools
import webbrowser
from functools import partial
from prompt_toolkit import prompt
from todo.misc import get_title_of_webpage, Colors
from prompt_toolkit.contrib.completers import WordCompleter
from todo.exceptions import GTDException
from todo.connection import TrelloConnection
from todo import __version__


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
    print('Press the character corresponding to your choice, selection will happen immediately. Ctrl+C to cancel')
    result = lookup.get(getch(), None)
    if result is not None:
        return list(options)[int(result)]
    else:
        return None


def tags_on_card(card, tags):
    '''Take in a comma-sep list of tag names, and ensure that
    each is on this card'''
    if card.list_labels:
        user_tags = set(tags.split(','))
        card_tags = set([l.name for l in card.list_labels])
        return user_tags.issubset(card_tags)
    else:
        return False


def triple_column_print(iterable):
    chunk_count = 3
    max_width = shutil.get_terminal_size().columns
    chunk_size = (max_width-4) // chunk_count
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
    def add_labels(card, label_choices):
        '''Give the user a way to toggle labels on this card by their
        name rather than by a numeric selection interface. Using
        prompt_toolkit, we have automatic completion which makes
        things substantially faster without having to do a visual
        lookup against numeric IDs
        :param trello.Card card: the card to modify
        :param dict label_choices: str->trello.Label, the names and objects of labels on this board
        '''
        label_names = [l for l in label_choices.keys()]
        label_completer = WordCompleter(label_names, ignore_case=True)
        while True:
            userinput = prompt('tag name (blank exits) > ', completer=label_completer).strip()
            if userinput == '':
                break
            elif userinput == 'ls':
                triple_column_print(label_names)
            elif userinput not in label_names:
                # TODO put a prompt here to create the tag name if it does not exist
                print('Unrecognized tag name {0}, try again'.format(userinput))
            else:
                label_obj = label_choices[userinput]
                try:
                    card.add_label(label_obj)
                    print('Added label {0}'.format(Colors.green + userinput + Colors.reset))
                except trello.exceptions.ResourceUnavailable:
                    # This label already exists on the card so remove it
                    card.remove_label(label_obj)
                    print('Removed label {0}'.format(Colors.red + userinput + Colors.reset))

    @staticmethod
    def smart_menu(card, f_display, list_choices, label_choices, color=None):
        '''make assumptions about what you want to do with a card and ask the user if they want to'''
        on = color if color else ''
        off = Colors.reset if color else ''
        f_display(card, True)
        if not card.list_labels:
            print('{0}No tags on this card yet, want to add some?{1}'.format(on, off))
            CardTool.add_labels(card, label_choices)
        if re.search('https?://', card.name):
            if prompt_for_confirmation('{0}Link in title detected, want to attach it & rename?{1}'.format(on, off), True):
                CardTool.title_to_link(card)
        if card.get_attachments():
            if prompt_for_confirmation('{0}Open attachments?{1}'.format(on, off), False):
                for l in [a.name for a in card.get_attachments()]:
                    webbrowser.open(l)
        commands = {
            'archive': 'mark this card as closed',
            'delete': 'permanently delete this card',
            'duedate': 'add a due date or change the due date',
            'help': 'display this help output',
            'move': 'move to a different list',
            'next': 'move on to the next card',
            'open': 'open all links on this card',
            'print': 'display this card',
            'rename': 'change title of this card',
            'tag': 'add or remove tags on this card',
            'quit': 'exit program'
        }
        command_completer = WordCompleter(commands.keys())
        while True:
            user_input = prompt('> ', completer=command_completer)
            if user_input in ['q', 'quit']:
                raise GTDException(0)
            elif user_input in ['n', 'next']:
                break
            elif user_input in ['p', 'print']:
                f_display(card, True)
            elif user_input in ['o', 'open']:
                for l in [a['name'] for a in card.get_attachments()]:
                    webbrowser.open(l)
            elif user_input == 'delete':
                card.delete()
                print('Card deleted')
                break
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
                    print('{0:<13}: {1}{2}{3}'.format(cname, on, cdesc, off))
            elif user_input in ['m', 'move']:
                if CardTool.move_to_list(card, list_choices):
                    break
            else:
                print('{0}{1}{2} is not a command, type "{0}help{2}" to view available commands'.format(on, user_input, off))

    @staticmethod
    def title_to_link(card):
        # assumes card.name is the link you want
        links = [n for n in card.name.split() if 'http' in n]
        existing_attachments = [a['name'] for a in card.get_attachments()]
        for l in links:
            if l not in existing_attachments:
                card.attach(url=l)
        # attempt to get the title of the link
        possible_title = get_title_of_webpage(links[0])
        if possible_title:
            CardTool.rename(card, default=possible_title)
        else:
            CardTool.rename(card)

    @staticmethod
    def rename(card, default=None):
        newname = input('Input new name for this card (blank for "{0}"): '.format(default or card.name)).strip()
        if newname:
            card.set_name(newname)
            # FIXME this hacks around a bug in the pytrello library, contribute it upstream
            #card.name = bytes(newname, 'utf8')
        else:
            if default:
                card.set_name(default)
                #card.name = bytes(default, 'utf8')

    @staticmethod
    def set_due_date(card):
        # prompt for the date
        input_date = ''
        while not re.match('^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$', input_date):
            input_date = input('Input a due date in the format of DD/MM/YYYY, May 1st = 01/05/2017: ').strip()
        date_args = [int(x) for x in input_date.split('/')[::-1]]
        input_datetime = datetime.datetime(*date_args, tzinfo=datetime.timezone.utc)
        card.set_due(input_datetime)
        return input_datetime

    @staticmethod
    def move_to_list(card, list_choices):
        '''Select labels to add to this card
        :param trello.Card card: the card to modify
        :param dict list_choices: str->trello.List, the names and objects of lists on this board
        '''
        dest = single_select(sorted(list_choices.keys()))
        if dest is not None:
            destination_list = list_choices[dest]
            card.change_list(destination_list.id)
            print('Moved to {0}'.format(destination_list.name))
            return destination_list
        else:
            print('Skipping!')
            return None


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
        target_lists = filter(
            lambda x: pattern.search(x.name),
            board.get_lists('open')
        )
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
            filters.append(lambda c: not c.list_labels)
        if title_regex:
            filters.append(lambda c: re.search(title_regex, c.name, regex_flags))
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
        '''use the configuration to get the main board & return it'''
        if config.board is None:
            # If no board name is passed, default to the first board
            return connection.trello.list_boards('open')[0]
        else:
            possible = [b for b in connection.trello.list_boards('open') if b.name == config.board]
            if possible:
                return possible[0]
            else:
                return connection.trello.list_boards('open')[0]

    @staticmethod
    def get_inbox_list(connection, config):
        '''use the configuration to get the main board & list from
        Trello, return the list where new cards should go.
        '''
        board = BoardTool.get_main_board(connection, config)
        if getattr(config, 'inbox_list', False):
            return [l for l in board.open_lists() if l.name == bytes(config.inbox_list, 'utf8')][0]
        else:
            return board.open_lists()[0]

    @staticmethod
    def list_lookup(board):
        return {o.name: o for o in board.get_lists('open')}

    @staticmethod
    def label_lookup(board):
        return {o.name: o for o in board.get_labels()}

    @staticmethod
    def list_and_label_length(board):
        '''return maximum string length of lists & labels '''
        max_list_len = len(max([l.name for l in board.get_lists('open')], key=len))
        max_label_len = len(max([l.name for l in board.get_labels()], key=len))
        return max_list_len, max_label_len

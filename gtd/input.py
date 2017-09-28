'''user interface, user interaction functions'''
import re
import sys
import tty
import string
import trello
import termios
import datetime
import webbrowser
from functools import partial
from gtd.exceptions import GTDException
from gtd.misc import get_title_of_webpage, Colors


def multiple_select(iterable):
    listed = list(iterable)
    for index, item in enumerate(listed):
        print('  [{0}] {1}'.format(index, item.decode('utf8')))
    while True:
        usersel = input('Input the numeric ID or IDs of the item(s) you want: ').strip()
        try:
            if ',' in usersel or ' ' in usersel:
                delimiter = ',' if ',' in usersel else ' '
                indicies = [int(i) for i in usersel.split(delimiter)]
            else:
                indicies = [int(usersel)]
            break
        except ValueError:
            print('You gave a malformed input!')
    return [listed[i] for i in indicies]


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
        print('[{0}] {1}'.format(assigned, chunk.decode('utf8')))
    print('Press the character corresponding to your choice, selection will happen immediately. Ctrl+C to cancel')
    result = lookup.get(getch(), None)
    if result is not None:
        return list(options)[int(result)]
    else:
        return None


def filter_card_by_tag(card, tag):
    if card.list_labels:
        return tag in [l.name.decode('utf8') for l in card.list_labels]
    else:
        return False


class CardTool:
    '''This static class holds functionality to do atomic modifications on certain cards.
    These methods are used inside of the user interaction parts of the codebase as a way of doing the same operation across
    different UI components.
    '''
    # TODO add type hints
    @staticmethod
    def add_labels(card, label_choices):
        '''Select labels to add to this card
        :param trello.Card card: the card to modify
        :param dict label_choices: str->trello.Label, the names and objects of labels on this board
        '''
        done = False
        newlabels = []
        while not done:
            label_to_add = multiple_select(label_choices)
            newlabels.extend([label_choices[l] for l in label_to_add])
            done = prompt_for_confirmation('Are you done tagging?', default=True)
        if newlabels:
            for label in newlabels:
                try:
                    card.add_label(label)
                except trello.exceptions.ResourceUnavailable:
                    print('Tag {0} is already present!'.format(label))
        return newlabels

    @staticmethod
    def title_to_link(card):
        # assumes card.name is the link you want
        links = [n for n in card.name.decode('utf8').split() if 'http' in n]
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
        newname = input('Input new name for this card (blank for "{0}"): '.format(default or card.name.decode('utf8'))).strip()
        if newname:
            card.set_name(newname)
            # FIXME this hacks around a bug in the pytrello library, contribute it upstream
            card.name = bytes(newname, 'utf8')
        else:
            if default:
                card.set_name(default)
                card.name = bytes(default, 'utf8')

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
        dest = single_select(list_choices.keys())
        if dest is not None:
            destination_list = list_choices[dest]
            card.change_list(destination_list.id)
            print('Moved to {0}'.format(destination_list.name.decode('utf8')))
            return destination_list
        else:
            print('Skipping!')
            return None

    @staticmethod
    def review_card(card, f_display, list_choices, label_choices, main_color=None):
        '''present the user with an option-based interface to do every operation on
        a single card
        :param trello.Card card: the card to modify
        :param function f_display: function to call with a string in order to draw the card
        :param str main_color: ansi escape code for the color you want this to be pretty-printed as
        '''
        on = main_color if main_color else ''
        off = Colors.reset if main_color else ''
        header = ''.join([
            '{on}D{off}elete, '
            '{on}T{off}ag, '
            '{on}A{off}ttach Title, '
            'ar{on}C{off}hive, '
            '{on}P{off}rint Card, '
            '{on}R{off}ename, '
            'd{on}U{off}e Date, '
            '{on}M{off}ove, '
            '{on}N{off}ext, '
            '{on}Q{off}uit'
        ]).format(on=on, off=off)
        if card.get_attachments():
            header = '{on}O{off}pen attachment, '.format(on=on, off=off) + header
        choice = ''
        f_display(card, True)
        while choice != 'N' and choice != 'D':
            print(header)
            choice = input('Input option character: ').strip().upper()
            if choice == 'D':
                card.delete()
                print('Card deleted')
            elif choice == 'C':
                card.set_closed(True)
                print('Card archived')
            elif choice == 'T':
                CardTool.add_labels(card, label_choices)
            elif choice == 'A':
                CardTool.title_to_link(card)
            elif choice == 'P':
                f_display(card, True)
            elif choice == 'R':
                CardTool.rename(card)
            elif choice == 'U':
                CardTool.set_due_date(card)
            elif choice == 'M':
                if CardTool.move_to_list(card, list_choices):
                    break
            elif choice == 'Q':
                raise GTDException(0)
            elif choice == 'N':
                pass
            elif choice == 'O':
                for l in [a['name'] for a in card.get_attachments()]:
                    webbrowser.open(l)
            else:
                print('Invalid option {0}'.format(choice))


class BoardTool:
    '''given a board, this one handles operations on individual cards and dynamically generating lookups that make certain
    operations faster
    provides convenience methods for doing certain repeatable tasks on the main board and lists described by the configuration properties
    Note that this will break if you have a tag in your Board named NOTAG

    :param str primary_list: name of the list you want to use for new cards
    '''
    def __init__(self, connection):
        self.trello = connection.trello
        self.config = connection.config
        self.main_board = self._filter_by_name(self.trello.list_boards(), self.config['board_name'])
        # Determine the list for inbound cards
        configured_list = self.config.get('inbox_list', False)
        if configured_list:
            main_list = self._filter_by_name(self.main_board.get_lists('open'), configured_list)
            if not main_list:
                print('[FATAL] The provided list name did not match any lists in {0}!'.format(self.main_board.name.decode('utf8')))
                raise GTDException(1)
            self.main_list = main_list
        else:
            self.main_list = self.get_first_list(self.main_board)
        # These are dicts of list&tag names -> objects to make subsequent reads faster
        self.label_lookup = self._make_name_lookup(self.main_board.get_labels())
        self.list_lookup = self._make_name_lookup(self.main_board.get_lists('open'))
        # The value passed to get_cards() if you want cards with no tags
        self.magic_value = 'NOTAG'

    def _filter_by_name(self, iterable, name):
        try:
            return set(b for b in iterable if name.lower() in b.name.decode('utf8').lower()).pop()
        except KeyError:
            return []

    def _make_name_lookup(self, object_grouping):
        return {o.name: o for o in object_grouping}

    def _cardpipe(self, target_lists):
        '''I wish their API had a "search" feature so this doesn't have to be
        N^2'''
        for cardlist in target_lists:
            for card in cardlist.list_cards():
                yield card

    def get_first_list(self, board_obj):
        return board_obj.open_lists()[0]

    def get_cards(self, target_lists=[], tag=None, title_regex=None, filterspec=None, has_attachments=None, has_due_date=None, regex_flags=0):
        '''Find cards on the main board that match our filters, hand them back
        as a generator'''
        cardsource = self._cardpipe(target_lists) if target_lists else self.main_board.get_cards('open')
        filters = []
        if tag == self.magic_value:
            filters.append(lambda c: not c.list_labels)
        elif tag:
            filters.append(partial(filter_card_by_tag, tag=tag))
        if title_regex:
            filters.append(lambda c: re.search(title_regex, c.name.decode('utf8'), regex_flags))
        if filterspec and callable(filterspec):
            filters.append(filterspec)
        if has_attachments:
            filters.append(lambda c: has_attachments and c.get_attachments())
        if has_due_date:
            filters.append(lambda c: c.due_date)
        for card in cardsource:
            keep = True
            for f in filters:
                if not f(card):
                    keep = False
            if keep:
                yield card

    def get_list(self, name):
        return self.list_lookup.get(bytes(name, 'utf8'), None)

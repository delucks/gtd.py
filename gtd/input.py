'''user interface, user interaction functions'''
import re
import sys
import tty
import string
import termios
import datetime
from functools import partial


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
    remainder = list(set(preferred_keys) - set(string.ascii_lowercase))
    all_keys = preferred_keys + remainder
    for idx, chunk in enumerate(options):
        assigned = all_keys[idx]
        lookup[assigned] = idx
        print('[{0}] {1}'.format(assigned, chunk.decode('utf8')))
    print('Press the character corresponding to your choice, selection will happen immediately. Ctrl+C to cancel')
    result = lookup.get(getch(), None)
    if result:
        return list(options)[int(result)]
    else:
        return None


def filter_card_by_tag(card, tag):
    if card.list_labels:
        return tag in [l.name.decode('utf8') for l in card.list_labels]
    else:
        return False


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
        list_name = self.config.list or self.config['list_names']['incoming']
        main_list = self._filter_by_name(self.main_board.get_lists('open'), list_name)
        if main_list:
            self.main_list = main_list
        else:
            print('[FATAL] The provided list name did not match any lists in {0}!'.format(self.main_board.name.decode('utf8')))
            raise GTDException(1)
        self.label_lookup = self._make_name_lookup(self.main_board.get_labels())
        self.list_lookup = self._make_name_lookup(self.main_board.get_lists('open'))
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

    def get_cards(self, target_lists=[], tag=None, title_regex=None, filterspec=None, has_attachments=None, has_due_date=None):
        '''Find cards on the main board that match our filters, hand them back
        as a generator'''
        cardsource = self._cardpipe(target_lists) if target_lists else self.main_board.get_cards('open')
        filters = []
        if tag == self.magic_value:
            filters.append(lambda c: not c.list_labels)
        elif tag:
            filters.append(partial(filter_card_by_tag, tag=tag))
        if title_regex:
            filters.append(lambda c: re.search(title_regex, c.name.decode('utf8')))
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

    def add_labels(self, card):
        done = False
        newlabels = []
        while not done:
            label_to_add = multiple_select(self.label_lookup.keys())
            newlabels.extend([self.label_lookup[l] for l in label_to_add])
            done = prompt_for_confirmation('Are you done tagging?', default=True)
        if newlabels:
            for label in newlabels:
                try:
                    card.add_label(label)
                except trello.exceptions.ResourceUnavailable:
                    print('Tag {0} is already present!'.format(label))
        return newlabels

    def set_due_date(self, card):
        # prompt for the date
        input_date = ''
        while not re.match('^[0-9]{2}\/[0-9]{2}\/[0-9]{4}$', input_date):
            input_date = input('Input a due date in the format of DD/MM/YYYY, May 1st = 01/05/2017: ').strip()
        date_args = [int(x) for x in input_date.split('/')[::-1]]
        input_datetime = datetime.datetime(*date_args, tzinfo=datetime.timezone.utc)
        card.set_due(input_datetime)
        return input_datetime

    def _get_title_of_webpage(self, url):
        headers = {'User-Agent': 'gtd.py version ' + __version__}
        resp = requests.get(url, headers=headers)
        as_text = resp.text
        return as_text[as_text.find('<title>') + 7:as_text.find('</title>')]

    def title_to_link(self, card):
        # assumes card.name is the link you want
        links = [n for n in card.name.decode('utf8').split() if 'http' in n]
        existing_attachments = [a['name'] for a in card.get_attachments()]
        for l in links:
            if l not in existing_attachments:
                card.attach(url=l)
        # attempt to get the title of the link
        possible_title = self._get_title_of_webpage(links[0])
        if possible_title:
            self.rename(card, default=possible_title)
        else:
            self.rename(card)

    def rename(self, card, default=None):
        newname = input('Input new name for this card (blank for "{0}"): '.format(default or card.name.decode('utf8'))).strip()
        if newname:
            card.set_name(newname)
            # FIXME this hacks around a bug in the pytrello library, contribute it upstream
            card.name = bytes(newname, 'utf8')
        else:
            if default:
                card.set_name(default)
                card.name = bytes(default, 'utf8')

    def move_to_list(self, card):
        dest = single_select(self.list_lookup.keys())
        if dest:
            destination_list = self.list_lookup[dest]
            card.change_list(destination_list.id)
            print('Moved to {0}'.format(destination_list.name.decode('utf8')))
            return destination_list
        else:
            print('Skipping!')
            return None

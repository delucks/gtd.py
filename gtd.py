#!/usr/bin/env python3
'''Incremental development is a thing dude
TODOs:
- Option to work on a list other than "Inbound"
- "Daily review" mode where you review the active and blocked ones as well
- Add a "batch mode" that allows you to only do one action (add labels, delete, ...) on all the cards at once

< Pasted the rest of this comment in from the old script >
functionality we want:
    Some kind of prompted/scheduled review of all inbound and/or holding items
    Easy categorization interface, preferrably with single button push decisions
    Displaying the decision tree that I follow to operate the program correctly
    Extensive documentation of what destinations things are going to, as well
        as an audit trail of logging.
    Ability to bookmark links that are in the incoming basket with an automatic title
how will users interact with my program?
    users? me. other people if they want.
    interface?
        ncurses
            easy to navigate, can draw a kind of UI for myself
            restricts the terminals this can work on
            harder to program
            could have cool things like certain list movements being triggered by a single keystroke
        $EDITOR
            take all card names and metadata, throw them into a temp file,
            open it with $EDITOR and do all the rearrangement manually
            read the new structure, take it as source of truth, and
            update the API accordingly
'''
import re
import sys
import tty
import string
import logging
import termios
import readline  # noqa
import datetime
import argparse

import trello
import yaml


class Colors:
    esc = '\033'
    black = esc + '[0;30m'
    red = esc + '[0;31m'
    green = esc + '[0;32m'
    yellow = esc + '[0;33m'
    blue = esc + '[0;34m'
    purple = esc + '[0;35m'
    cyan = esc + '[0;36m'
    white = esc + '[0;37m'
    reset = esc + '[0m'


__version__ = '0.0.6'
__banner__ = '''Welcome to{1.green}

  __|_ _| ._
 (_||_(_|o|_)\/
  _|      |  /{1.red}

version {0}
by delucks{1.reset}
'''.format(__version__, Colors)

_workflow_description = '''
1. 
'''


def parse_configuration(configfile='gtd.yaml'):
    '''load user-defined configuration for what boards and lists to use
    '''
    logging.info('Opening configuration file...')
    with open(configfile, 'r') as config_yaml:
        logging.info('Loading configuration properties...')
        return yaml.safe_load(config_yaml)


def initialize_trello(config):
    '''Initializes our connection to the trello API
    '''
    logging.info('Connecting to the Trello API...')
    trello_client = trello.TrelloClient(
        api_key=config['trello']['api_key'],
        api_secret=config['trello']['api_secret'],
        token=config['trello']['oauth_token'],
        token_secret=config['trello']['oauth_token_secret']
    )
    logging.info('Connected to Trello.')
    return trello_client


def _filter_by_name(iterable, name):
    return [b for b in iterable if b.name == bytes(name, 'utf8')][0]


def _colorize(lbl, msg, colorstring=Colors.blue):
    return '  {0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)


def display_card(card):
    created = card.create_date
    print('{1.red}Card {1.reset}{0}'.format(card.id, Colors))
    print(_colorize('Name:', card.name.decode('utf8')))
    print(_colorize('Created on:', '{0} ({1})'.format(created, created.timestamp())))
    print(_colorize('Age:', datetime.datetime.now(datetime.timezone.utc) - created))
    if card.labels:
        print(_colorize('Labels:', ','.join([l.name.decode('utf8') for l in card.labels])))
    if card.get_attachments():
        print(_colorize('Attachments:', ','.join([a['name'] for a in card.get_attachments()])))
    if card.due:
        diff = card.due_date - datetime.datetime.now(datetime.timezone.utc)
        if diff < datetime.timedelta(0):
            display = Colors.red
        else:
            display = Colors.green
        print(_colorize('Due:', card.due_date, display))
        print(_colorize('Remaining:', diff, display))


def prompt_for_user_choice(iterable):
    iterable = list(iterable)
    for index, item in enumerate(iterable):
        print('  [{0}] {1}'.format(index, item.decode('utf8')))
    broken = False
    while not broken:
        usersel = input('Input the numeric ID or IDs of the item(s) you want: ').strip()
        try:
            if ',' in usersel or ' ' in usersel:
                delimiter = ',' if ',' in usersel else ' '
                indicies = [int(i) for i in usersel.split(delimiter)]
            else:
                indicies = [int(usersel)]
            broken = True
        except ValueError:
            print('You gave a malformed input!')
    return [iterable[i] for i in indicies]


def prompt_for_confirmation(message, default=False):
    while True:
        print(message)
        choice = getch() #input(message).strip().lower()
        if choice == 'y' or choice == 'n' or choice == '\r':
            break
        else:
            print('Input was not y, nor was it n. Enter is OK')
    return choice == 'y' if choice != '\r' else default


def add_labels(card, lookup):
    done = False
    newlabels = []
    while not done:
        label_to_add = prompt_for_user_choice(lookup.keys())
        newlabels.extend([lookup[l] for l in label_to_add])
        done = prompt_for_confirmation('Are you done adding labels? (Y/n) ', default=True)
    return newlabels


def move_to_list(card, lookup, current):
    dest = quickmove(lookup.keys())
    if lookup[dest].id == current.id:
        logging.info('Did not want to move')
        return False
    else:
        return lookup[dest]


def make_readable(object_grouping):
    return {o.name: o for o in object_grouping}


def apply_filters(cardlist, reverse=False, regex=None):
    cards = list(cardlist) 
    if regex:
        selected = [c for c in cardlist if re.search(regex, c.name.decode('utf8'))]
    else:
        selected = cards
    if reverse:
        return reversed(selected)
    else:
        return selected

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    except KeyboardInterrupt:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def quickmove(iterable):
    '''a faster selection interface: get the terminal width and draw options
    in a table squashed to the width of the terminal. Assign a unique one-char
    identifier to each option, and read only one character from stdin. Match that
    one character against the options, and return the one that matches. Give users
    an error if they try to use a nonexistent char
    We have 26 + 10 alphanumeric chars we can easily use, so there's a practical
    limit of 36 options to this method
    '''
    #width, height = shutil.get_terminal_size()
    #print(width, height)
    lookup = {}
    preferred_keys = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"]
    remainder = list(set(preferred_keys) - set(string.ascii_lowercase))
    all_keys = preferred_keys + remainder
    for idx, chunk in enumerate(iterable):
        assigned = all_keys[idx]
        lookup[assigned] = idx
        print('[{0}] {1}'.format(assigned, chunk.decode('utf8')))
    print('Press the character for the desired option. Selection will happen immediately upon keystroke')
    req = getch()
    return list(iterable)[int(lookup.get(req, None))]


def review_card(card, label_lookup, list_lookup, inbound):
    mandatory_choice_footer = '{0.blue}D{0.reset}elete, {0.blue}L{0.reset}abels, {0.blue}M{0.reset}ove, {0.blue}S{0.reset}kip, {0.blue}Q{0.reset}uit'.format(Colors)
    choice = ''
    while choice != 'S' and choice != 'D':
        print(mandatory_choice_footer)
        choice = input('Input option character: ').strip().upper()
        if choice == 'D':
            card.delete()
            print('Card deleted')
            break
        elif choice == 'L':
            labels = add_labels(card, label_lookup)
            if labels:
                for label in labels:
                    try:
                        card.add_label(label)
                    except trello.exceptions.ResourceUnavailable:
                        print('Label {0} is already present!'.format(label))
        elif choice == 'M':
            destination = move_to_list(card, list_lookup, inbound)
            if destination:
                card.change_list(destination.id)
                print('Moved to {0}'.format(destination.name.decode('utf8')))
            else:
                print('Staying in inbound')
            break
        elif choice == 'Q':
            sys.exit(1)
        else:
            pass


def main():
    config_properties = parse_configuration()
    p = argparse.ArgumentParser(description='gtd.py version {0}'.format(__version__))
    p.add_argument('-r', '--reverse', help='process the list of cards in reverse', action='store_true')
    p.add_argument('-m', '--match', help='provide a regex to filter the card names on', default=None)
    p.add_argument('-l', '--list', help='list name to use', default=config_properties['list_names']['incoming'])
    commands = p.add_subparsers(dest='command')
    commands.add_parser('help')
    show = commands.add_parser('show')
    show.add_argument('type', choices=('lists', 'cards'), default='lists')
    review = commands.add_parser('review')
    add = commands.add_parser('add')  # TODO add argument for tags to add
    add.add_argument('title', help='title for the new card')
    add.add_argument('-m', '--message', help='append a description for the new card')
    args = p.parse_args()
    if args.command == 'help':
        p.print_help()
        return True

    trello = initialize_trello(config_properties)
    main_board = _filter_by_name(trello.list_boards(), config_properties['board_name'])
    inbound_list = _filter_by_name(main_board.get_lists('open'), args.list)
    cards = apply_filters(inbound_list.list_cards(), reverse=args.reverse, regex=args.match)

    print(__banner__)
    if args.command == 'show':
        if args.type == 'lists':
            for l in main_board.get_lists('open'):
                print(l.name.decode('utf8'))
        elif args.type == 'cards':
            for card in cards:
                display_card(card)
    elif args.command == 'add':
        logging.info('Adding new card with title {0} and description {1} to list {2}'.format(args.title, args.message, inbound_list))
        returned = inbound_list.add_card(name=args.title, desc=args.message)
        print('Successfully added card {0}'.format(returned))
    else: # args.command == 'review':
        label_lookup = make_readable(main_board.get_labels())
        list_lookup = make_readable(main_board.get_lists('open'))
        for card in cards:
            display_card(card)
            review_card(card, label_lookup, list_lookup, inbound_list)
        print('All done, have a great day!')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Quitting!')
        sys.exit(0)

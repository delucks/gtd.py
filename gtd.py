#!/usr/bin/env python3
'''Incremental development is a thing dude
Notes:
- This only works on Unix systems and has only been tested on Linux
- This only works when your terminal supports colors via escape codes
TODOs:
- "Daily review" mode where you review the active and blocked ones as well
- Add an audit trail of logging or metrics emission so you can see where things are going
- Ability to bookmark links that are in the incoming basket with an automatic title
- Translate #tag into adding that tag, then removing that part of the title
- "show" arg with a flexible argument scheme that also allows you to specify tag names and names of lists to dump
- Method entirely for filtering the list of cards down to the user selection- we shouldn't be doing that in main()
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
import webbrowser

import trello
import yaml

__version__ = '0.0.7'


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


_banner = ''' __|_ _| ._     version {1.green}{0}{1.reset}
(_||_(_|{1.green}o{1.reset}|_)\/  by {1.green}delucks{1.reset}
 _|      |  /
'''.format(__version__, Colors)
_workflow_description = '''1. Collect absolutely everything that can take your attention into "Inbound"
2. Filter:
    Nonactionable -> Static Reference or Delete
    Takes < 2 minutes -> Do now, then Delete
    Not your responsibility -> "Holding" or "Blocked" with follow-up
    Something to communicate -> messaging lists
    Your responsibility -> Your lists
3. Write "final" state of each task and "next" state of each task
4. Categorize inbound items into lists based on action type required (call x, talk to x, meet x...)
5. Reviews:
    Daily -> Go through "Inbound" and "Doing"
    Weekly -> Additionally, go through "Holding", "Blocked", and messaging lists
6. Do

The goal is to get everything except the current task out of your head
and into this trusted system external to your mind.
'''


def parse_configuration(configfile='gtd.yaml'):
    '''load user-defined configuration for what boards and lists to use
    '''
    logging.info('Opening configuration file...')
    with open(configfile, 'r') as config_yaml:
        logging.info('Loading configuration properties...')
        properties = yaml.safe_load(config_yaml)
        return validate_config(properties)


def validate_config(config):
    try:
        config['trello']['api_key']
        config['trello']['api_secret']
        config['trello']['oauth_token_secret']
        config['trello']['oauth_token']
        config['board_name']
        config['list_names']['incoming']
        return config
    except KeyError as e:
        print('A required property {0} in your configuration was not found!'.format(e))
        return False


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
    return [b for b in iterable if bytes(name, 'utf8') in b.name][0]


def _colorize(lbl, msg, colorstring=Colors.blue):
    return '  {0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)


def display_card(card):
    created = card.create_date
    print('{1.red}Card {1.reset}{0}'.format(card.id, Colors))
    print(_colorize('Name:', card.name.decode('utf8')))
    print(_colorize('Created on:', '{0} ({1})'.format(created, created.timestamp())))
    print(_colorize('Age:', datetime.datetime.now(datetime.timezone.utc) - created))
    if card.labels:
        print(_colorize('Tags:', ','.join([l.name.decode('utf8') for l in card.labels])))
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
    listed = list(iterable)
    for index, item in enumerate(listed):
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


def add_labels(card, lookup):
    done = False
    newlabels = []
    while not done:
        label_to_add = prompt_for_user_choice(lookup.keys())
        newlabels.extend([lookup[l] for l in label_to_add])
        done = prompt_for_confirmation('Are you done tagging?', default=True)
    if newlabels:
        for label in newlabels:
            try:
                card.add_label(label)
            except trello.exceptions.ResourceUnavailable:
                print('Tag {0} is already present!'.format(label))
    return newlabels


def move_to_list(card, lookup, current):
    dest = quickmove(lookup.keys())
    if lookup[dest].id == current.id:
        logging.info('Did not want to move')
        print('Staying in inbound')
        return False
    else:
        destination_list = lookup[dest]
        card.change_list(destination_list.id)
        print('Moved to {0}'.format(destination_list.name.decode('utf8')))
        return destination_list


def make_name_lookup(object_grouping):
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
        if ch == '\x03':
            raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def quickmove(iterable):
    '''a faster selection interface
    Assign a unique one-char identifier to each option, and read only one
    character from stdin. Match that one character against the options
    Downside: you can only have 30ish options
    '''
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
    '''present the user with an option-based interface to do every operation on
    a single card'''
    header = (
        '{0.blue}D{0.reset}elete, '
        '{0.blue}T{0.reset}ag, '
        '{0.blue}M{0.reset}ove, '
        '{0.blue}S{0.reset}kip, '
        '{0.blue}Q{0.reset}uit'
    ).format(Colors)
    if card.get_attachments():
        header = '{0.blue}O{0.reset}pen link, '.format(Colors) + header
    choice = ''
    while choice != 'S' and choice != 'D':
        print(header)
        choice = input('Input option character: ').strip().upper()
        if choice == 'D':
            card.delete()
            print('Card deleted')
            break
        elif choice == 'T':
            add_labels(card, label_lookup)
        elif choice == 'M':
            if move_to_list(card, list_lookup, inbound):
                break
        elif choice == 'Q':
            raise KeyboardInterrupt
        elif choice == 'O':
            if not 'link' in header:
                print('This card does not have an attachment!')
            else:
                webbrowser.open([a['name'] for a in card.get_attachments()][0])
        else:
            pass


def main():
    config_properties = parse_configuration()
    if not config_properties:
        sys.exit(1)
    p = argparse.ArgumentParser(description='gtd.py version {0}'.format(__version__))
    p.add_argument('-r', '--reverse', help='process the list of cards in reverse', action='store_true')
    p.add_argument('-m', '--match', help='provide a regex to filter the card names on', default=None)
    p.add_argument('-l', '--list', help='list name to use', default=config_properties['list_names']['incoming'])
    commands = p.add_subparsers(dest='command')
    commands.add_parser('help')
    commands.add_parser('workflow')
    batch = commands.add_parser('batch')
    batch.add_argument('type', choices=('tag', 'move', 'delete'), default='move')
    show = commands.add_parser('show')
    show.add_argument('type', choices=('lists', 'cards', 'tags'), default='lists')
    review = commands.add_parser('review')
    add = commands.add_parser('add')  # TODO add argument for tags to add
    add.add_argument('title', help='title for the new card')
    add.add_argument('-m', '--message', help='append a description for the new card')
    args = p.parse_args()
    if args.command == 'help':
        p.print_help()
        return True
    elif args.command == 'workflow':
        print(_workflow_description)
        return True

    trello = initialize_trello(config_properties)
    main_board = _filter_by_name(trello.list_boards(), config_properties['board_name'])
    inbound_list = _filter_by_name(main_board.get_lists('open'), args.list)
    cards = apply_filters(inbound_list.list_cards(), reverse=args.reverse, regex=args.match)

    print(_banner)
    if args.command == 'show':
        if args.type == 'lists':
            for l in main_board.get_lists('open'):
                print(l.name.decode('utf8'))
        elif args.type == 'cards':
            for card in cards:
                display_card(card)
        else: # args.type == 'tags':
            for t in main_board.get_labels():
                print(t.name.decode('utf8'))
    elif args.command == 'add':
        logging.info('Adding new card with title {0} and description {1} to list {2}'.format(args.title, args.message, inbound_list))
        returned = inbound_list.add_card(name=args.title, desc=args.message)
        print('Successfully added card {0}'.format(returned))
    elif args.command == 'batch':
        if args.type == 'move':
            list_lookup = make_name_lookup(main_board.get_lists('open'))
            for card in cards:
                display_card(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    move_to_list(card, list_lookup, inbound_list)
        elif args.type == 'delete':
            for card in cards:
                display_card(card)
                if prompt_for_confirmation('Should we delete this card?'):
                    card.delete()
                    print('Bye!')
        else: # args.type == 'tag'
            label_lookup = make_name_lookup(main_board.get_labels())
            for card in cards:
                display_card(card)
                if prompt_for_confirmation('Want to tag this one?'):
                    add_labels(card, label_lookup)
        print('Batch completed')
    else: # args.command == 'review':
        label_lookup = make_name_lookup(main_board.get_labels())
        list_lookup = make_name_lookup(main_board.get_lists('open'))
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

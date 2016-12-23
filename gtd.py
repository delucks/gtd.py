'''Incremental development is a thing dude'''
import logging
import readline
from trello import TrelloClient
import yaml

__version__ = '0.0.2'
__banner__ = '''
Welcome to
  __|_ _| ._    
 (_||_(_|o|_)\/ 
  _|      |  /  
version {0}
by delucks
'''.format(__version__)


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
    trello_client = TrelloClient(
        api_key=config['trello']['api_key'],
        api_secret=config['trello']['api_secret'],
        token=config['trello']['oauth_token'],
        token_secret=config['trello']['oauth_token_secret']
    )
    logging.info('Connected to Trello.')
    return trello_client


def filter_them(iterable, name):
    return [b for b in iterable if b.name == bytes(name, 'utf8')][0]


def display_card(card):
    # TODO add due date
    print('Card {0}'.format(card.id))
    print('  Name: {0}'.format(card.name.decode('utf8')))
    print('  Created on: {0} ({1})'.format(card.create_date.timestamp(), card.create_date))
    if card.labels:
        print('  Labels: {0}'.format(','.join([l.name.decode('utf8') for l in card.labels])))
    if card.get_attachments():
        print('  Attachments: {0}'.format(','.join([a['name'] for a in card.get_attachments()])))
    if card.due:
        print('  Due: {0}'.format(card.due_date))


def prompt_for_user_choice(iterable):
    iterable = list(iterable)
    for index, item in enumerate(iterable):
        print('[{0}] {1}'.format(index, item.decode('utf8')))
    broken = False
    while not broken: #index <= 0 or index > len(iterable):
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
        choice = input(message).strip().lower()
        if choice == 'y' or choice == 'n' or choice == '':
            break
        else:
            print('Input was not y nor n, partner. Enter is OK if you meant to use the default')
    return choice == 'y' if choice != '' else default


def add_labels(card, lookup):
    if prompt_for_confirmation('Would you like to add labels? (y/N) '):
        done = False
        newlabels = []
        while not done:
            label_to_add = prompt_for_user_choice(lookup.keys())
            newlabels.extend([lookup[l] for l in label_to_add])
            done = prompt_for_confirmation('Are you done adding labels? (Y/n) ', default=True)
        return newlabels
    else:
        logging.info('User did not add labels')
        return False


def move_to_list(card, lookup, current):
    dest = prompt_for_user_choice(lookup.keys())[0]
    if lookup[dest] == current:
        logging.info('Did not want to move')
        return False
    else:
        return lookup[dest]

def make_readable(object_grouping):
    return {o.name: o for o in object_grouping}


config_properties = parse_configuration()
trello = initialize_trello(config_properties)

main_board = filter_them(trello.list_boards(), config_properties['board_name'])
inbound_list = filter_them(main_board.get_lists('open'), config_properties['list_names']['incoming'])
other_lists = main_board.get_lists('open')
all_labels = main_board.get_labels()

label_lookup = make_readable(all_labels)
list_lookup = make_readable(other_lists)

print(__banner__)
for card in inbound_list.list_cards():
    display_card(card)
    labels = add_labels(card, label_lookup)
    if labels:
        for label in labels:
            card.add_label(label)
    destination = move_to_list(card, list_lookup, inbound_list)
    if destination:
        card.change_list(destination.id)
        print('Moved to {0}'.format(destination.name.decode('utf8')))
print('Good show, chap. Have a great day')

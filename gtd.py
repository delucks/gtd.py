'''Incremental development is a thing dude'''
import logging
import readline
from trello import TrelloClient
import yaml


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
    # TODO add multiselect
    for index, item in enumerate(iterable):
        print('[{0}] {1}'.format(index+1, item.decode('utf8')))
    index = 0
    while index <= 0 or index > len(iterable):
        try:
            index = int(input('Input the numeric ID of the item you want: '))
        except ValueError:
            print('Was that an integer? Study your algebra')
    return list(iterable)[index-1]

def prompt_for_confirmation(message):
    while True:
        choice = input(message).strip().lower()
        if choice == 'y' or choice == 'n':
            break
        else:
            print('Input was not y nor n, partner')
    return choice == 'y'

def add_labels(card, lookup):
    if prompt_for_confirmation('Would you like to add labels? (y/n) '):
        done = False
        newlabels = []
        while not done:
            label_to_add = prompt_for_user_choice(lookup.keys())
            newlabels.append(lookup[label_to_add])
            done = prompt_for_confirmation('Are you done adding labels? (y/n) ')
        return newlabels
    else:
        logging.info('User did not add labels')
        return False

def move_to_list(card, lookup, current):
    dest = prompt_for_user_choice(lookup.keys())
    if dest == current:
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

for card in inbound_list.list_cards():
    display_card(card)
    labels = add_labels(card, label_lookup)
    if labels:
        for label in labels:
            card.add_label(label)
    destination = move_to_list(card, list_lookup, inbound_list)
    if destination:
        card.change_list(destination.id)
        print('Moved to {d.name}'.format(d=destination))

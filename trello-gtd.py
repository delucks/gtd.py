#!/usr/bin/env python3

# implementation of a getting things done style command line utiltiy using python and the trello API
# uses a configuration file for things like API keys, board names, etc

'''
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
design ideas
    MVC may be an appropriate pattern here, especially with the ncurses option
    $EDITOR would just need state and controller to diff the states and update API
'''

import sys
import logging

from trello import TrelloClient
import yaml

logging.basicConfig(level=logging.DEBUG)
stringerize = lambda x: [b.name.decode('utf-8') for b in x]

# load user-defined configuration for what boards and lists to use

def parse_configuration(configfile='gtd.config.yaml'):
    logging.info('Opening configuration file...')
    with open(configfile, 'r') as config_yaml:
        logging.info('Loading configuration properties...')
        return yaml.safe_load(config_yaml)

# TODO initialize google calendar API client

class GTD_Controller:
    def __init__(self, config):
        self.config = config
        self.trello = self.initialize_trello()
        self.board = self.validate_config()

    def initialize_trello(self):
        '''Initializes our connection to the trello API
        '''
        trello_client = TrelloClient(
            api_key=self.config['trello']['api_key'],
            api_secret=self.config['trello']['api_secret'],
            token=self.config['trello']['oauth_token'],
            token_secret=self.config['trello']['oauth_token_secret']
        )
        return trello_client

    def validate_config(self):
        '''Validates that all required lists and boards exist
        Returns the selected Board on success, or False if failure
        '''
        # hit trello API to make sure the board exists
        board_names = stringerize(self.trello.list_boards())
        if self.config['board_name'] not in board_names:
            logging.fatal('Board {0} not found in board list!'.format(
                self.config['board_name']
            ))
            return False
        else:
            fb = lambda x: x.name.decode('utf-8') == self.config['board_name']
            target_board = next(filter(fb, self.trello.list_boards()))
            logging.info('Target board {0} exists'.format(target_board))
        # TODO may be nice to display a message about when the board was last modified here
        # Check for existence of all configuration-requested lists
        board_list_names = stringerize(target_board.get_lists('open'))
        config_lists = [v for k, v in self.config['list_names'].items() if v]
        for requested_list in config_lists:
            if requested_list not in board_list_names:
                logging.fatal('List {0} not found in board {1}'.format(
                    requested_list, target_board.name
                ))
                return False
            else:
                logging.debug('List {0} exists...'.format(requested_list))
        logging.info('All boards/lists exist')
        return target_board

    def dump_list_yaml(self):
        shortened = {
            i.name.decode('utf-8'): i.id for i in self.board.get_lists('open')
        }
        logging.debug('Dumping {0} to yaml...'.format(shortened))
        return yaml.dump(shortened, default_flow_style=False)

config_properties = parse_configuration()
gtd = GTD_Controller(config_properties)
logging.info(gtd.dump_list_yaml())

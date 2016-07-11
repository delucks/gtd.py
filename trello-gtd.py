#!/usr/bin/env python3
'''implementation of a getting things done style command line utiltiy
using python and the trello API. Uses a configuration file for things like API
keys, board names, etc

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
import argparse

from trello import TrelloClient
import yaml

VERSION='0.0.2'

logging.basicConfig(level=logging.INFO)
stringerize = lambda x: [b.name.decode('utf-8') for b in x]

def parse_configuration(configfile='gtd.config.yaml'):
    '''load user-defined configuration for what boards and lists to use
    '''
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

    # Discovery & Initialization steps

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
        self.lists = {}
        # TODO validation that all the required list names exist in the config file
        for list_label, requested_list in self.config['list_names'].items():
            if not requested_list:
                continue
            if requested_list not in board_list_names:
                logging.fatal('List {0} not found in board {1}'.format(
                    requested_list, target_board.name
                ))
                return False
            else:
                logging.debug('List {0} exists...'.format(requested_list))
                self.lists[list_label] = self._find_list_id(
                    target_board,
                    requested_list
                )
        logging.info('All boards/lists exist')
        return target_board

    # Utility Functions

    def _find_list_id(self, board, list_name):
        '''Pull out the list id which matches the given name from the board
        '''
        open_lists = board.get_lists('open')
        fl = lambda x: x.name.decode('utf-8') == list_name
        target_list = next(filter(fl, open_lists))
        return target_list.id

    def _dump_lists(self):
        shortened = {
            i.id: i.name.decode('utf-8') for i in self.board.get_lists('open')
        }
        logging.debug('Dumping lists {0} to yaml...'.format(shortened))
        return yaml.dump(shortened, default_flow_style=False)

    def _dump_list_cards(self, list_id):
        target_list = self.board.get_list(list_id)
        shortened = {
            i.id: i.name.decode('utf-8') for i in target_list.list_cards()
        }
        logging.debug('Dumping cards {0} to yaml...'.format(shortened))
        return yaml.dump(shortened, default_flow_style=False)

    # Higher-level functions, steps in the decision tree

    def add_incoming(self, title, description=None):
        target_list = self.board.get_list(self.lists['incoming'])
        return target_list.add_card(name=title, desc=description)

    # not actionable

    def trash(self, card_id):
        pass

    def someday(self, card_id):
        pass

    def reference(self, card_id):
        pass

    def bookmark(self, card_id):
        pass

    # Plan Project task

    def add_project(self, card_id):
        pass

    # Do it now!

    def doing(self, card_id):
        pass

    def blocked(self, card_id):
        pass

    def schedule_follow_up(self, card_id):
        # would be called in conjunction with "blocked" in certain situations
        # requires Gcal API
        pass

    def add_holding_task(self, card_id):
        ''' includes prompting for additional metadata and labels
        '''
        pass

    def add_calendar_event(self, card_id):
        # requires Gcal API
        pass

def main():
    '''argument parsing, config file parsing
    '''
    p = argparse.ArgumentParser()
    actions = p.add_subparsers(help='Actions/Commands:', dest='subparser_name')

    add = actions.add_parser('add', help='Create a new inbound item')
    add.add_argument('title', help='title for the new card')
    add.add_argument('-m', '--message', help='append a description for the new card')

    version = actions.add_parser('version', help='display program version')

    args = p.parse_args()
    print(args)

    if args.subparser_name == 'version':
        print('{0} version {1}'.format(sys.argv[0], VERSION))
    elif args.subparser_name == 'add':
        config_properties = parse_configuration()
        gtd = GTD_Controller(config_properties)
        gtd.add_incoming(args.title, args.message)

if __name__ == '__main__':
    main()

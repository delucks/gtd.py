#!/usr/bin/env python
'''entrypoint of gtd.py'''
import re
import sys
import readline  # noqa
import datetime
import argparse
from functools import partial

import trello
import yaml
import requests

from gtd.input import prompt_for_confirmation, prompt_for_user_choice, quickmove
from gtd.display import JSONDisplay, TextDisplay
from gtd.exceptions import GTDException
from gtd.misc import filter_card_by_tag
from gtd import __version__


class TrelloWrapper:
    '''wraps the trello client, holds state, and provides convenience methods
    for doing certain repeatable tasks on the main board and lists described
    by the configuration properties
    Note that this will break if you have a tag in your Board named NOTAG
    '''
    def __init__(self, primary_list=None, config_file='gtd.yaml', autoconnect=True):
        self.config = self.parse_configuration(config_file)
        self.trello = self.initialize_trello(self.config)
        self.primary_list_name = primary_list or self.config['list_names']['incoming']
        if autoconnect:
            self.__connect()

    def __connect(self):
        try:
            # This is the first connection to the API made by the client
            self.main_board = self._filter_by_name(self.trello.list_boards(), self.config['board_name'])
        except requests.exceptions.ConnectionError:
            print('[FATAL] Could not connect to the Trello API!')
            raise GTDException(1)
        main_list = self._filter_by_name(self.main_board.get_lists('open'), self.primary_list_name)
        if main_list:
            self.main_list = main_list
        else:
            print('[FATAL] The provided list name did not match any lists in {0}!'.format(self.main_board.name.decode('utf8')))
            raise GTDException(1)
        self.label_lookup = self._make_name_lookup(self.main_board.get_labels())
        self.list_lookup = self._make_name_lookup(self.main_board.get_lists('open'))
        self.magic_value = 'NOTAG'

    def initialize_trello(self, config):
        '''Initializes our connection to the trello API
        :param dict config: parsed configuration from the yaml file
        :returns: trello.TrelloClient client
        '''
        trello_client = trello.TrelloClient(
            api_key=config['trello']['api_key'],
            api_secret=config['trello']['api_secret'],
            token=config['trello']['oauth_token'],
            token_secret=config['trello']['oauth_token_secret']
        )
        return trello_client

    def parse_configuration(self, configfile='gtd.yaml'):
        '''load user-defined configuration for what boards and lists to use
        '''
        with open(configfile, 'r') as config_yaml:
            properties = yaml.safe_load(config_yaml)
            return self._validate_config(properties)

    def _validate_config(self, config):
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
            raise GTDException(1)

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
            label_to_add = prompt_for_user_choice(self.label_lookup.keys())
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
        dest = quickmove(self.list_lookup.keys())
        if dest:
            destination_list = self.list_lookup[dest]
            card.change_list(destination_list.id)
            print('Moved to {0}'.format(destination_list.name.decode('utf8')))
            return destination_list
        else:
            print('Skipping!')
            return None

def perform_command(args):
    wrapper = TrelloWrapper(args.list)
    target_lists = [wrapper.main_list] if args.list else []
    tag = wrapper.magic_value if args.no_tag else args.tag if args.tag else None
    cards = wrapper.get_cards(target_lists=target_lists, tag=tag, title_regex=args.match, has_attachments=args.attachments, has_due_date=args.has_due)
    # some modes require a TextDisplay
    if args.json and args.command in ['show', 'grep']:
        display = JSONDisplay()
    else:
        display = TextDisplay(args.no_color)
    if args.no_banner:
        display.banner()
    if args.command == 'show':
        if args.type == 'lists':
            for l in wrapper.main_board.get_lists('open'):
                print(l.name.decode('utf8'))
        elif args.type == 'tags':
            for t in wrapper.main_board.get_labels():
                print(t.name.decode('utf8'))
        else:
            with display:
                for card in cards:
                    display.show(card, True)
    elif args.command == 'grep':
        pattern = args.pattern or '.*'
        with display:
            for card in wrapper.get_cards(title_regex=pattern, tag=tag):
                display.show(card, True)
    elif args.command == 'add':
        if args.destination == 'tag':
            label = wrapper.main_board.add_label(args.title, 'black')
            print('Successfully added tag {0}!'.format(label))
        elif args.destination == 'list':
            l = wrapper.main_board.add_list(args.title)
            print('Successfully added list {0}!'.format(l))
        else:
            returned = wrapper.main_list.add_card(name=args.title, desc=args.message)
            if args.edit:
                display.review_card(returned, wrapper)
            else:
                print('Successfully added card {0}!'.format(returned))
    elif args.command == 'batch':
        if args.type == 'move':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    wrapper.move_to_list(card)
        elif args.type == 'delete':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Should we delete this card?'):
                    card.delete()
                    print('Card deleted!')
        elif args.type == 'due':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Set due date?'):
                    wrapper.set_due_date(card)
        else:
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to tag this one?'):
                    wrapper.add_labels(card)
        print('Batch completed, have a great day!')
    else:
        if args.daily:
            print('Welcome to daily review mode!\nThis combines all "Doing", "Holding", and "Inbound" lists into one big review.\n')
            doing_lists = [wrapper.get_list(l) for l in ['Doing Today', 'Doing this Week', 'Doing this Month']]
            holding = wrapper.get_list(wrapper.config['list_names']['holding'])
            interested_lists = doing_lists + [holding, wrapper.main_list]
            cards = wrapper.get_cards(target_lists=interested_lists, tag=tag, title_regex=args.match)
        display.review_list(cards, wrapper)
        print('All done, have a great day!')


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-m', '--match', metavar='PCRE', help='filter cards to this regex on their title', default=None)
    common.add_argument('-l', '--list', metavar='NAME', help='filter cards to this list', default=None)
    common.add_argument('-j', '--json', action='store_true', help='display results as a JSON list')
    common.add_argument('-a', '--attachments', action='store_true', help='select cards which have attachments')
    common.add_argument('-dd', '--has-due', action='store_true', help='select cards which have due dates')
    tag_group = common.add_mutually_exclusive_group(required=False)
    tag_group.add_argument('-t', '--tag', metavar='NAME', help='filter cards to this tag', default=None)
    tag_group.add_argument('--no-tag', help='only select cards without a tag', action='store_true')
    p = argparse.ArgumentParser(description='{0} version {1}'.format(__doc__, __version__), parents=[common])
    p.add_argument('-c', '--no-color', help='disable colorized output using ANSI escape codes', action='store_false')
    p.add_argument('-b', '--no-banner', help='do not print a banner', action='store_false')
    commands = p.add_subparsers(dest='command')
    commands.add_parser('help', help='display this message')
    add = commands.add_parser('add', help='create a new card, tag, or list')
    add.add_argument('destination', choices=('tag', 'card', 'list'), help='type of item to create')
    add.add_argument('title', help='title for the new item')
    add.add_argument('-m', '--message', help='description for a new card')
    add.add_argument('--edit', help='review the card right after creating it', action='store_true')
    grep = commands.add_parser('grep', help='search through the titles of all cards on the board', parents=[common])
    grep.add_argument('pattern', help='regex to search card titles for', nargs='?')
    show = commands.add_parser('show', help='print all cards of one type', parents=[common])
    show.add_argument('type', choices=('lists', 'cards', 'tags'), default='lists')
    batch = commands.add_parser('batch', help='process cards quickly using only one action: tag, move, or delete', parents=[common])
    batch.add_argument('type', choices=('tag', 'move', 'delete', 'due'), default='move')
    review = commands.add_parser('review', help='process cards with a rich menu interface', parents=[common])
    review.add_argument('-d', '--daily', help='start a daily review mode, which goes through several lists at once', action='store_true')
    commands.add_parser('workflow', help='show the GTD process')
    args = p.parse_args()
    if args.command == 'help':
        p.print_help()
    elif args.command == 'workflow':
        print(
        '1. Collect absolutely everything that can take your attention into "Inbound"\n'
        '2. Filter:\n'
        '    Nonactionable -> Static Reference or Delete\n'
        '    Takes < 2 minutes -> Do now, then Delete\n'
        '    Not your responsibility -> "Holding" or "Blocked" with follow-up\n'
        '    Something to communicate -> messaging lists\n'
        '    Your responsibility -> Your lists\n'
        '3. Write "final" state of each task and "next" state of each task\n'
        '4. Categorize inbound items into lists based on action type required (call x, talk to x, meet x...)\n'
        '5. Reviews:\n'
        '    Daily -> Go through "Inbound" and "Doing"\n'
        '    Weekly -> Additionally, go through "Holding", "Blocked", and messaging lists\n'
        '6. Do\n'
        '\n'
        'The goal is to get everything except the current task out of your head\n'
        'and into a trusted system external to your mind.'
        )
    else:
        perform_command(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Recieved Ctrl+C, quitting!')
        sys.exit(0)
    except GTDException as e:
        if e.errno == 0:
            sys.exit(0)
        else:
            print('Quitting due to error')
            sys.exit(1)

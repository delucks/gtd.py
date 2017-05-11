#!/usr/bin/env python
'''entrypoint of gtd.py'''
import re
import sys
import readline  # noqa
import datetime
from functools import partial

import trello
import requests

from gtd.input import prompt_for_confirmation, prompt_for_user_choice, quickmove
from gtd.display import JSONDisplay, TextDisplay
from gtd.misc import filter_card_by_tag
from gtd.exceptions import GTDException
from gtd.config import ConfigParser
from gtd import __version__


class TrelloConnection:
    '''this one handles connection, retry attempts, stuff like that so it doesn't bail out each
    time we lose connection
    creating a connection requires configuration to be parsed because we need the api keys- so this will need to be invoked
    after the config parser is done doing its thing, with a parameter perhaps being the config

    :param bool autoconnect: should we make a network connection to Trello immediately?
    '''
    def __init__(self, config, autoconnect=True):
        self.autoconnect = autoconnect
        self.trello = self.__connect(config) if autoconnect else None

    def __connect(self, config):
        trello_client = self.initialize_trello(config)
        try:
            # This is the first connection to the API made by the client
            self.boards = trello_client.list_boards()
            return trello_client
        except requests.exceptions.ConnectionError:
            print('[FATAL] Could not connect to the Trello API!')
            raise GTDException(1)
        except trello.exceptions.Unauthorized:
            print('[FATAL] Trello API credentials are invalid')
            raise GTDException(1)

    def initialize_trello(self, config):
        '''Initializes our connection to the trello API
        :param dict config: parsed configuration from the yaml file
        :returns: trello.TrelloClient client
        '''
        trello_client = trello.TrelloClient(
            api_key=config.api_key,
            api_secret=config.api_secret,
            token=config.oauth_token,
            token_secret=config.oauth_token_secret
        )
        return trello_client


class BoardTool:
    '''given a board, this one handles operations on individual cards and dynamically generating lookups that make certain
    operations faster
    provides convenience methods for doing certain repeatable tasks on the main board and lists described by the configuration properties
    Note that this will break if you have a tag in your Board named NOTAG

    :param str primary_list: name of the list you want to use for new cards
    '''
    def __init__(self, trello, config):
        self.trello = trello
        self.config = config
        self.main_board = self._filter_by_name(self.trello.list_boards(), self.config['board_name'])
        list_name = config.list or config['list_names']['incoming']
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

def main():
    config = ConfigParser().config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection.trello, config)
    target_lists = [wrapper.main_list] if config.list else []  # TODO make the conversion from str -> trello.List here more clear
    tag = wrapper.magic_value if config.no_tag else config.tag if config.tag else None
    cards = wrapper.get_cards(target_lists=target_lists, tag=tag, title_regex=config.match, has_attachments=config.attachments, has_due_date=config.has_due)
    # some modes require a TextDisplay
    if config.json and config.command in ['show', 'grep']:
        display = JSONDisplay(config.no_color)
    else:
        display = TextDisplay(config.no_color)
    if config.command == 'help':
        config.argparser.print_help()
        raise GTDException(0)
    elif config.command == 'workflow':
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
        raise GTDException(0)
    if config.no_banner:
        display.banner()
    if config.command == 'show':
        if config.type == 'lists':
            for l in wrapper.main_board.get_lists('open'):
                print(l.name.decode('utf8'))
        elif config.type == 'tags':
            for t in wrapper.main_board.get_labels():
                print(t.name.decode('utf8'))
        else:
            with display:
                for card in cards:
                    display.show(card, True)
    elif config.command == 'grep':
        pattern = config.pattern or '.*'
        with display:
            for card in wrapper.get_cards(title_regex=pattern, tag=tag):
                display.show(card, True)
    elif config.command == 'add':
        if config.destination == 'tag':
            label = wrapper.main_board.add_label(config.title, 'black')
            print('Successfully added tag {0}!'.format(label))
        elif config.destination == 'list':
            l = wrapper.main_board.add_list(config.title)
            print('Successfully added list {0}!'.format(l))
        else:
            returned = wrapper.main_list.add_card(name=config.title, desc=config.message)
            if config.edit:
                display.review_card(returned, wrapper)
            else:
                print('Successfully added card {0}!'.format(returned))
    elif config.command == 'batch':
        if config.type == 'move':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Want to move this one?', True):
                    wrapper.move_to_list(card)
        elif config.type == 'delete':
            for card in cards:
                display.show(card)
                if prompt_for_confirmation('Should we delete this card?'):
                    card.delete()
                    print('Card deleted!')
        elif config.type == 'due':
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
        if config.daily:
            print('Welcome to daily review mode!\nThis combines all "Doing", "Holding", and "Inbound" lists into one big review.\n')
            doing_lists = [wrapper.get_list(l) for l in ['Doing Today', 'Doing this Week', 'Doing this Month']]
            holding = wrapper.get_list(wrapper.config['list_names']['holding'])
            interested_lists = doing_lists + [holding, wrapper.main_list]
            cards = wrapper.get_cards(target_lists=interested_lists, tag=tag, title_regex=config.match)
        display.review_list(cards, wrapper)
        print('All done, have a great day!')


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

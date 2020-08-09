'''Things which operate on or generate Trello cards'''
import re
import json
import shutil
import itertools
import webbrowser
from functools import partial
from typing import Optional

import arrow
import click
import trello
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter, FuzzyWordCompleter

from todo.connection import TrelloConnection
from todo.exceptions import GTDException
from todo.input import prompt_for_confirmation, single_select
from todo.misc import get_title_of_webpage, DevNullRedirect, VALID_URL_REGEX, return_on_eof, build_name_lookup


def parse_user_date_input(user_input):
    accepted_formats = ['MMM D YYYY', 'MM/DD/YYYY', 'DD/MM/YYYY']
    for fmt in accepted_formats:
        try:
            input_datetime = arrow.get(user_input, fmt)
            return input_datetime
        except arrow.parser.ParserError:
            continue
        except ValueError:
            continue
    return None


class Card:
    '''This class is an alternative to py-trello's Card that can reuse the entire JSON structure rather than calling the
    API for each remote attribute. The only network calls are to fetch external attributes like comments or attachments,
    unless you call Card.fetch() to refresh the base JSON structure.
    '''

    def __init__(self, connection: TrelloConnection, card_json: dict):
        self.card_json = card_json
        self.connection = connection

    def __getitem__(self, attr):
        '''Make this object subscriptable so you can treat it like the JSON structure directly'''
        return self.card_json[attr]

    def __str__(self):
        return self.card_json['name']

    @property
    def json(self):
        return self.card_json

    @property
    def id(self):
        return self.card_json['id']

    def fetch(self):
        '''Refresh the base card JSON structure'''
        self.card_json = self.connection.trello.fetch_json('/cards/' + self.id, query_params={'fields': 'all'})

    def fetch_comments(self, force: bool = False):
        '''Fetch the comments on this card and return them in JSON format, adding them into self.card_json
        to cache until the next run.
        '''
        if 'comments' in self.card_json and not force:
            return self.card_json['comments']
        query_params = {'filter': 'commentCard'}
        comments = self.connection.trello.fetch_json('/cards/' + self.id + '/actions', query_params=query_params)
        sorted_comments = sorted(comments, key=lambda comment: comment['date'])
        self.card_json['comments'] = sorted_comments
        return sorted_comments

    def fetch_attachments(self, force: bool = False):
        '''Fetch the attachments on this card and return them in JSON format, after enriching the card JSON
        with the full attachment structure.
        '''
        if 'attachments' in self.card_json and not force:
            return self.card_json['attachments']
        attachments = self.connection.trello.fetch_json(
            '/cards/' + self.id + '/attachments', query_params={'filter': 'false'}
        )
        self.card_json['attachments'] = attachments
        return attachments

    def attach_url(self, url: str):
        '''Attach a link from the internet'''
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/attachments', http_method='POST', post_args={'url': url}
        )

    def remove_attachment(self, attachment_id: str):
        '''Remove an attachment by ID'''
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/attachments/' + attachment_id, http_method='DELETE'
        )

    def delete(self):
        '''Permanently delete the card'''
        return self.connection.trello.fetch_json('/cards/' + self.id, http_method='DELETE')

    def set_closed(self, closed: bool = True):
        '''Archive or unarchive this card'''
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/closed', http_method='PUT', post_args={'value': closed}
        )

    def set_name(self, new_name: str):
        '''Change this card's name'''
        self.card_json['name'] = new_name
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/name', http_method='PUT', post_args={'value': new_name}
        )

    def add_label(self, label_id: str):
        '''Add a label to this card by ID'''
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/idLabels', http_method='POST', post_args={'value': label_id}
        )

    def remove_label(self, label_id: str):
        '''Remove a label from this card by ID'''
        return self.connection.trello.fetch_json('/cards/' + self.id + '/idLabels/' + label_id, http_method='DELETE')

    def comment(self, comment_text: str) -> dict:
        '''Add a comment to a card'''
        return self.connection.trello.fetch_json(
            '/cards/' + self.id + '/actions/comments', http_method='POST', post_args={'text': comment_text}
        )

    def change_board(self, board_id: str, list_id: Optional[str] = None) -> None:
        '''Change the board of this card, and optionally select the list the card should move to'''
        args = {'value': board_id}
        if list_id is not None:
            args['idList'] = list_id
        return self.connection.trello.fetch_json('/cards/' + self.id + '/idBoard', http_method='PUT', post_args=args)

    @return_on_eof
    def rename(self, default: Optional[str] = None, variables: dict = {}):
        if variables:
            print('You can use the following variables in your new card title:')
            for k, v in variables.items():
                print(f'  ${k}: {v}')
        suggestion = variables.get('title0', None) or self.card_json['name']
        newname = prompt(f'Input new name for this card (blank for "{default or suggestion}"): ').strip()
        if newname:
            for k, v in variables.items():
                expansion = f'${k}'
                if expansion in newname:
                    newname = newname.replace(expansion, v)
            self.set_name(newname)
        else:
            # If there wasn't a default set for the card name, leave the card name unchanged
            result = default or suggestion
            if result != self.card_json['name']:
                self.set_name(result)

    @return_on_eof
    def add_labels(self, label_choices):
        '''Give the user a way to toggle labels on this card by their
        name rather than by a numeric selection interface. Using
        prompt_toolkit, we have automatic completion which makes
        things substantially faster without having to do a visual
        lookup against numeric IDs

        Options:
            label_choices: str->trello.Label, the names and objects of labels on this board
        '''
        print('Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit')
        while True:
            label_completer = FuzzyWordCompleter(label_choices.keys())
            userinput = prompt('gtd.py > tag > ', completer=label_completer).strip()
            if userinput not in label_choices.keys():
                if prompt_for_confirmation(f'Unrecognized tag name {userinput}, would you like to create it?', False):
                    label = self.connection.main_board().add_label(userinput, 'green')
                    self.add_label(label.id)
                    click.echo(
                        f'Added tag {label.name} to board {self.connection.main_board().name} and to the card {self}'
                    )
                    label_choices[userinput] = label
            else:
                label_obj = label_choices[userinput]
                try:
                    self.add_label(label_obj.id)
                    click.secho(f'Added tag {userinput}', fg='green')
                except trello.exceptions.ResourceUnavailable:
                    # This label already exists on the card so remove it
                    self.remove_label(label_obj.id)
                    click.secho(f'Removed tag {userinput}', fg='red')

    def title_to_link(self):
        # This assumes your link is in card.name somewhere
        sp = self.card_json['name'].split()
        links = [n for n in sp if VALID_URL_REGEX.search(n)]
        existing_attachments = [a['name'] for a in self.fetch_attachments()]
        user_parameters = {'oldname': self.card_json['name']}
        for idx, link_name in enumerate(links):
            # Attach this link
            if link_name not in existing_attachments:
                self.attach_url(link_name)
            # Get the URL & title of the link for the user to access in the renaming interface
            user_parameters[f'link{idx}'] = link_name
            possible_title = get_title_of_webpage(link_name)
            if possible_title:
                user_parameters[f'title{idx}'] = possible_title
        # Give the user a default title without the link, but allow them to use the title of the page from a link as a var instead
        reconstructed = ' '.join([n for n in sp if not VALID_URL_REGEX.search(n)])
        self.rename(variables=user_parameters, default=reconstructed)

    @return_on_eof
    def manipulate_attachments(self):
        '''Give the user a CRUD interface for attachments on this card'''
        print('Enter a URL, "delete", "open", or "print". Ctrl+D to exit')
        attachment_completer = WordCompleter(['delete', 'print', 'open', 'http://', 'https://'], ignore_case=True)
        while True:
            user_input = prompt('gtd.py > attach > ', completer=attachment_completer).strip()
            if re.search(VALID_URL_REGEX, user_input):
                # attach this link
                self.attach_url(user_input)
                print(f'Attached {user_input}')
            elif user_input in ['delete', 'open']:
                attachment_opts = {a['name']: a for a in self.fetch_attachments()}
                if not attachment_opts:
                    print('This card is free of attachments')
                    continue
                dest = single_select(attachment_opts.keys())
                if dest is not None:
                    target = attachment_opts[dest]
                    if user_input == 'delete':
                        self.remove_attachment(target['id'])
                        self.fetch_attachments(force=True)
                    elif user_input == 'open':
                        with DevNullRedirect():
                            webbrowser.open(target['url'])
            elif user_input == 'print':
                existing_attachments = self.fetch_attachments(force=True)
                if existing_attachments:
                    print('Attachments:')
                    for a in existing_attachments:
                        print('  ' + a['name'])

    @return_on_eof
    def set_due_date(self):
        def validate_date(text):
            return re.match(r'\d{2}\/\d{2}\/\d{4}', text) or re.match(r'[A-Z][a-z]{2} \d{2} \d{4}', text)

        validator = Validator.from_callable(
            validate_date,
            error_message='Enter a date in format "Jun 15 2018", "06/15/2018" or "15/06/2018". Ctrl+D to go back',
            move_cursor_to_end=True,
        )
        while True:
            user_input = prompt('gtd.py > duedate > ', validator=validator, validate_while_typing=True)
            result = parse_user_date_input(user_input)
            if result is None:
                print('Invalid date format!')
            else:
                break
        # Set the due daet
        self.connection.trello.fetch_json(
            '/cards/' + self.id + '/due', http_method='PUT', post_args={'value': result.isoformat()}
        )
        # Pick it up
        self.fetch()
        print('Due date set')
        return result

    def move_to_list(self, list_choices: dict):
        '''Select labels to add to this card

        Options:
            list_choices: str->trello.List, the names and objects of lists on this board
        '''
        dest = single_select(sorted(list_choices.keys()))
        if dest is not None:
            destination_list = list_choices[dest]
            self.connection.trello.fetch_json(
                '/cards/' + self.id + '/idList', http_method='PUT', post_args={'value': destination_list.id}
            )
            print(f'Moved to {destination_list.name}')
            return destination_list

    def change_description(self):
        old_desc = self.card_json['desc']
        new_desc = click.edit(text=old_desc)
        if new_desc is not None and new_desc != old_desc:
            self.connection.trello.fetch_json(
                '/cards/' + self.id + '/desc', http_method='PUT', post_args={'value': new_desc}
            )
        return new_desc


def search_for_regex(card, title_regex, regex_flags):
    try:
        return re.search(title_regex, card['name'], regex_flags)
    except re.error as e:
        click.secho(f'Invalid regular expression "{title_regex}" passed: {str(e)}', fg='red')
        raise GTDException(1)


def check_for_label_presence(card, tags):
    '''Take in a comma-sep list of tag names, and ensure that
    each is on this card'''
    if card['idLabels']:
        user_tags = set(tags.split(','))
        card_tags = set()
        for label in card['labels']:
            card_tags.add(label['name'])
        return user_tags.issubset(card_tags)
    else:
        return False


class CardView:
    '''CardView presents an interface to a stateful set of cards selected by the user, allowing the user
    to navigate back and forth between them, delete them from the list, etc.
    CardView also translates filtering options from the CLI into parameters to request from Trello, or
    filters to post-process the list of cards coming in.

    Use this class either as an iterator ('for card in cardview') or by calling the next() and prev() methods to
    manually step through the list of cards.

    Goals:
        Be light on resources. Store a list of IDs and only create Card objects when they are viewed for the first time.
        Minimize network calls.
        Simplify the API for a command to iterate over a set of selected cards
    '''

    def __init__(self, context, cards):
        self.context = context
        self.cards = cards
        self.position = 0

    def __str__(self):
        return f'CardView on {self.context.connection.main_board().name} with {len(self.cards)} items'

    def __iter__(self):
        return self

    def __next__(self):
        if self.position < len(self.cards):
            card = Card(self.context.connection, self.cards[self.position])
            self.position += 1
            return card
        else:
            raise StopIteration

    def current(self):
        return Card(self.context.connection, self.cards[self.position])

    def next(self):
        if self.position < len(self.cards) - 1:
            self.position += 1
            return self.current()

    def prev(self):
        if self.position > 0:
            self.position -= 1
            return self.current()

    def json(self):
        return json.dumps(self.cards, sort_keys=True, indent=2)

    @staticmethod
    def create(context, **kwargs):
        '''Create a new CardView with the given filters on the cards to find.
        '''
        # Establish all base filters for cards nested resource query parameters.
        query_params = {}
        regex_flags = kwargs.get('regex_flags', 0)
        # Card status, in nested card resource
        status = kwargs.get('status', 'visible')
        valid_filters = ['all', 'closed', 'open', 'visible']
        if status not in valid_filters:
            click.secho(f'Card filter {status} is not valid! Use one of {",".join(valid_filters)}')
            raise GTDException(1)
        query_params['cards'] = status
        query_params['card_fields'] = 'all'
        target_cards = []
        if (list_regex := kwargs.get('list_regex', None)) is not None:  # noqa
            # Are lists passed? If so, query to find out the list IDs corresponding to the names we have
            target_list_ids = []
            lists_json = context.connection.main_lists()
            pattern = re.compile(list_regex, flags=regex_flags)
            for list_object in lists_json:
                if pattern.search(list_object['name']):
                    target_list_ids.append(list_object['id'])
            # Iteratively pull IDs from each list, passing the common parameters to them
            for list_id in target_list_ids:
                cards_json = context.connection.trello.fetch_json(f'/lists/{list_id}/cards', query_params=query_params)
                target_cards.extend(cards_json)
        else:
            # If no lists are passed, call the board's card resource
            cards_json = context.connection.trello.fetch_json(f'/boards/{context.board.id}', query_params=query_params)
            target_cards.extend(cards_json['cards'])

        # Post-process the returned JSON, filtering down to the other passed parameters
        filters = []
        post_processed_cards = []
        # Regular expression on trello.Card.name
        if (title_regex := kwargs.get('title_regex', None)) is not None:  # noqa
            filters.append(partial(search_for_regex, title_regex=title_regex, regex_flags=regex_flags))
        # boolean queries about whether the card has things
        if (has_attachments := kwargs.get('has_attachments', None)) is not None:  # noqa
            filters.append(lambda c: c['badges']['attachments'] > 0)
        if (no_tags := kwargs.get('no_tags', None)) is not None:  # noqa
            filters.append(lambda c: not c['idLabels'])
        if (has_due_date := kwargs.get('has_due_date', None)) is not None:  # noqa
            filters.append(lambda c: c['due'])
        # comma-separated string of tags to filter on
        if (tags := kwargs.get('tags', None)) is not None:  # noqa
            filters.append(partial(check_for_label_presence, tags=tags))

        for card in target_cards:
            if all(filter_func(card) for filter_func in filters):
                post_processed_cards.append(card)

        if not post_processed_cards:
            click.secho('No cards matched the filters provided', fg='red')
            raise GTDException(0)
        # Create a CardView with those objects as the base
        return CardView(context=context, cards=post_processed_cards)

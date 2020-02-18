'''This is most of the user interface and helper functions'''
import re
import sys
import tty
import string
import shutil
import termios
import itertools
import webbrowser
from functools import partial

import arrow
import click
import trello
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter, FuzzyWordCompleter

from todo.misc import get_title_of_webpage, DevNullRedirect, VALID_URL_REGEX, return_on_eof, build_name_lookup
from todo.exceptions import GTDException


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
    remainder = list(set(string.ascii_lowercase) - set(preferred_keys))
    all_keys = preferred_keys + remainder
    for idx, chunk in enumerate(options):
        assigned = all_keys[idx]
        lookup[assigned] = idx
        print(f'[{assigned}] {chunk}')
    print('Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel')
    result = lookup.get(getch(), None)
    if result is not None:
        return list(options)[int(result)]


def triple_column_print(iterable):
    chunk_count = 3
    max_width = shutil.get_terminal_size().columns
    chunk_size = (max_width - 4) // chunk_count
    args = [iter(iterable)] * chunk_count
    for triplet in itertools.zip_longest(fillvalue='', *args):
        print('  {0:<{width}}{1:^{width}}{2:>{width}}  '.format(width=chunk_size, *triplet))


class CardTool:
    '''This static class holds functionality to do atomic modifications on certain cards.
    These methods are used inside of the user interaction parts of the codebase as a way of doing the same operation across
    different UI components.
    '''

    @staticmethod
    @return_on_eof
    def add_labels(card, label_choices):
        '''Give the user a way to toggle labels on this card by their
        name rather than by a numeric selection interface. Using
        prompt_toolkit, we have automatic completion which makes
        things substantially faster without having to do a visual
        lookup against numeric IDs
        :param trello.Card card: the card to modify
        :param dict label_choices: str->trello.Label, the names and objects of labels on this board
        '''
        print('Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Ctrl+D to exit')
        label_completer = FuzzyWordCompleter(label_choices.keys())
        while True:
            userinput = prompt('gtd.py > tag > ', completer=label_completer).strip()
            if userinput == 'ls':
                triple_column_print(label_choices.keys())
            elif userinput not in label_choices.keys():
                if prompt_for_confirmation(f'Unrecognized tag name {userinput}, would you like to create it?', False):
                    label = card.board.add_label(userinput, 'black')
                    card.add_label(label)
                    click.echo(f'Successfully added tag {label.name} to board {card.board.name} and card {card.name}!')
                    label_choices = build_name_lookup(card.board.get_labels(limit=200))
                    label_completer = FuzzyWordCompleter(label_choices.keys())
            else:
                label_obj = label_choices[userinput]
                try:
                    card.add_label(label_obj)
                    click.secho(f'Added tag {userinput}', fg='green')
                except trello.exceptions.ResourceUnavailable:
                    # This label already exists on the card so remove it
                    card.remove_label(label_obj)
                    click.secho(f'Removed tag {userinput}', fg='red')

    @staticmethod
    def title_to_link(card):
        # This assumes your link is in card.name somewhere
        sp = card.name.split()
        links = [n for n in sp if VALID_URL_REGEX.search(n)]
        existing_attachments = [a.name for a in card.get_attachments()]
        user_parameters = {'oldname': card.name}
        for idx, link_name in enumerate(links):
            # Attach this link
            if link_name not in existing_attachments:
                card.attach(url=link_name)
            # Get the URL & title of the link for the user to access in the renaming interface
            user_parameters[f'link{idx}'] = link_name
            possible_title = get_title_of_webpage(link_name)
            if possible_title:
                user_parameters[f'title{idx}'] = possible_title
        # Give the user a default title without the link, but allow them to use the title of the page from a link as a var instead
        reconstructed = ' '.join([n for n in sp if not VALID_URL_REGEX.search(n)])
        CardTool.rename(card, variables=user_parameters, default=reconstructed)

    @staticmethod
    @return_on_eof
    def manipulate_attachments(card):
        '''Give the user a CRUD interface for attachments on this card'''
        print('Enter a URL, "delete", "open", "print", or Enter to exit')
        user_input = 'Nothing really'
        attachment_completer = WordCompleter(['delete', 'print', 'open', 'http://', 'https://'], ignore_case=True)
        while user_input != '':
            user_input = prompt('gtd.py > attach > ', completer=attachment_completer).strip()
            if re.search(VALID_URL_REGEX, user_input):
                # attach this link
                card.attach(url=user_input)
                print(f'Attached {user_input}')
            elif user_input in ['delete', 'open']:
                attachment_opts = {a.name: a for a in card.get_attachments()}
                if not attachment_opts:
                    print('This card is free of attachments')
                    continue
                dest = single_select(attachment_opts.keys())
                if dest is not None:
                    target = attachment_opts[dest]
                    if user_input == 'delete':
                        card.remove_attachment(target.id)
                    elif user_input == 'open':
                        with DevNullRedirect():
                            webbrowser.open(target.url)
            elif user_input == 'print':
                existing_attachments = card.get_attachments()
                if existing_attachments:
                    print('Attachments:')
                    for a in existing_attachments:
                        print('  ' + a.name)

    @staticmethod
    @return_on_eof
    def rename(card, default=None, variables={}):
        if variables:
            print('You can use the following variables in your new card title:')
            for k, v in variables.items():
                print(f'  ${k}: {v}')
        suggestion = variables.get('title0', None) or card.name
        newname = prompt(f'Input new name for this card (blank for "{default or suggestion}"): ').strip()
        if newname:
            for k, v in variables.items():
                expansion = f'${k}'
                if expansion in newname:
                    newname = newname.replace(expansion, v)
            card.set_name(newname)
        else:
            # If there wasn't a default set for the card name, leave the card name unchanged
            card.set_name(default or suggestion)

    @staticmethod
    @return_on_eof
    def set_due_date(card):
        '''prompt for the date to set this card due as'''

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
        card.set_due(result)
        card.fetch()  # Needed to pick up the new due date
        print('Due date set')
        return result

    @staticmethod
    def move_to_list(card, list_choices):
        '''Select labels to add to this card
        :param trello.Card card: the card to modify
        :param dict list_choices: str->trello.List, the names and objects of lists on this board
        '''
        dest = single_select(sorted(list_choices.keys()))
        if dest is not None:
            destination_list = list_choices[dest]
            card.change_list(destination_list.id)
            print(f'Moved to {destination_list.name}')
            return destination_list

    @staticmethod
    def change_description(card):
        old_desc = card.desc or ''
        new_desc = click.edit(text=old_desc)
        if new_desc is not None:
            card.set_description(new_desc)
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
        card_tags = set(card['_labels'])
        return user_tags.issubset(card_tags)
    else:
        return False


class CardView:
    '''CardView presents an interface to a stateful set of cards selected by the user, allowing the user
    to navigate back and forth between them, delete them from the list, etc.
    CardView also translates filtering options from the CLI into parameters to request from Trello, or
    filters to post-process the list of cards coming in.

    Goals:
        Be light on resources. Store a list of IDs and only create Card objects when they are viewed for the first time.
        Minimize network calls.
        Simplify the API for a command to iterate over a set of selected cards
    '''

    def __init__(self, context, cards_json):
        self.context = context
        self.cards_json = cards_json
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self):
        '''This bridges the class into an iterator that acts equivalently to the current "for card in cardsource" type of usage
        It should be replaced with a more elegant way of moving through the cards
        '''
        if self.position < len(self.cards_json):
            card = trello.Card.from_json(self.context.board, self.cards_json[self.position])
            self.position += 1
            return card
        else:
            raise StopIteration

    @staticmethod
    def create(context, **kwargs):
        '''Create a new CardView with the given filters on the cards to find.
        '''
        # Establish all base filters for cards nested resource query parameters.
        query_params = {}
        regex_flags = kwargs.get('regex_flags', 0)
        # Card status: open/closed/archived/all
        if (status := kwargs.get('status', None)) is not None:  # noqa
            valid_filters = ['all', 'closed', 'open', 'visible']
            if status not in valid_filters:
                click.secho(f'Card filter {status} is not valid! Use one of {",".join(valid_filters)}')
                raise GTDException(1)
            query_params['cards'] = status
        # TODO common field selection? Might be able to avoid ones that we don't use at all
        target_cards = []
        if (list_regex := kwargs.get('list_regex', None)) is not None:  # noqa
            # Are lists passed? If so, query to find out the list IDs corresponding to the names we have
            target_list_ids = []
            lists_json = context.connection.trello.fetch_json(
                f'/boards/{context.board.id}/lists',
                query_params={'cards': 'none', 'filter': 'open', 'fields': 'id,name'},
            )
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
            cards_json = context.connection.trello.fetch_json(
                f'/boards/{context.board.id}/cards', query_params=query_params
            )
            target_cards.extend(cards_json)

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

        # Create a CardView with those objects as the base
        return CardView(context=context, cards_json=post_processed_cards)

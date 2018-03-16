import json
import trello
import datetime
from collections import OrderedDict

import click
import prettytable

from todo.exceptions import GTDException
from todo.misc import Colors, get_banner


class Display:
    '''This class is responsible for displaying cards, lists, and other pieces of data from Trello in a visually appealing way.
    It replaces a polymorphic hierarchy that was a poor fit for this operation.
    Different functions are useful for displaying cards in JSON, a table, and in a set of pretty-printed lines.

    Needs:
    - json & text displays must be interchangeable for noninteractive commands
    - table display must have more columns / ability to select only certain columns
    - the "show lists/show tags" thing should have way more bits of metadata it can display. we should ideally have a method that just dumps the names of
      something to stdout
    - banner should have more ascii art options :D
    '''
    def __init__(self, color=True, primary_color=Colors.blue):
        self.color = color
        self.primary = primary_color

    def banner(self):
        '''Display an ASCII art banner for the beginning of program run'''
        print(get_banner(use_color=self.color))

    def show_raw(self, data, use_json=False):
        '''this shows random datastructures
        supports the following features
            show lists
            show tags
            show boards
        '''
        if use_json:
            print(json.dumps(self._force_json(data), sort_keys=True, indent=2))
        elif isinstance(data, list):
            for l in data:
                self.show_raw(l)
        elif isinstance(data, dict):
            for k, v in data.items():
                print(k, end=' ')
                self.show_raw(v)
        elif isinstance(data, trello.Board):
            print(data)
        elif isinstance(data, trello.List):
            print(data)
        elif isinstance(data, trello.Label):
            print(data)
        elif isinstance(data, trello.Card):
            print(data)
        else:
            print(data)

    def _force_json(self, for_json):
        '''force objects held in datastructures to be json-serializable by name only
        :param List|Label|Board|bytes|list|dict|datetime for_json: object to be encoded
        '''
        if isinstance(for_json, trello.List):
            return for_json.name
        elif isinstance(for_json, trello.Label):
            return for_json.name
        elif isinstance(for_json, trello.Board):
            return for_json.name
        elif isinstance(for_json, bytes):
            return for_json.decode('utf8')
        elif isinstance(for_json, list):
            return list(map(self._force_json, for_json))
        elif isinstance(for_json, dict):
            return {k: self._force_json(v) for k, v in for_json.items()}
        elif isinstance(for_json, datetime.datetime):
            return str(for_json)
        else:
            return for_json

    def show_cards(self, cards, use_json=False, tsv=False, table_fields=[], field_blacklist=[]):
        '''Display an iterable of cards all at once.
        Uses a pretty-printed table by default, but can also print JSON and tab-separated values (TSV).
        Supports the following cli commands:
            show cards
            grep

        :param list(trello.Card)|iterable(trello.Card) cards: cards to show
        :param bool use_json: display all metadata of these cards in JSON format
        :param bool tsv: display these cards using a tab-separated value format
        :param list table_fields: display only these fields (overrides field_blacklist)
        :param list field_blacklist: display all except these fields
        '''
        if use_json:
            sanitized_cards = list(map(
                lambda d: d.pop('client') and d,
                [c.__dict__.copy() for c in cards]
            ))
            tostr = self._force_json(sanitized_cards)
            print(json.dumps(tostr, sort_keys=True, indent=2))
        else:
            # TODO implement a custom sorting functions so the table can be sorted by multiple columns
            fields = OrderedDict()
            # This is done repetitively to establish column order
            fields['name'] = lambda c: c.name
            fields['list'] = lambda c: c.get_list().name
            fields['tags'] = lambda c: '\n'.join([l.name for l in c.list_labels]) if c.list_labels else ''
            fields['desc'] = lambda c: c.desc
            fields['due'] = lambda c: c.due or ''
            fields['last activity'] = lambda c: getattr(c, 'dateLastActivity')
            fields['board'] = lambda c: c.board.name
            fields['id'] = lambda c: getattr(c, 'id')
            fields['url'] = lambda c: getattr(c, 'shortUrl')
            table = prettytable.PrettyTable()
            table.field_names = fields.keys()
            table.align = 'l'
            if tsv:
                table.set_style(prettytable.PLAIN_COLUMNS)
            else:
                table.hrules = prettytable.FRAME
            with click.progressbar(list(cards), label='Fetching cards', width=0) as pg:
                for card in pg:
                    table.add_row([x(card) for x in fields.values()])
            try:
                table[0]
            except IndexError:
                click.secho('No cards match!', fg='red')
                raise GTDException(1)
            if table_fields:
                print(self.resize_and_get_table(table, table_fields))
            elif field_blacklist:
                f = set(fields.keys()) - set(field_blacklist)
                print(self.resize_and_get_table(table, list(f)))
            else:
                print(self.resize_and_get_table(table, fields.keys()))

    def resize_and_get_table(self, table, fields):
        '''Remove columns from the table until it fits in your terminal'''
        maxwidth = click.get_terminal_size()[0]
        possible = table.get_string(fields=fields, sortby='last activity')
        fset = set(fields)
        # Fields in increasing order of importance
        to_remove = ['desc', 'id', 'board', 'url', 'last activity', 'list']
        # Wait until we're under max width or until we can't discard more fields
        while len(possible.splitlines()[0]) >= maxwidth and to_remove:
            # Remove a field one at a time
            fset.remove(to_remove.pop(0))
            possible = table.get_string(fields=list(fset), sortby='last activity')
        return possible

    def show_card(self, card):
        '''Display only one card in a format that doesn't take up too much space or depend on external styling.
        Supports the following cli commands:
            review
            batch

        :param trello.Card card: card to display
        '''
        indent_print = lambda m, d: print('  {on}{name: <{fill}}{off}{val}'.format(name=m, val=d, fill='14', on=on, off=off))
        on = self.primary if self.color else ''
        off = Colors.reset if self.color else ''
        print('{on}Card{off}'.format(on=on, off=off), card.id)
        indent_print('Name:', card.name)
        indent_print('List:', '{0}'.format(card.get_list().name))
        if card.list_labels:
            indent_print('Tags:', ','.join([l.name for l in card.list_labels]))
        try:
            created = card.card_created_date
            indent_print('Created:', '{0} ({1})'.format(created, created.timestamp()))
            indent_print('Age:', datetime.datetime.now() - created)
        except IndexError:
            # this happens when the card is created by the repeating cards trello power-up
            indent_print('Created:', 'Repeating Creation Date')
        if card.get_attachments():
            indent_print('Attachments:', '')
            for a in card.get_attachments():
                print(' '*4 + a.name)
        if card.comments:
            indent_print('Comments:', '')
            for c in card.comments:
                print('    {}: {}'.format(c['memberCreator']['username'], c['data']['text']))
        if card.due:
            indent_print('Due:', card.due_date)
            try:
                diff = card.due_date - datetime.datetime.now(datetime.timezone.utc)
                if diff < datetime.timedelta(0):
                    display = Colors.red
                elif diff < datetime.timedelta(weeks=2):
                    display = Colors.yellow
                else:
                    display = Colors.green
                indent_print('Remaining:', '{0}{1}{2}'.format(display, diff, Colors.reset))
            except TypeError:
                # fucking datetime throws exceptions about bullshit
                pass
        if card.description:
            indent_print('Description', '')
            for line in card.description.splitlines():
                print(' '*4 + line)

import json
import shutil
import trello
import datetime
import itertools
import prettytable
from collections import OrderedDict

from todo import __version__, __author__
from todo.misc import Colors


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
    def __init__(self, color=True):
        self.color = color

    def banner(self):
        '''display a banner for the beginning of program run, if supported'''
        on = self.primary if self.coloration else ''
        off = Colors.reset if self.coloration else ''
        banner = (
            ' __|_ _| ._     version {on}{0}{off}\n'
            '(_||_(_|{on}o{off}|_)\/  by {on}{1}{off}\n'
            ' _|      |  /\n').format(__version__, __author__, on=on, off=off)
        print(banner)

    def show_raw(self, data, use_json=False):
        '''this shows random datastructures
        supports the following features
            show lists
            show tags
            show boards
        '''
        if isinstance(data, list):
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

    '''copied from the JSONDisplay'''

    def _force_json(self, for_json):
        '''force things to be json-serializable by name only'''
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

    # 'name', 'tags', 'list'
    def show_cards(self, cards, use_json=False, csv=False, table_fields=[], field_blacklist=['desc']):
        # this shows a table of some objects + metadata
        # this shows a group of cards
        '''supports
            show cards
            grep
        '''
        if use_json:
            sanitized_cards = list(map(
                lambda d: d.pop('client') and d,
                [c.__dict__.copy() for c in cards]
            ))
            tostr = self._force_json(sanitized_cards)
            print(json.dumps(tostr, sort_keys=True, indent=2))
        elif csv:
            # not yet supported
            pass
        else:
            # table
            # name of field -> callable that obtains this field from the card
            # we'll register the table with .keys()
            # then iterate through the cards and call each .value() on the card to produce columns
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
            table.hrules = prettytable.FRAME
            table.align = 'l'
            for card in cards:
                table.add_row([x(card) for x in fields.values()])
            # TODO add detection for when the table is over maximum width of the terminal and chop off fields
            if table_fields:
                print(table.get_string(fields=table_fields, sortby='last activity'))
            elif field_blacklist:
                f = list(set(fields.keys()) - set(field_blacklist))
                print(table.get_string(fields=f, sortby='last activity'))
            else:
                print(table)

    '''copied from the TextDisplay'''

    # TODO refactor these out
    def _colorize(self, lbl, msg, colorstring):
        return '{0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)

    def _p(self, lbl, msg, colorstring=Colors.blue):
        if self.color:
            print(self._colorize(lbl, msg, colorstring))
        else:
            print('{0} {1}'.format(lbl, msg))

    def show_card(self, card):
        '''display one card in a way that does not depend on external styling like a table
        supports
            review
            batch
        '''
        self._p('Card', card.id)
        self._p('  Name:', card.name)
        try:
            created = card.card_created_date
            self._p('  Created on:', '{0} ({1})'.format(created, created.timestamp()))
            self._p('  Age:', datetime.datetime.now() - created)
        except IndexError:
            # this happens when the card is created by the repeating cards trello power-up
            print('  Repeating Creation Date')
        if card.list_labels:
            self._p('  Tags:', ','.join([l.name for l in card.list_labels]))
        if card.get_attachments():
            self._p('  Attachments:', ','.join(a.name for a in card.get_attachments()))
        if card.due:
            self._p('  Due:', card.due_date)
            try:
                diff = card.due_date - datetime.datetime.now(datetime.timezone.utc)
                if diff < datetime.timedelta(0):
                    display = Colors.red
                elif diff < datetime.timedelta(weeks=2):
                    display = Colors.yellow
                else:
                    display = Colors.green
                print('  {0}Remaining: {1}{2}'.format(display, diff, Colors.reset))
            except TypeError:
                # fucking datetime throws exceptions about bullshit
                pass
        if card.description:
            self._p('  Description', '')
            for line in card.description.splitlines():
                print(' '*4 + line)
        self._p('  List:', '{0}'.format(card.get_list().name))

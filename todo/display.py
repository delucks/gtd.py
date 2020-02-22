import json
import trello
import datetime
from collections import OrderedDict

import click
import prettytable

from todo.exceptions import GTDException
from todo.misc import Colors, get_banner, mongo_id_to_date


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

    def __init__(self, config, connection, primary_color=Colors.blue):
        # TODO move primary_color into a configuration setting
        self.config = config
        self.connection = connection
        self.primary = primary_color
        self.fields = Display.build_fields()

    @staticmethod
    def build_fields():
        '''This creates the dictionary of field name -> getter function that's used to translate the JSON
        response into a table. It's created once and bound to this object so the CLI functions can check if their
        --field arguments are valid field names before invoking the functions that output onto the screen
        '''
        fields = OrderedDict()
        # This is done repetitively to establish column order
        fields['name'] = lambda c: c.name
        fields['list'] = lambda c: c.get_list().name
        fields['tags'] = lambda c: '\n'.join([l.name for l in c.labels]) if c.labels else ''
        fields['desc'] = lambda c: c.desc
        fields['due'] = lambda c: c.due[:10] if c.due is not None else ''
        fields['activity'] = lambda c: c.dateLastActivity.strftime('%Y-%m-%d')
        fields['board'] = lambda c: c.board.name
        fields['id'] = lambda c: getattr(c, 'id')
        fields['url'] = lambda c: getattr(c, 'shortUrl')
        return fields

    def banner(self):
        '''Display an ASCII art banner for the beginning of program run'''
        if self.config.banner:
            print(get_banner(use_color=self.config.color))

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

    def show_cards(self, cards, tsv=False, sort='activity', table_fields=[]):
        '''Display an iterable of cards all at once.
        Uses a pretty-printed table by default, but can also print JSON and tab-separated values (TSV).
        Supports the following cli commands:
            show cards
            grep

        :param list(trello.Card)|iterable(trello.Card) cards: cards to show
        :param bool tsv: display these cards using a tab-separated value format
        :param str sort: the field name to sort by (must be a valid field name in this table)
        :param list table_fields: display only these fields
        '''
        # TODO construct the table dynamically instead of filtering down an already-constructed table
        # TODO implement a custom sorting functions so the table can be sorted by multiple columns
        table = prettytable.PrettyTable()
        table.field_names = self.fields.keys()
        table.align = 'l'
        if tsv:
            table.set_style(prettytable.PLAIN_COLUMNS)
        else:
            table.hrules = prettytable.FRAME
        with click.progressbar(list(cards), label='Fetching cards', width=0) as pg:
            for card in pg:
                table.add_row([x(card) for x in self.fields.values()])
        try:
            table[0]
        except IndexError:
            click.secho('No cards match!', fg='red')
            raise GTDException(1)
        if table_fields:
            print(table.get_string(fields=table_fields, sortby=sort))
        else:
            print(self.resize_and_get_table(table, self.fields.keys(), sort))

    def resize_and_get_table(self, table, fields, sort):
        '''Remove columns from the table until it fits in your terminal'''
        maxwidth = click.get_terminal_size()[0]
        possible = table.get_string(fields=fields, sortby=sort)
        fset = set(fields)
        # Fields in increasing order of importance
        to_remove = ['desc', 'id', 'board', 'url', 'activity', 'list']
        # Wait until we're under max width or until we can't discard more fields
        while len(possible.splitlines()[0]) >= maxwidth and to_remove:
            # Remove a field one at a time
            fset.remove(to_remove.pop(0))
            possible = table.get_string(fields=list(fset), sortby=sort)
        return possible

    def show_card(self, card: dict):
        '''Display only one card in a format that doesn't take up too much space or depend on external styling.

        Arguments:
            card: Full JSON card structure back from the Trello API
        '''
        label_color_correction = {
            'purple': 'magenta',
            'sky': 'cyan',
            'orange': 'yellow',
            'lime': 'green',
            'pink': 'magenta',
            # TODO allow this to be overridden
            'black': 'white',
        }
        date_display_format = '%Y-%m-%d %H:%M:%S'
        on = self.primary if self.config.color else ''
        off = Colors.reset if self.config.color else ''
        indent_print = lambda m, d: print(
            '  {on}{name: <{fill}}{off}{val}'.format(name=m, val=d, fill='14', on=on, off=off)
        )
        print(f'{on}Card{off} {card["id"]}')
        indent_print('Name:', card['name'])
        indent_print('List:', self.connection.lists_by_id()[card['idList']])
        if card['labels']:
            name = 'Tags:'
            click.echo(f'  {on}{name:<14}{off}', nl=False)
            for l in card['labels']:
                click.secho(l['name'] + ' ', fg=label_color_correction.get(l['color'], l['color']) or 'green', nl=False)
            print()
        created = mongo_id_to_date(card['id'])
        indent_print('Created:', f'{created.strftime(date_display_format)} ({int(created.timestamp())})')
        indent_print('Age:', datetime.datetime.now() - created)
        if card['badges']['attachments']:
            indent_print('Attachments:', '')
            for a in card.fetch_attachments():
                print(' ' * 4 + a['name'])
        if card['badges']['comments'] > 0:
            indent_print('Comments:', '')
            for c in card.fetch_comments():
                print(f"    {c['memberCreator']['username']}: {c['data']['text']}")
        if card['due']:
            # Why can't python properly parse ISO8601 timestamps? gah
            due_date_string = card['due'].replace('Z', '+00:00')
            due = datetime.datetime.fromisoformat(due_date_string)
            indent_print('Due:', f'{due.strftime(date_display_format)}')
            diff = due - datetime.datetime.now(datetime.timezone.utc)
            if diff < datetime.timedelta(0):
                display = Colors.red
            elif diff < datetime.timedelta(weeks=2):
                display = Colors.yellow
            else:
                display = Colors.green
            indent_print('Remaining:', f'{display if self.config.color else ""}{diff}{off}')
        if card['desc']:
            indent_print('Description', '')
            for line in card['desc'].splitlines():
                print(' ' * 4 + line)

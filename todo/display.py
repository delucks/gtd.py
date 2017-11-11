import json
import shutil
import trello
import datetime
import itertools

from todo import __version__, __author__
from todo.misc import Colors


class Display:
    '''base class for different card display modes

    :param bool coloration: use color for the output of this session
    '''
    def __init__(self, coloration, *kwargs):
        self.coloration = coloration

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, tb):
        pass

    def banner(self):
        '''display a banner for the beginning of program run, if supported'''
        on = self.primary if self.coloration else ''
        off = Colors.reset if self.coloration else ''
        banner = (
            ' __|_ _| ._     version {on}{0}{off}\n'
            '(_||_(_|{on}o{off}|_)\/  by {on}{1}{off}\n'
            ' _|      |  /\n').format(__version__, __author__, on=on, off=off)
        print(banner)

    def show(self, card, *kwargs):
        '''output the state for a single card

        :param trello.Card card: card to display
        '''
        raise NotImplemented()

    def show_list(self, iterable):
        '''output a normal list of strings in the display manner this class handles
        '''
        raise NotImplemented()


class TableDisplay(Display):
    '''outputs cards in a terminal-width optimized manner
    Column Layout:

    | Name | List | Create Date | Due Date | Tags | Attachments |

    All column widths should be precomputed so we can output each card consistently
    '''
    def __init__(self, coloration, max_list_length=10, max_label_length=10, per_row_divider=True, size_override=None):
        super(TableDisplay, self).__init__(coloration)
        if isinstance(size_override, tuple) and all(isinstance(x, int) for x in size_override):
            self.width, self.height = size_override
        else:
            self.width, self.height = shutil.get_terminal_size()
        num_columns = 5
        self.time_format_string = '%d/%m/%y %H:%M'
        self.sz_list = max_list_length
        self.sz_label = max_label_length
        self.sz_due = self.sz_created = len(self.time_format_string)
        self.primary = Colors.green
        total = self.sz_created + self.sz_due + self.sz_label + self.sz_list + 3*num_columns + 1
        self.sz_name = self.width - total
        self.per_row_divider = per_row_divider
        self.fmt_str = '| {on}{name: <{sz_name}}{off} | {on}{listname: <{sz_list}}{off} | {on}{ctime: <{sz_created}}{off} | {on}{tags: <{sz_tags}}{off} | {on}{cdue: <{sz_due}}{off} |'

    def __enter__(self):
        on = self.primary if self.coloration else ''
        off = Colors.reset if self.coloration else ''
        self.__show_divider()
        print(self.fmt_str.format(
            name='Name', sz_name=self.sz_name,
            listname='List', sz_list=self.sz_list,
            ctime='Creation', sz_created=self.sz_created,
            cdue='Due Date', sz_due=self.sz_due,
            tags='Tags', sz_tags=self.sz_label,
            on=on, off=off
        ))
        if not self.per_row_divider:
            self.__show_divider()
        return self

    def __exit__(self, etype, evalue, tb):
        self.__show_divider()

    def __show_divider(self):
        print('+{0}+{1}+{2}+{3}+{4}+'.format(
            '-'*(self.sz_name+2),
            '-'*(self.sz_list+2),
            '-'*(self.sz_created+2),
            '-'*(self.sz_label+2),
            '-'*(self.sz_due+2)
        ))

    def _wrap_long_string(self, towrap, maxwidth):
        '''turn a string of length greater than a column width into
        a list of multiple substrings, optimistically split by word'''
        result = []
        current = ''
        for chunk in towrap.split():
            if len(chunk) > maxwidth:
                # split a long word up into multiple words
                if current:
                    result.append(current)
                # split it the first time
                result.append(chunk[:maxwidth])
                new = chunk[maxwidth:]
                while len(new) > maxwidth:
                    # if we still have more to do...
                    result.append(new[:maxwidth])
                    new = new[maxwidth:]
                current = new
            elif (len(chunk) + len(current) + 1) > maxwidth:
                result.append(current)
                current = chunk
            else:
                # our current word plus the current unwrapped one does not exceed the max length
                if current:
                    current = current + ' ' + chunk
                else:
                    current = chunk
        result.append(current)  # final chunk
        return result

    def show(self, card, *kwargs):
        '''Perform the logic to split a card's fields up into multiple columns, showing them side by side.
        If there is not anything to be printed in one of the columns, print ' '*width
        '''
        if self.per_row_divider:
            self.__show_divider()
        # Set up lists of the contents of each column
        rawname = card.name
        if len(rawname) > self.sz_name:
            name = self._wrap_long_string(rawname, self.sz_name)
        else:
            name = [rawname]
        try:
            create = [card.card_created_date.strftime(self.time_format_string)]
        except IndexError:
            create = ['Repeating']
        tags = [l.name for l in card.list_labels] if card.list_labels else []
        due = [card.due_date.strftime(self.time_format_string)] if card.due_date else []
        listname = [card.get_list().name]
        # Take one element at a time each column's contents, print it
        for group in itertools.zip_longest(name, listname, create, tags, due, fillvalue=''):
            print(self.fmt_str.format(
                name=group[0], sz_name=self.sz_name,
                listname=group[1], sz_list=self.sz_list,
                ctime=group[2], sz_created=self.sz_created,
                tags=group[3], sz_tags=self.sz_label,
                cdue=group[4], sz_due=self.sz_due,
                on='', off=''
            ))

    def show_list(self, iterable):
        for l in iterable:
            print(l)


class TextDisplay(Display):
    '''controls the color and output detail for an interactive
    session of gtd.py

    :param bool coloration: use color for the output of this session
    :param str primary: unix escape for the primary accent color
    '''
    def __init__(self, coloration, primary=Colors.red):
        super(TextDisplay, self).__init__(coloration)
        self.primary = primary
        self.maxwidth = shutil.get_terminal_size().columns

    def _colorize(self, lbl, msg, colorstring):
        return '{0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)

    def _p(self, lbl, msg, colorstring=Colors.blue):
        if self.coloration:
            print(self._colorize(lbl, msg, colorstring))
        else:
            print('{0} {1}'.format(lbl, msg))

    def show(self, card, *kwargs):
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
                    display = self.primary
                print('  {0}Remaining: {1}{2}'.format(display, diff, Colors.reset))
            except TypeError:
                # fucking datetime throws exceptions about bullshit
                pass
        if card.description:
            self._p('  Description', '')
            for line in card.description.splitlines():
                print(' '*4 + line)
        self._p('  List:', '{0}'.format(card.get_list().name))

    def show_list(self, iterable):
        for l in iterable:
            print(l)


class JSONDisplay(Display):
    '''collects all returned objects into an array then dumps them to json

    :param bool coloration: unused
    '''
    def __init__(self, coloration=False):
        super(JSONDisplay, self).__init__(coloration)
        self.items = []

    def __enter__(self):
        return self

    def _normalize(self, for_json):
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
            return list(map(self._normalize, for_json))
        elif isinstance(for_json, datetime.datetime):
            return str(for_json)
        else:
            return for_json

    def __exit__(self, etype, evalue, tb):
        items = self.items[0] if len(self.items) == 1 else self.items
        try:
            print(json.dumps(items))
        except TypeError:
            print(items)
            raise

    def banner(self):
        pass

    def show(self, card, *kwargs):
        result = {}
        for k, v in card.__dict__.items():
            if k != 'client':
                result[k] = self._normalize(v)
        self.items.append(result)

    def show_list(self, iterable):
        self.items = list(iterable)

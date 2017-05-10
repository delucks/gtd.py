import json
import trello
import datetime
import webbrowser

from gtd import __version__, __author__
from gtd.misc import Colors
from gtd.exceptions import GTDException


class Display:
    '''base class for different card display modes

    :param bool coloration: use color for the output of this session
    '''
    def __init__(self, coloration, *kwargs):
        self.coloration = coloration

    def banner(self):
        '''display a banner for the beginning of program run, if supported'''
        raise NotImplemented()

    def show(self, card, *kwargs):
        '''output the state for a single card

        :param trello.Card card: card to display
        '''
        raise NotImplemented()


class TextDisplay(Display):
    '''controls the color and output detail for an interactive
    session of gtd.py

    :param bool coloration: use color for the output of this session
    :param str primary: unix escape for the primary accent color
    '''
    def __init__(self, coloration, primary=Colors.green):
        super(TextDisplay, self).__init__(coloration)
        self.primary = primary

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, tb):
        pass

    def _colorize(self, lbl, msg, colorstring):
        return '{0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)

    def _p(self, lbl, msg, colorstring=Colors.blue):
        if self.coloration:
            print(self._colorize(lbl, msg, colorstring))
        else:
            print('{0} {1}'.format(lbl, msg))

    def banner(self):
        on = self.primary if self.coloration else ''
        off = Colors.reset if self.coloration else ''
        banner = (' __|_ _| ._     version {on}{0}{off}\n'
        '(_||_(_|{on}o{off}|_)\/  by {on}{1}{off}\n'
        ' _|      |  /\n').format(__version__, __author__, on=on, off=off)
        print(banner)

    def show(self, card, show_list=True):
        created = card.create_date
        self._p('Card', card.id)
        self._p('  Name:', card.name.decode('utf8'))
        self._p('  Created on:', '{0} ({1})'.format(created, created.timestamp()))
        self._p('  Age:', datetime.datetime.now(datetime.timezone.utc) - created)
        if card.list_labels:
            self._p('  Tags:', ','.join([l.name.decode('utf8') for l in card.list_labels]))
        if card.get_attachments():
            self._p('  Attachments:', ','.join([a['name'] for a in card.get_attachments()]))
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
        if show_list:
            self._p('  List:', '{0}'.format(card.get_list().name.decode('utf8')))

    def review_card(self, card, wrapper):
        '''present the user with an option-based interface to do every operation on
        a single card'''
        on = self.primary if self.coloration else ''
        off = Colors.reset if self.coloration else ''
        header = ''.join([
            '{on}D{off}elete, '
            '{on}T{off}ag, '
            '{on}A{off}ttach Title, '
            '{on}P{off}rint Card, '
            '{on}R{off}ename, '
            'd{on}U{off}e Date, '
            '{on}M{off}ove, '
            '{on}S{off}kip, '
            '{on}Q{off}uit'
        ]).format(on=on, off=off)
        if card.get_attachments():
            header = '{on}O{off}pen attachment, '.format(on=on, off=off) + header
        choice = ''
        self.show(card, True)
        while choice != 'S' and choice != 'D':
            print(header)
            choice = input('Input option character: ').strip().upper()
            if choice == 'D':
                card.delete()
                print('Card deleted')
                break
            elif choice == 'T':
                wrapper.add_labels(card)
            elif choice == 'A':
                wrapper.title_to_link(card)
            elif choice == 'P':
                self.show(card, True)
            elif choice == 'R':
                wrapper.rename(card)
            elif choice == 'U':
                wrapper.set_due_date(card)
            elif choice == 'M':
                if wrapper.move_to_list(card):
                    break
            elif choice == 'Q':
                raise GTDException(0)
            elif choice == 'S':
                pass
            elif choice == 'O':
                for l in [a['name'] for a in card.get_attachments()]:
                    webbrowser.open(l)
            else:
                print('Invalid option {0}'.format(choice))

    def review_list(self, cards, wrapper):
        for card in cards:
            self.review_card(card, wrapper)


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
            return for_json.name.decode('utf8')
        elif isinstance(for_json, trello.Label):
            return for_json.name.decode('utf8')
        elif isinstance(for_json, trello.Board):
            return for_json.name.decode('utf8')
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

    def show(self, card, _=None):
        result = {}
        for k, v in card.__dict__.items():
            if k != 'client':
                result[k] = self._normalize(v)
        self.items.append(result)

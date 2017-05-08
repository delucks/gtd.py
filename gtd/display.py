import json
import datetime
import webbrowser

from gtd import __version__, __author__
from gtd.misc import Colors
from gtd.exceptions import GTDException


class TextDisplay:
    '''controls the coloration and detail of the output for a session duration'''
    def __init__(self, use_color):
        self.use_color = use_color

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, tb):
        pass

    def _colorize(self, lbl, msg, colorstring):
        return '{0}{1}{2} {3}'.format(colorstring, lbl, Colors.reset, msg)

    def _p(self, lbl, msg, colorstring=Colors.blue):
        if self.use_color:
            print(self._colorize(lbl, msg, colorstring))
        else:
            print('{0} {1}'.format(lbl, msg))

    def banner(self):
        on = Colors.green if self.use_color else ''
        off = Colors.reset if self.use_color else ''
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
                    display = Colors.green
                print('  {0}Remaining: {1}{2}'.format(display, diff, Colors.reset))
            except TypeError:
                # fucking datetime throws exceptions about bullshit
                pass
        if show_list:
            self._p('  List:', '{0}'.format(card.get_list().name.decode('utf8')))

    def review_card(self, card, wrapper):
        '''present the user with an option-based interface to do every operation on
        a single card'''
        # FIXME have the color of the options be configurable
        header = (
            '{0.green}D{0.reset}elete, '
            '{0.green}T{0.reset}ag, '
            '{0.green}A{0.reset}ttach Title, '
            '{0.green}P{0.reset}rint Card, '
            '{0.green}R{0.reset}ename, '
            'd{0.green}U{0.reset}e Date, '
            '{0.green}M{0.reset}ove, '
            '{0.green}S{0.reset}kip, '
            '{0.green}Q{0.reset}uit'
        ).format(Colors)
        if card.get_attachments():
            header = '{0.green}O{0.reset}pen attachment, '.format(Colors) + header
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
                if 'link' not in header:
                    print('This card does not have an attachment!')
                else:
                    for l in [a['name'] for a in card.get_attachments()]:
                        webbrowser.open(l)
            else:
                print('Invalid option {0}'.format(choice))

    def review_list(self, cards, wrapper):
        for card in cards:
            self.review_card(card, wrapper)


class JSONDisplay:
    '''collects all returned objects into an array then dumps them to json'''
    def __init__(self):
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

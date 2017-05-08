'''user interface, user interaction functions'''
import sys
import tty
import string
import termios


def prompt_for_user_choice(iterable):
    listed = list(iterable)
    for index, item in enumerate(listed):
        print('  [{0}] {1}'.format(index, item.decode('utf8')))
    while True:
        usersel = input('Input the numeric ID or IDs of the item(s) you want: ').strip()
        try:
            if ',' in usersel or ' ' in usersel:
                delimiter = ',' if ',' in usersel else ' '
                indicies = [int(i) for i in usersel.split(delimiter)]
            else:
                indicies = [int(usersel)]
            break
        except ValueError:
            print('You gave a malformed input!')
    return [listed[i] for i in indicies]


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


def quickmove(iterable):
    '''a faster selection interface
    Assign a unique one-char identifier to each option, and read only one
    character from stdin. Match that one character against the options
    Downside: you can only have 30ish options
    '''
    lookup = {}
    preferred_keys = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"]
    remainder = list(set(preferred_keys) - set(string.ascii_lowercase))
    all_keys = preferred_keys + remainder
    for idx, chunk in enumerate(iterable):
        assigned = all_keys[idx]
        lookup[assigned] = idx
        print('[{0}] {1}'.format(assigned, chunk.decode('utf8')))
    print('Press the character corresponding to your choice, selection will happen immediately. Ctrl+C to cancel')
    result = lookup.get(getch(), None)
    if result:
        return list(iterable)[int(result)]
    else:
        return None

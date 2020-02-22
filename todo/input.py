'''Helper functions that retrieve user input'''
import sys
import tty
import string
import termios


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

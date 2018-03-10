import os
import re
import requests
from todo import __version__, __author__
try:
    from random import choice
except OSError:
    # Some platforms (cough cough armv7, mips) fail when importing random due to lack of hardware support
    choice = lambda n: n.pop()


VALID_URL_REGEX = re.compile('https?://.*\.')


class Colors:
    esc = '\033'
    black = esc + '[0;30m'
    red = esc + '[0;31m'
    green = esc + '[0;32m'
    yellow = esc + '[0;33m'
    blue = esc + '[0;34m'
    purple = esc + '[0;35m'
    cyan = esc + '[0;36m'
    white = esc + '[0;37m'
    reset = esc + '[0m'

    @staticmethod
    def all_colors():
        return [Colors.red, Colors.green, Colors.yellow, Colors.blue, Colors.purple, Colors.cyan]


def get_title_of_webpage(url):
    headers = {'User-Agent': 'gtd.py version ' + __version__}
    try:
        resp = requests.get(url, headers=headers)
        if 'text/html' not in resp.headers.get('Content-Type', ''):
            return None
        as_text = resp.text
        return as_text[as_text.find('<title>') + 7:as_text.find('</title>')]
    except requests.exceptions.ConnectionError:
        return None


class DevNullRedirect:
    '''Temporarily eat stdout/stderr to allow no output.
    This is used to suppress browser messages in webbrowser.open'''
    def __enter__(self):
        self.old_stderr = os.dup(2)
        self.old_stdout = os.dup(1)
        os.close(2)
        os.close(1)
        os.open(os.devnull, os.O_RDWR)

    def __exit__(self, exc_type, exc_value, traceback):
        os.dup2(self.old_stderr, 2)
        os.dup2(self.old_stdout, 1)


WORKFLOW_TEXT = (
    '1. Collect absolutely everything that can take your attention into "Inbound"\n'
    '2. Filter:\n'
    '    Nonactionable -> Static Reference or Delete\n'
    '    Takes < 2 minutes -> Do now, then Delete\n'
    '    Not your responsibility -> "Holding" or "Blocked" with follow-up\n'
    '    Something to communicate -> messaging lists\n'
    '    Your responsibility -> Your lists\n'
    '3. Write "final" state of each task and "next" state of each task\n'
    '4. Categorize inbound items into lists based on action type required (call x, talk to x, meet x...)\n'
    '5. Reviews:\n'
    '    Daily -> Go through "Inbound" and "Doing"\n'
    '    Weekly -> Additionally, go through "Holding", "Blocked", and messaging lists\n'
    '6. Do\n'
    '\n'
    'The goal is to get everything except the current task out of your head\n'
    'and into a trusted system external to your mind.'
)


def get_banner(version=__version__, author=__author__, use_color=True):
    '''Hold a buncha poorly done ASCII banners and display one at random!'''
    if use_color:
        on = choice(Colors.all_colors())
        off = Colors.reset
    else:
        on = off = ''
    b1 = (
        ' __|_ _| ._     version {on}{0}{off}\n'
        '(_||_(_|{on}o{off}|_)\/  by {on}{1}{off}\n'
        ' _|      |  /\n'
    ).format(version, author, on=on, off=off)
    b2 = (
        '  ___  ____  ____    ____  _  _\n'
        ' / __)(_  _)(  _ \  (  _ \( \/ )\n'
        '( (_-.  )(   )(_) )  )___/ \  /\n'
        ' \___/ (__) (____/{on}(){off}(__)   (__)\n'
        '   version {on}{0}{off}\n'
    ).format(version, on=on, off=off)
    b3 = (
        '        __      __   version {on}{0}{off}\n'
        '.-----.|  |_.--|  |  .-----.--.--.\n'
        '|  _  ||   _|  _  |{on}__{off}|  _  |  |  |\n'
        '|___  ||____|_____{on}|__|{off}   __|___  |\n'
        '|_____|              |__|  |_____|\n'
    ).format(version, on=on, off=off)
    b4 = (
        '         __      .___  version {on}{0}{off}\n'
        '   _____/  |_  __| _/______ ___.__.\n'
        '  / ___\   __\/ __ | \____ <   |  |\n'
        ' / /_/  >  | / /_/ | |  |_> >___  |\n'
        ' \___  /|__| \____ |{on}/\{off}   __// ____|\n'
        '/_____/           \/{on}\/{off}__|   \/\n'
    ).format(version, on=on, off=off)
    # A joke, is funny
    b5 = '67 74 64 {on}2e{off} 70 79\n76 65 72 73 69 6f 6e {on}{0}{off}\n'.format(version, on=on, off=off)
    b6 = '--. - -.. {on}.-.-.-{off} .--. -.--\n...- . .-. ... .. --- -. {on}{0}{off}\n'.format(version, on=on, off=off)
    b7 = (
        '     _     _\n'
        ' ___| |_ _| |  ___ _ _\n'
        '| . |  _| . |{on}_{off}| . | | |\n'
        '|_  |_| |___{on}|_|{off}  _|_  |\n'
        '|___|         |_| |___|\n'
        '     version {on}{0}{off}\n'
    ).format(version, on=on, off=off)
    banner_choices = [b1, b2, b3, b4, b5, b6, b7]
    return choice(banner_choices)

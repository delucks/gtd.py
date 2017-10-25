import requests
from todo import __version__


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


class AttrDict(dict):
    def __init__(self):
        self.__dict__ = self


def get_title_of_webpage(url):
    headers = {'User-Agent': 'gtd.py version ' + __version__}
    try:
        resp = requests.get(url, headers=headers)
        as_text = resp.text
        return as_text[as_text.find('<title>') + 7:as_text.find('</title>')]
    except requests.exceptions.ConnectionError:
        return None

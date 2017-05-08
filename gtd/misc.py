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


def filter_card_by_tag(card, tag):
    if card.list_labels:
        return tag in [l.name.decode('utf8') for l in card.list_labels]
    else:
        return False

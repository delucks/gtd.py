#!/usr/bin/env python
'''entrypoint of gtd.py'''
import sys
import readline  # noqa

from gtd.input import prompt_for_confirmation, BoardTool
from gtd.display import JSONDisplay, TextDisplay, TableDisplay
from gtd.exceptions import GTDException
from gtd.connection import TrelloConnection
from gtd.config import ConfigParser
from gtd import __version__


def main():
    config = ConfigParser().config
    connection = TrelloConnection(config)
    wrapper = BoardTool(connection)
    target_lists = [wrapper.main_list] if config.list else []  # TODO make the conversion from str -> trello.List here more clear
    tag = wrapper.magic_value if config.no_tag else config.tag if config.tag else None
    cards = wrapper.get_cards(target_lists=target_lists, tag=tag, title_regex=config.match, has_attachments=config.attachments, has_due_date=config.has_due)
    # some modes require a TextDisplay
    if config.json and config.command in ['show', 'grep']:
        display = JSONDisplay(config.no_color)
    elif config.table and config.command != 'review':
        max_list_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_lists('open')], key=len))
        max_label_len = len(max([l.name.decode('utf8') for l in wrapper.main_board.get_labels()], key=len))
        display = TableDisplay(config.no_color, max_list_len, max_label_len)
    else:
        display = TextDisplay(config.no_color)
    if config.command == 'help':
        config.argparser.print_help()
        raise GTDException(0)
    elif config.command == 'workflow':
        print(
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
        raise GTDException(0)
    if config.no_banner:
        display.banner()
    if config.command == 'show':
        if config.type == 'lists':
            for l in wrapper.main_board.get_lists('open'):
                print(l.name.decode('utf8'))
        elif config.type == 'tags':
            for t in wrapper.main_board.get_labels():
                print(t.name.decode('utf8'))
        else:
            with display:
                for card in cards:
                    display.show(card, True)
    elif config.command == 'grep':
        pattern = config.pattern or '.*'
        with display:
            for card in wrapper.get_cards(title_regex=pattern, tag=tag):
                display.show(card, True)
    elif config.command == 'add':
        if config.destination == 'tag':
            label = wrapper.main_board.add_label(config.title, 'black')
            print('Successfully added tag {0}!'.format(label))
        elif config.destination == 'list':
            l = wrapper.main_board.add_list(config.title)
            print('Successfully added list {0}!'.format(l))
        else:
            returned = wrapper.main_list.add_card(name=config.title, desc=config.message)
            if config.edit:
                display.review_card(returned, wrapper)
            else:
                print('Successfully added card {0}!'.format(returned))
    elif config.command == 'batch':
        with display:
            if config.type == 'move':
                for card in cards:
                    display.show(card)
                    if prompt_for_confirmation('Want to move this one?', True):
                        wrapper.move_to_list(card)
            elif config.type == 'delete':
                for card in cards:
                    display.show(card)
                    if prompt_for_confirmation('Should we delete this card?'):
                        card.delete()
                        print('Card deleted!')
            elif config.type == 'due':
                for card in cards:
                    display.show(card)
                    if prompt_for_confirmation('Set due date?'):
                        wrapper.set_due_date(card)
            else:
                for card in cards:
                    display.show(card)
                    if prompt_for_confirmation('Want to tag this one?'):
                        wrapper.add_labels(card)
        print('Batch completed, have a great day!')
    else:
        if config.daily:
            print('Welcome to daily review mode!\nThis combines all "Doing", "Holding", and "Inbound" lists into one big review.\n')
            doing_lists = [wrapper.get_list(l) for l in ['Doing Today', 'Doing this Week', 'Doing this Month']]
            holding = wrapper.get_list(wrapper.config['list_names']['holding'])
            interested_lists = doing_lists + [holding, wrapper.main_list]
            cards = wrapper.get_cards(target_lists=interested_lists, tag=tag, title_regex=config.match)
        display.review_list(cards, wrapper)
        print('All done, have a great day!')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Recieved Ctrl+C, quitting!')
        sys.exit(0)
    except GTDException as e:
        if e.errno == 0:
            sys.exit(0)
        else:
            print('Quitting due to error')
            sys.exit(1)

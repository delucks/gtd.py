import trello
import requests
from todo.exceptions import GTDException


class TrelloConnection:
    '''this one handles connection, retry attempts, stuff like that so it doesn't bail out each
    time we lose connection
    creating a connection requires configuration to be parsed because we need the api keys- so this will need to be invoked
    after the config parser is done doing its thing, with a parameter perhaps being the config
    '''

    def __init__(self, config):
        self.config = config
        self.trello = self.__connect(config)
        # Used to cache the board object
        self._main_board = None
        # and list JSON contents
        self._main_lists = None

    def __connect(self, config):
        trello_client = trello.TrelloClient(
            api_key=config.api_key,
            api_secret=config.api_secret,
            token=config.oauth_token,
            token_secret=config.oauth_token_secret,
        )
        try:
            # A simple API call (data reused in self.main_board) to initiate connection & test our credentials etc
            self.boards = trello_client.fetch_json('/members/me/boards/?filter=open')
            return trello_client
        except requests.exceptions.ConnectionError:
            print('[FATAL] Could not connect to the Trello API!')
            raise GTDException(1)
        except trello.exceptions.Unauthorized:
            print('[FATAL] Trello API credentials are invalid')
            raise GTDException(1)

    def __repr__(self):
        c = 'disconnected' if self.trello is None else 'connected'
        return f'TrelloConnection {c} at {id(self)}'

    def __str__(self):
        return repr(self)

    def main_board(self):
        '''use the configuration to get the main board & return it
        This function avoids py-trello's connection.list_boards() function as it produces O(N) network calls.
        This function is guaranteed to only produce 1 network call, in the trello.Board initialization below.
        '''
        if self._main_board is not None:
            return self._main_board
        # self.boards is a response from the trello API unpacked as a list of dicts
        if self.config.board is None:
            # If no board name is passed, default to the first board
            board_json = self.boards[0]
        else:
            possible = [b for b in self.boards if b['name'] == self.config.board]
            if possible:
                board_json = possible[0]
            else:
                board_json = self.boards[0]
        board_object = trello.Board.from_json(self.trello, json_obj=board_json)
        self._main_board = board_object
        return board_object

    def boards_by_name(self):
        '''Return a mapping of board names present in this account to their JSON contents.
        Useful to potentially avoid a network call when generating mappings for interactive
        completion, and allowing the boards to be turned into objects quickly with Board.from_json
        '''
        return {b['name']: b for b in self.boards}

    def main_lists(self, status_filter='open', force=False):
        '''Load the JSON corresponding to all lists on the main board, to ease setup of CardView'''
        if self._main_lists is None:
            lists_json = self.trello.fetch_json(
                f'/boards/{self.main_board().id}/lists',
                query_params={'cards': 'none', 'filter': status_filter, 'fields': 'all'},
            )
            self._main_lists = lists_json
        return self._main_lists

    def lists_by_id(self):
        '''Return a mapping of list names to IDs on the main board, so that cards can have their
        lists shown without making a network call to retrieve the list names.
        '''
        return {l['id']: l['name'] for l in self.main_lists(status_filter='all', force=True)}

    def inbox_list(self):
        '''use the configuration to get the main board & list from
        Trello, return the list where new cards should go.
        '''
        if getattr(self.config, 'inbox_list', False):
            return [l for l in self.main_board().open_lists() if l.name == self.config.inbox_list][0]
        else:
            return self.main_board().open_lists()[0]

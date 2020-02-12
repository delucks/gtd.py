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
        # Used as a singleton to cache the board object when created
        self._main_board = None

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
        return 'TrelloConnection {0} at {0}'.format(c, id(self))

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

    def inbox_list(self):
        '''use the configuration to get the main board & list from
        Trello, return the list where new cards should go.
        '''
        if getattr(self.config, 'inbox_list', False):
            return [l for l in self.main_board().open_lists() if l.name == self.config.inbox_list][0]
        else:
            return self.main_board().open_lists()[0]

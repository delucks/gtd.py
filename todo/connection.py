import trello
import requests
from todo.exceptions import GTDException


class TrelloConnection:
    '''this one handles connection, retry attempts, stuff like that so it doesn't bail out each
    time we lose connection
    creating a connection requires configuration to be parsed because we need the api keys- so this will need to be invoked
    after the config parser is done doing its thing, with a parameter perhaps being the config

    :param bool autoconnect: should we make a network connection to Trello immediately?
    '''
    def __init__(self, config, autoconnect=True):
        self.autoconnect = autoconnect
        self.config = config
        self.trello = self.__connect(config) if autoconnect else None

    def __connect(self, config):
        trello_client = self.initialize_trello(config)
        try:
            # This is the first connection to the API made by the client
            self.boards = trello_client.list_boards()
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

    def initialize_trello(self, config):
        '''Initializes our connection to the trello API
        :param dict config: parsed configuration from the yaml file
        :returns: trello.TrelloClient client
        '''
        trello_client = trello.TrelloClient(
            api_key=config.api_key,
            api_secret=config.api_secret,
            token=config.oauth_token,
            token_secret=config.oauth_token_secret
        )
        return trello_client

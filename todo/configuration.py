import os
import yaml
import platform
from todo.exceptions import GTDException


class Configuration:
    '''hold global configuration for this application. This class has required
    arguments of the properties we need to connect to the Trello API and some
    other properties that modify global state during each run
    '''
    def __init__(self, api_key, api_secret, oauth_token, oauth_token_secret, **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret
        self.board = kwargs.get('board', None)
        self.banner = kwargs.get('banner', True)
        self.color = kwargs.get('color', True)

    def __repr__(self):
        return '\n'.join([
            'GTD Configuration:',
            '  API key: ' + self.api_key,
            '  API secret: ' + self.api_secret,
            '  OAuth token: ' + self.oauth_token,
            '  OAuth secret: ' + self.oauth_token_secret,
            '  Primary board: '.format(self.board),
            '  Banner? '.format(self.banner),
            '  Use ANSI color? {0}'.format(self.color),
        ])

    def __str__(self):
        return repr(self)

    @staticmethod
    def suggest_config_location():
        '''Do some platform detection and suggest a place for the users' config file to go'''
        system = platform.system()
        if system == 'Windows':
            print('gtd.py support for Windows is rudimentary to none. Try to put your config file in $HOME/.gtd.yaml and run the script again')
            raise GTDException(0)
        elif system == 'Darwin':
            preferred_location = os.path.expanduser('~/Library/Application Support/gtd/gtd.yaml')
        elif system == 'Linux':
            preferred_location = os.path.expanduser('~/.config/gtd/gtd.yaml')
        else:
            preferred_location = os.path.expanduser('~/.gtd.yaml')
        return preferred_location

    @staticmethod
    def all_config_locations():
        return [os.path.expanduser(x) for x in [
            '~/.gtd.yaml',
            '~/.config/gtd/gtd.yaml',
            '~/Library/Application Support/gtd/gtd.yaml',
            '~/.local/etc/gtd.yaml',
            '~/.local/etc/gtd/gtd.yaml',
        ]]

    @staticmethod
    def find_config_file():
        # where to try finding the file in order
        for possible_loc in Configuration.all_config_locations():
            if os.path.isfile(possible_loc):
                return possible_loc
        # If we've gotten this far and did not find the configuration file, it does not exist
        raise GTDException(1)

    @staticmethod
    def from_file(filename=None):
        if filename is None:
            filename = Configuration.find_config_file()
        with open(filename, 'r') as config_yaml:
            file_config = yaml.safe_load(config_yaml)
        for prop in ['api_key', 'api_secret', 'oauth_token', 'oauth_token_secret']:
            if file_config.get(prop, None) is not None:
                # great!
                continue
            else:
                print('A required property {0} in your configuration was not found!'.format(prop))
                print('Check the file {0}'.format(filename))
                raise GTDException(1)
        return Configuration(
            file_config['api_key'],
            file_config['api_secret'],
            file_config['oauth_token'],
            file_config['oauth_token_secret'],
            board=file_config.get('board', None),
            color=file_config.get('color', True),
            banner=file_config.get('banner', True)
        )

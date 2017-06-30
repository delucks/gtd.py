import os
import sys
import yaml

from gtd import __version__, __doc__
from gtd.misc import AttrDict
from gtd.exceptions import GTDException


class ConfigParser:
    '''this one handles the yaml config file and possibly
    eventually a python config files

    :param str config_file: path to the yaml configuration file for this program
    '''
    def __init__(self, config_file='gtd.yaml'):
        self.required_properties = ['api_key', 'api_secret', 'oauth_token', 'oauth_token_secret']
        # try to get configuration from yaml config file
        yaml_config = self.__parse_yaml(config_file) if os.path.isfile(config_file) else None
        # this performs implicit validation of the configuration
        self.config = self.__merge_config(yaml_config)

    def __merge_config(self, yaml_config=None):
        #TODO add support for a python plugin style config file
        new_config = AttrDict()
        if yaml_config:
            for param, val in yaml_config.items():
                # skip properties already overridden on the command line
                if param in self.required_properties:
                    if hasattr(new_config, param):
                        continue
                new_config[param] = val
        return self._validate_config(new_config)

    def __parse_yaml(self, config_file):
        '''load yaml configuration file'''
        with open(config_file, 'r') as config_yaml:
            properties = yaml.safe_load(config_yaml)
            return self._validate_yaml(properties)

    def _validate_config(self, config):
        '''make sure properties needed for program operation are found in the configurations struct'''
        for prop in self.required_properties:
            if hasattr(config, prop) and prop is not None:
                # great!
                continue
            else:
                print('A required property {0} in your configuration was not found!'.format(prop))
                raise GTDException(1)
        return config

    def _validate_yaml(self, config):
        '''make sure the required properties of the yaml configuration file are found,
        and raise a GTDException otherwise'''
        try:
            config['board_name']
            config['list']
            return config
        except KeyError as e:
            print('A required property {0} in your configuration was not found!'.format(e))
            raise GTDException(1)

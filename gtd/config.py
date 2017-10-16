import os
import yaml
from gtd.misc import AttrDict
from gtd.exceptions import GTDException


class ConfigParser:
    '''this class handles the yaml config file and possibly
    eventually a python config files

    :param str config_file: path to the yaml configuration file for this program
    '''
    def __init__(self, config_file='gtd.yaml'):
        self.required_properties = ['api_key', 'api_secret', 'oauth_token', 'oauth_token_secret', 'board_name']
        # try to get configuration from yaml config file
        yaml_config = self.__parse_yaml(config_file) if os.path.isfile(config_file) else None
        # this performs implicit validation of the configuration
        self.config = self.__merge_config(yaml_config)

    def __merge_config(self, yaml_config=None):
        new_config = AttrDict()
        # Defaults
        new_config['color'] = True
        new_config['banner'] = True
        if yaml_config:
            for param, val in yaml_config.items():
                new_config[param] = val
        return self._validate_config(new_config)

    def __parse_yaml(self, config_file):
        '''load yaml configuration file'''
        with open(config_file, 'r') as config_yaml:
            return yaml.safe_load(config_yaml)

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

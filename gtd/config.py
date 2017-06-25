import os
import sys
import yaml
import argparse

from gtd import __version__, __doc__
from gtd.misc import AttrDict
from gtd.exceptions import GTDException


class ConfigParser:
    '''this one handles the yaml config file and possibly eventually the python config files
    as well as argument parsing for an interactive session. it should intelligently merge all of those
    settings, giving preference to runtime options over configuration settings when possible

    :param bool parse_args: collect commandline arguments?
    :param list args: list of arguments to parse. Defaults to sys.argv
    :param str config_file: path to the yaml configuration file for this program
    '''
    def __init__(self, parse_args=True, args=sys.argv[1:], config_file='gtd.yaml'):
        self.required_properties = ['api_key', 'api_secret', 'oauth_token', 'oauth_token_secret']
        # try to get configuration from the command line
        interactive_args = self.__argument_parser(args) if parse_args else None
        # try to get configuration from yaml config file
        yaml_config = self.__parse_yaml(config_file) if os.path.isfile(config_file) else None
        # this performs implicit validation of the configuration
        self.config = self.__merge_config(interactive_args, yaml_config)

    def __merge_config(self, cli_args=None, yaml_config=None):
        #TODO add support for a python plugin style config file
        new_config = AttrDict()
        if cli_args:
            # parse the Namespace object into our struct
            for param, val in cli_args._get_kwargs():
                # do not copy required properties that are unset into the configuration struct
                if param in self.required_properties and val is None:
                    continue
                new_config[param] = val
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

    def __argument_parser(self, arguments):
        selection_opts = argparse.ArgumentParser(add_help=False)
        selection_opts.add_argument('-m', '--match', metavar='PCRE', help='filter cards to this regex on their title', default=None)
        selection_opts.add_argument('-l', '--list', metavar='NAME', help='filter cards to this list', default=None)
        selection_opts.add_argument('-j', '--json', action='store_true', help='display results as a JSON list')
        selection_opts.add_argument('--table', action='store_true', help='display results in a table the width of the terminal')
        selection_opts.add_argument('-a', '--attachments', action='store_true', help='select cards which have attachments')
        selection_opts.add_argument('-dd', '--has-due', action='store_true', help='select cards which have due dates')
        tag_group = selection_opts.add_mutually_exclusive_group(required=False)
        tag_group.add_argument('-t', '--tag', metavar='NAME', help='filter cards to this tag', default=None)
        tag_group.add_argument('--no-tag', help='only select cards without a tag', action='store_true')
        # Override arguments that should apply everywhere
        common = argparse.ArgumentParser(description='{0} version {1}'.format(__doc__, __version__), parents=[selection_opts])
        common.add_argument('-c', '--no-color', help='disable colorized output using ANSI escape codes', action='store_false')
        common.add_argument('-b', '--no-banner', help='do not print a banner', action='store_false')
        common.add_argument('--api-key', help='Trello connection API Key')
        common.add_argument('--api-secret', help='Trello connection API Secret')
        common.add_argument('--oauth-token', help='Trello connection OAuth Token')
        common.add_argument('--oauth-secret', help='Trello connection OAuth Secret')
        commands = common.add_subparsers(dest='command')
        commands.add_parser('help', help='display this message')
        add = commands.add_parser('add', help='create a new card, tag, or list')
        add.add_argument('destination', choices=('tag', 'card', 'list'), help='type of item to create')
        add.add_argument('title', help='title for the new item')
        add.add_argument('-m', '--message', help='description for a new card')
        add.add_argument('--edit', help='review the card right after creating it', action='store_true')
        grep = commands.add_parser('grep', help='search through the titles of all cards on the board', parents=[selection_opts])
        grep.add_argument('pattern', help='regex to search card titles for', nargs='?')
        show = commands.add_parser('show', help='print all cards of one type', parents=[selection_opts])
        show.add_argument('type', choices=('lists', 'cards', 'tags'), default='lists')
        batch = commands.add_parser('batch', help='process cards quickly using only one action: tag, move, or delete', parents=[selection_opts])
        batch.add_argument('type', choices=('tag', 'move', 'delete', 'due'), default='move')
        review = commands.add_parser('review', help='process cards with a rich menu interface', parents=[selection_opts])
        review.add_argument('-d', '--daily', help='start a daily review mode, which goes through several lists at once', action='store_true')
        commands.add_parser('workflow', help='show the GTD process')
        # this is needed to allow no args to execute the "review" command
        common.set_defaults(command='review', daily=False)
        self.argparser = common
        return common.parse_args(arguments)

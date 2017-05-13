#!/usr/bin/env python
import os
import yaml
import pytest
import tempfile

from gtd.config import ConfigParser
from gtd.exceptions import GTDException

def test_yaml_parser():
    # open and parse our example configs, sunny case
    c = ConfigParser(False, None, config_file='gtd.yaml.example')
    assert c.config == {
        'board_name': 'GTD',
        'list_names': {
            'blocked': 'Blocked',
            'done': 'Done',
            'holding': 'Holding',
            'in_progress': 'Doing',
            'incoming': 'Incoming',
            'projects': 'Projects',
            'reference': 'Reference',
            'someday': 'Ideas'
        },
        'testing_board_name': 'Unused',
        'api_key': 'your-api-key',
        'api_secret': 'your-api-secret',
        'oauth_token': 'your-oauth-token',
        'oauth_token_secret': 'your-oauth-secret'
    }
    # mock a bad config file
    fd, name = tempfile.mkstemp(prefix='gtd_test_')
    with open(fd, 'w') as tmpfile:
        tmpfile.write(yaml.dump({
            'board_name': 123,
            'trello': {
                'api_key': 'nope',
                'misspelled': None
            }
        }))
    with pytest.raises(GTDException):
        ConfigParser(False, None, config_file=name)
    os.remove(name)

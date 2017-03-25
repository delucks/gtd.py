#!/usr/bin/env python
from gtd import TrelloWrapper, GTDException

import trello
import yaml
import pytest
import tempfile

@pytest.fixture
def unconnected_wrapper():
    return TrelloWrapper(config_file='gtd.yaml.example', autoconnect=False)

def test_parse_configuration(unconnected_wrapper):
    # open and parse our example configs, sunny case
    assert unconnected_wrapper.config == {
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
        'trello': {
            'api_key': 'your-api-key',
            'api_secret': 'your-api-secret',
            'oauth_token': 'your-oauth-token',
            'oauth_token_secret': 'your-oauth-secret'
        }
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
        bad_wrapper = TrelloWrapper(config_file=name, autoconnect=False)

class Trello_Like_Object:
    def __init__(self, name):
        if isinstance(name, str):
            self.name = bytes(name, 'utf8')
        else:
            self.name = name
    def __eq__(self, other):
        return self.name == other.name
    def __hash__(self):
        return hash(self.name)
    def __repr__(self):
        return 'TLO: {0}'.format(self.name)

def test_filter_by_name(unconnected_wrapper):
    ex_iter = [Trello_Like_Object(b) for b in [
        'Nonsense1',
        'Garbage',
        'Heap of trash',
        'Mountain of dung'
    ]]
    assert unconnected_wrapper._filter_by_name(ex_iter, 'Nonse') == Trello_Like_Object('Nonsense1')
    assert unconnected_wrapper._filter_by_name(ex_iter, 'trash') == Trello_Like_Object('Heap of trash')
    assert unconnected_wrapper._filter_by_name(ex_iter, 'dung') == Trello_Like_Object('Mountain of dung')

def test_with_connection():
    assert TrelloWrapper('Inbound'), 'No connection'

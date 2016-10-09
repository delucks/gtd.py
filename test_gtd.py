#!/usr/bin/env python
from gtd import parse_configuration, GTD_Controller, GTD_Display

import trello
import pytest
# TODO upgrade my version of python and get rid of this
import mock

def test_parse_configuration():
    # open and parse our example configs
    properties = parse_configuration('gtd.yaml.example')
    assert properties == {
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

def test_bad_trello_key():
    '''test the case where we pass invalid trello creds
    '''
    configs = parse_configuration('gtd.yaml.example')
    with pytest.raises(trello.Unauthorized):
        g = GTD_Controller(configs, None)

@pytest.fixture(scope='session')
def configs():
    return parse_configuration()

@pytest.fixture
def uninitialized(configs):
    '''a GTD_Controller that hasn't been __init__'d yet
    '''
    with mock.patch.object(GTD_Controller, '__init__', return_value=None) as mock_init:
        return GTD_Controller(configs, None)

@pytest.fixture(scope='session')
def testing_board(configs):
    '''a GTD_Controller that's initialized on a testing board
    '''
    with mock.patch.object(GTD_Controller, '__init__', return_value=None) as mock_init:
        g = GTD_Controller(configs, None, testing=True)
        g.trello = g.initialize_trello(configs)
        return g

def test_initialize_trello(uninitialized, configs):
    with pytest.raises(AttributeError):
        getattr(uninitialized, 'trello')
    client = uninitialized.initialize_trello(configs)
    assert type(client) == trello.TrelloClient
    assert client.api_key == configs['trello']['api_key']
    assert client.oauth.client.client_key == configs['trello']['api_key']
    assert client.api_secret == configs['trello']['api_secret']
    assert client.oauth.client.client_secret == configs['trello']['api_secret']
    
def test_validate_config(uninitialized, configs):
    uninitialized.trello = uninitialized.initialize_trello(configs)
    board = uninitialized.validate_config(configs)
    # make sure the board was initialized and bound correctly
    assert type(board) == trello.Board
    assert board.name.decode('utf-8') == configs['board_name']
    assert board == uninitialized.board
    # make sure the lists were found and registered
    assert type(uninitialized.lists) == dict
    for label, id in uninitialized.lists.items():
        list_name = configs['list_names'][label]
        assert uninitialized._find_list_id(board, list_name) == id

def test_nonexistent_board(testing_board, configs):
    assert testing_board._validate_board_existence(configs['testing_board_name']) == False

import pytest
import trello
from todo.connection import TrelloConnection
from todo.configuration import Configuration
# from todo.input import BoardTool


@pytest.fixture
def config():
    return Configuration.from_file()


@pytest.fixture
def test_conn(config):
    if config.test_board is None:
        pytest.fail('Define test_board in your config to run gtd.py tests')
    return TrelloConnection(config)


@pytest.fixture
def test_board(config, test_conn):
    '''Creates the board if it doesn't already exist'''
    possible = [b for b in test_conn.boards if b['name'] == config.test_board]
    if possible:
        board_json = possible[0]
        board = trello.Board.from_json(test_conn.trello, json_obj=board_json)
    else:
        board = test_conn.trello.add_board(config.test_board)
    return board

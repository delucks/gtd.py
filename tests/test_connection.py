import pytest
import trello
from todo.connection import TrelloConnection

def test_connection_basics(off_connection):
    assert off_connection.trello is None

def test_connection_network(on_connection):
    assert isinstance(on_connection.trello, trello.TrelloClient)
    assert hasattr(on_connection, 'boards')

import pytest
from todo.connection import TrelloConnection

@pytest.fixture
def on_connection():
    c = ConfigParser(parse_args=False).config
    return TrelloConnection(c)

@pytest.fixture
def off_connection():
    return TrelloConnection(None, False)

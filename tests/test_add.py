import click
from click.testing import CliRunner
from gtd import cli
from conftest import TEST_LIST_INBOX


TEST_TAG_NAME = 'gtd.py__CREATED_TAG'
TEST_LIST_CREATION = 'gtd.py__CREATED_LIST'
TEST_CARD_CREATION = 'gtd.py__CREATED_CARD'


def test_add_board(config, test_conn):
    # This test creates a new board in your account because py-trello doesn't support board deletion yet
    # TODO do not create duplicate boards
    runner = CliRunner()
    result = runner.invoke(cli, ['add', 'board', config.test_board])
    assert result.exit_code == 0
    boards = test_conn.trello.list_boards('open')
    todelete = [b for b in boards if b.name == config.test_board]
    assert todelete
    for b in todelete:
        b.close()


def test_add_tag(config, test_board):
    # The "-c blue" in there is a lame attempt at testing the color handling code
    runner = CliRunner()
    result = runner.invoke(cli, ['--board', config.test_board, 'add', 'tag', '-c', 'blue', TEST_TAG_NAME])
    assert result.exit_code == 0
    assert TEST_TAG_NAME in result.output
    assert TEST_TAG_NAME in [o.name for o in test_board.get_labels()]
    todelete = [l for l in test_board.get_labels() if l.name == TEST_TAG_NAME]
    assert todelete
    for t in todelete:
        test_board.delete_label(t.id)


def test_add_list(config, test_board):
    runner = CliRunner()
    result = runner.invoke(cli, ['--board', config.test_board, 'add', 'list', TEST_LIST_CREATION])
    assert result.exit_code == 0
    assert TEST_LIST_CREATION in result.output
    assert TEST_LIST_CREATION in [o.name for o in test_board.get_lists('open')]
    todelete = [l for l in test_board.get_lists('open') if l.name == TEST_LIST_CREATION]
    assert todelete
    for l in todelete:
        l.close()


def test_add_card(config, test_list):
    # Untestable: -e/--edit flag
    runner = CliRunner()
    # Test the -l flag
    result = runner.invoke(
        cli, ['--board', config.test_board, 'add', 'card', '-l', TEST_LIST_INBOX, TEST_CARD_CREATION]
    )
    assert result.exit_code == 0
    assert len(test_list.list_cards()) == 1
    # Test the -m flag with the -l flag
    result = runner.invoke(
        cli,
        [
            '--board',
            config.test_board,
            'add',
            'card',
            '-m',
            'Sample Description',
            '-l',
            TEST_LIST_INBOX,
            TEST_CARD_CREATION,
        ],
    )
    assert result.exit_code == 0
    assert len(test_list.list_cards()) == 2
    # Test the default no-flags behavior
    result = runner.invoke(cli, ['--board', config.test_board, 'add', 'card', TEST_CARD_CREATION])
    assert result.exit_code == 0
    assert len(test_list.list_cards()) == 3
    # Clean up
    for c in test_list.list_cards():
        c.delete()

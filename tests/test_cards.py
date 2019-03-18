import click
from click.testing import CliRunner
from gtd import cli


def test_add_tag(config, test_board):
    TEST_TAG_NAME = 'gtd.py__SIGNAL_TAG'
    runner = CliRunner()
    result = runner.invoke(cli, ['--board', config.test_board, 'add', 'tag', TEST_TAG_NAME])
    assert result.exit_code == 0
    assert TEST_TAG_NAME in result.output
    assert TEST_TAG_NAME in [o.name for o in test_board.get_labels()]
    todelete = [l for l in test_board.get_labels() if l.name == TEST_TAG_NAME]
    assert todelete
    for t in todelete:
        test_board.delete_label(t.id)

import json
import pytest
from click.testing import CliRunner
from gtd import cli


def test_show_boards():
    '''This test doesn't do too much. It's difficult to test "show boards" because there's always going to be variation
    in each person's Trello account. This test gets the count of open boards and the count of all boards, then asserts
    that there are more boards in the full set than the open set. Since pytests modules run in alphabetical order, this
    is guaranteed to be the case as test_add.py has already created & archived a board.
    '''
    runner = CliRunner()
    args = ['show', 'boards', '--json']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        open_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        pytest.fail(f'Output of `{" ".join(args)}` is not valid JSON')
    # Now include the all-flag
    args = ['show', 'boards', '--json', '--show-all']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        archived_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        pytest.fail(f'Output of `{" ".join(args)}` is not valid JSON')
    assert len(archived_results) > len(open_results)
    # Last basic test: run "show boards" with no arguments and assert it gets a 0-error code
    # ¯\_(ツ)_/¯
    result = runner.invoke(cli, ['show', 'boards'])
    assert result.exit_code == 0, result.output


def test_show_lists(config, test_board):
    '''Mostly ditto for "show lists"
    '''
    runner = CliRunner()
    args = ['--board', config.test_board, 'show', 'lists', '--json']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        open_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        pytest.fail(f'Output of `{" ".join(args)}` is not valid JSON')
    args = ['--board', config.test_board, 'show', 'lists', '--json', '--show-all']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        all_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        pytest.fail(f'Output of `{" ".join(args)}` is not valid JSON')
    assert len(all_results) > len(open_results)
    assert len(all_results) == len(test_board.get_lists('all'))
    assert len(open_results) == len(test_board.get_lists('open'))

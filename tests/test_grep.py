import json
import pytest
from click.testing import CliRunner
from gtd import cli


def test_grep(config, test_list):
    cards = []
    runner = CliRunner()
    # Test no-flag behavior
    cards.append(test_list.add_card('GREP_TESTING'))
    args = ['--board', config.test_board, 'grep', '--json', 'GREP_TEST']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        grep_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        [c.delete() for c in cards]
        pytest.fail('Output of `{0}` is not valid JSON'.format(' '.join(args)))
    assert len(grep_results) == 1
    # Test -i/--insensitive
    cards.append(test_list.add_card('grep_t'))
    args = ['--board', config.test_board, 'grep', '--json', '-i', 'gReP.t']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        grep_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        [c.delete() for c in cards]
        pytest.fail('Output of `{0}` is not valid JSON'.format(' '.join(args)))
    assert len(grep_results) == 2
    # Test -e/--regexp
    cards.append(test_list.add_card('foo'))
    cards.append(test_list.add_card('bar'))
    cards.append(test_list.add_card('baz'))
    args = ['--board', config.test_board, 'grep', '--json', '-e', 'foo', '-e', 'bar']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        grep_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        [c.delete() for c in cards]
        pytest.fail('Output of `{0}` is not valid JSON'.format(' '.join(args)))
    assert len(grep_results) == 2
    args = ['--board', config.test_board, 'grep', '--json', '-i', '-e', 'grep', '-e', 'ba[rz]']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        grep_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        [c.delete() for c in cards]
        pytest.fail('Output of `{0}` is not valid JSON'.format(' '.join(args)))
    # grep_t, GREP_TESTING, bar, and baz
    assert len(grep_results) == 4
    # Test -e and an argument given at the same time
    args = ['--board', config.test_board, 'grep', '--json', '-i', '-e', 'foo', '-e', 'grep', 'ba[rz]']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    try:
        grep_results = json.loads(result.output)
    except json.decoder.JSONDecodeError:
        print(result.output)
        [c.delete() for c in cards]
        pytest.fail('Output of `{0}` is not valid JSON'.format(' '.join(args)))
    # grep_t, GREP_TESTING, foo, bar, and baz
    assert len(grep_results) == 5
    # Test -c/--count
    args = ['--board', config.test_board, 'grep', '-c', 'foo|grep|ba[rz]']
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    # Test whether the count matches our expectation
    assert int(result.output) == 4
    # Cleanup
    for c in cards:
        c.delete()

"""
Regression tests for the Case Study #3 clone refactorings (Track B).

They pin the behaviour of the code paths that were de-duplicated so the
extracted helpers keep behaving exactly like the original clones.

"""
import argparse
from unittest import mock

import pytest

from httpie.cli.argparser import get_failed_action
from httpie.manager.cli import COMMANDS
from httpie.status import ExitStatus
from .utils import MockEnvironment, http


# C01 — httpie/core.py: shared KeyboardInterrupt / SystemExit handling

@pytest.mark.parametrize('code, expected', [
    (0, ExitStatus.SUCCESS),
    (1, ExitStatus.ERROR),
    (2, ExitStatus.ERROR),
])
def test_system_exit_in_program_exit_status(code, expected):
    with mock.patch('httpie.core.program', side_effect=SystemExit(code)):
        r = http('--offline', 'example.org', tolerate_error_exit_status=True)
    assert r.exit_status == expected
    assert r.stderr == ('' if code == 0 else '\n')


@pytest.mark.parametrize('code, expected', [
    (0, ExitStatus.SUCCESS),
    (2, ExitStatus.ERROR),
])
def test_system_exit_during_arg_parsing_exit_status(code, expected):
    with mock.patch('httpie.cli.definition.parser.parse_args',
                    side_effect=SystemExit(code)):
        r = http('--offline', 'example.org', tolerate_error_exit_status=True)
    assert r.exit_status == expected


@pytest.mark.parametrize('target', [
    'httpie.cli.definition.parser.parse_args',
    'httpie.core.program',
])
def test_keyboard_interrupt_is_reraised_with_traceback(target):
    with mock.patch(target, side_effect=KeyboardInterrupt()):
        with pytest.raises(KeyboardInterrupt):
            http('--traceback', '--offline', 'example.org', env=MockEnvironment())


# C03 — httpie/cli/argparser.py: shared "which action failed" inspection

def test_get_failed_action_returns_action_from_argument_error():
    action = argparse.Action(option_strings=['--style'], dest='style')
    try:
        raise argparse.ArgumentError(action, 'invalid choice')
    except argparse.ArgumentError:
        assert get_failed_action() is action


def test_get_failed_action_without_active_error():
    assert get_failed_action() is None


def test_get_failed_action_ignores_other_exceptions():
    try:
        raise ValueError('not an argparse error')
    except ValueError:
        assert get_failed_action() is None


def test_invalid_option_value_still_shows_option_in_usage():
    r = http('--style=invalid', 'example.org', tolerate_error_exit_status=True)
    assert r.exit_status == ExitStatus.ERROR
    assert '--style' in r.stderr


# C04 — httpie/manager/cli.py: shared plugin TARGET argument definition

@pytest.mark.parametrize('verb', ['install', 'upgrade', 'uninstall'])
def test_plugin_target_argument_help_matches_subcommand(verb):
    _, target_arg = COMMANDS['plugins'][verb]
    assert target_arg == {
        'dest': 'targets',
        'metavar': 'TARGET',
        'nargs': target_arg['nargs'],
        'help': f'targets to {verb}',
    }

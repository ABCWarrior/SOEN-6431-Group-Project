import argparse
import pytest
import shutil
import os

from httpie.cli.constants import PRETTY_MAP
from tests.utils import http

NAKED_BASE_TEMPLATE = """\
usage:
    http {extra_args}[METHOD] URL [REQUEST_ITEM ...]

error:
    {error_msg}

for more information:
    run 'http --help' or visit https://httpie.io/docs/cli

"""

NAKED_HELP_MESSAGE = NAKED_BASE_TEMPLATE.format(
    extra_args="",
    error_msg="the following arguments are required: URL"
)

NAKED_HELP_MESSAGE_PRETTY_WITH_NO_ARG = NAKED_BASE_TEMPLATE.format(
    extra_args="--pretty {all, colors, format, none} ",
    error_msg="argument --pretty: expected one argument"
)


def _invalid_choice_error(value, choices):
    # The wording differs between Python releases: recent 3.12 releases
    # print the choices without quotes, 3.11 and 3.14 quote them. Ask the
    # running argparse for its own wording instead of hard-coding one.
    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument('--pretty', choices=choices)
    try:
        parser.parse_args(['--pretty', value])
    except argparse.ArgumentError as exc:
        return str(exc)


NAKED_HELP_MESSAGE_PRETTY_WITH_INVALID_ARG = NAKED_BASE_TEMPLATE.format(
    extra_args="--pretty {all, colors, format, none} ",
    error_msg=_invalid_choice_error('$invalid', sorted(PRETTY_MAP)),
)


PREDEFINED_TERMINAL_SIZE = (200, 100)


@pytest.fixture(scope="function")
def ignore_terminal_size(monkeypatch):
    """Some tests wrap/crop the output depending on the
    size of the executed terminal, which might not be consistent
    through all runs.

    This fixture ensures every run uses the same exact configuration.
    """

    def fake_terminal_size(*args, **kwargs):
        return os.terminal_size(PREDEFINED_TERMINAL_SIZE)

    # Setting COLUMNS as an env var is required for 3.8<
    monkeypatch.setitem(os.environ, 'COLUMNS', str(PREDEFINED_TERMINAL_SIZE[0]))
    monkeypatch.setattr(shutil, 'get_terminal_size', fake_terminal_size)
    monkeypatch.setattr(os, 'get_terminal_size', fake_terminal_size)


@pytest.mark.parametrize(
    'args, expected_msg', [
        ([], NAKED_HELP_MESSAGE),
        (['--pretty'], NAKED_HELP_MESSAGE_PRETTY_WITH_NO_ARG),
        (['pie.dev', '--pretty'], NAKED_HELP_MESSAGE_PRETTY_WITH_NO_ARG),
        (['--pretty', '$invalid'], NAKED_HELP_MESSAGE_PRETTY_WITH_INVALID_ARG),
    ]
)
def test_naked_invocation(ignore_terminal_size, args, expected_msg):
    result = http(*args, tolerate_error_exit_status=True)
    assert result.stderr == expected_msg

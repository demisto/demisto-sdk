import logging

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from TestSuite.test_tools import str_in_call_args_list


@pytest.mark.parametrize("error_code", ["BA102"])
def test_error_code_info_end_to_end(mocker, error_code):
    """
    Given
     - an error code

    When
     - executing the error-code command via cli

    Then
     - make sure the command does not fail and exits gracefully.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["error-code", "-i", error_code])
    assert result.exit_code == 0
    assert not result.exception
    assert logger_info.called


def test_error_code_info_sanity(mocker, monkeypatch):
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["error-code", "-i", "BA100"])

    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Function: wrong_version(expected='-1')",
                "The version for our files should always be -1, please update the file.",
            ]
        ]
    )
    assert result.exit_code == 0


def test_error_code_info_failure(mocker, monkeypatch):
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["error-code", "-i", "KELLER"])

    assert str_in_call_args_list(logger_info.call_args_list, "No such error")
    assert result.exit_code == 1

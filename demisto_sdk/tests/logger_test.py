import tempfile
from pathlib import Path
from typing import Optional

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_SDK_LOG_FILE_PATH, LOGS_DIR
from demisto_sdk.commands.common.loguru_logger import calculate_log_dir


def _run_calculate_dir_test(
    monkeypatch,
    input_path: Path,
    environment_variable_value: Optional[str],
    expected_result: Path,
):
    """Prevents code duplication in calculate_log_dir tests"""
    with monkeypatch.setenv(DEMISTO_SDK_LOG_FILE_PATH, environment_variable_value):
        assert calculate_log_dir(input_path) == expected_result


def test_calculate_dir_path_input_dir(monkeypatch):
    """
    Given:
        A Path object representing an existing directory
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_calculate_dir_test(
            monkeypatch=monkeypatch,
            input_path=Path(tmpdir),
            environment_variable_value=None,
            expected_result=LOGS_DIR,
        )

def test_calculate_dir_path_input_nonexistent_dir(monkeypatch):
    """
    Given:
        A Path object representing an existing directory
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _run_calculate_dir_test(
            monkeypatch=monkeypatch,
            input_path=Path(tmpdir),
            environment_variable_value=None,
            expected_result=LOGS_DIR,
        )

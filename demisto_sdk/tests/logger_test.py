import shutil
import tempfile
from pathlib import Path

from demisto_sdk.commands.common.constants import DEMISTO_SDK_LOG_FILE_PATH, LOGS_DIR
from demisto_sdk.commands.common.logger import calculate_log_dir


def test_calculate_dir_path_no_input():
    """
    Given:
        No input directory provided
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected default path
    """
    assert calculate_log_dir(None) == LOGS_DIR


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
        path = Path(tmpdir)
        assert calculate_log_dir(path) == path


def test_calculate_dir_path_input_nonexistent_dir(monkeypatch):
    """
    Given:
        A Path object representing a directory that doesn't exist
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path (creating the directory)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.rmtree(temp_dir)  # delete the temp dir
        assert not Path(temp_dir).exists()  # make sure it's deleted

        expected_path = Path(temp_dir, "subfolder", "even deeper folder")
        assert calculate_log_dir(expected_path) == expected_path
        assert expected_path.exists()


def test_calculate_dir_path_input_file():
    """
    Given:
        A Path object representing a file
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path (using the parent directory)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()
        temp_file = Path(temp_dir, "test_file.txt")
        temp_file.touch()
        assert calculate_log_dir(Path(temp_file)) == temp_dir_path


def test_calculate_dir_path_environment_variable(monkeypatch):
    """
    Given:
        The DEMISTO_SDK_LOG_FILE_PATH environment variable is set
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path (using the environment variable)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setenv(DEMISTO_SDK_LOG_FILE_PATH, temp_dir)
        assert calculate_log_dir(None) == Path(temp_dir)


def test_calculate_dir_path_input_overrides_environment_variable(monkeypatch):
    """
    Given:
        The DEMISTO_SDK_LOG_FILE_PATH environment variable is set,
        and a Path object is provided as input
    When:
        Calling `calculate_log_dir` function
    Then:
        Ensure the returned path is the expected path (using the input Path object)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setenv(DEMISTO_SDK_LOG_FILE_PATH, "/some/other/path")
        assert calculate_log_dir(Path(temp_dir)) == Path(temp_dir)

import pytest
from pathlib import Path
from typing import List
from demisto_sdk.commands.lint.linter import Linter


@pytest.fixture(scope='module')
def linter_obj() -> Linter:
    return Linter(pack_dir=Path(__file__).parent / 'data' / 'Integration' / 'intergration_sample',
                  content_path=Path(__file__).parent / 'test_data',
                  req_3=["pytest==3.0"],
                  req_2=["pytest==2.0"])


@pytest.fixture(scope='module')
def lint_files() -> List[Path]:
    return [Path(__file__).parent / 'test_data' / 'Integration' / 'intergration_sample' / 'intergration_sample.py']


class TestFlake8:
    def test_run_flake8_success(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        linter.run_command_os.return_value = ('', '', 0)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files)

        assert exit_code == 0b0, "Exit code should be 0"
        assert output == '', "Output should be empty"

    def test_run_flake8_fail_lint(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = (expected_output, '', 1)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_flake8_usage_stderr(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = ('not good', expected_output, 1)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_flake8_exception(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import helpers

        mocker.patch.object(helpers, 'Popen')
        expected_output = 'Boom'
        helpers.Popen.side_effect = OSError(expected_output)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"


class TestBandit:
    def test_run_bandit_success(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        linter.run_command_os.return_value = ('', '', 0)

        exit_code, output = linter_obj._run_bandit(lint_files=lint_files)

        assert exit_code == 0b0, "Exit code should be 0"
        assert output == '', "Output should be empty"

    def test_run_bandit_fail_lint(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = (expected_output, '', 1)

        exit_code, output = linter_obj._run_bandit(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_bandit_usage_stderr(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = ('not good', expected_output, 1)

        exit_code, output = linter_obj._run_bandit(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_bandit_exception(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import helpers

        mocker.patch.object(helpers, 'Popen')
        expected_output = 'Boom'
        helpers.Popen.side_effect = OSError(expected_output)

        exit_code, output = linter_obj._run_bandit(lint_files=lint_files)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"


class TestMypy:
    def test_run_mypy_success(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        linter.run_command_os.return_value = ('Success: no issues found', '', 0)

        exit_code, output = linter_obj._run_mypy(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b0, "Exit code should be 0"
        assert output == '', "Output should be empty"

    def test_run_mypy_fail_lint(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = (expected_output, '', 1)

        exit_code, output = linter_obj._run_mypy(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_mypy_usage_stderr(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = ('not good', expected_output, 1)

        exit_code, output = linter_obj._run_mypy(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_mypy_exception(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import helpers

        mocker.patch.object(helpers, 'Popen')
        expected_output = 'Boom'
        helpers.Popen.side_effect = OSError(expected_output)

        exit_code, output = linter_obj._run_mypy(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"


class TestRunLintInHost:
    """Flake8/Bandit/Mypy"""

    def test_run_one_lint_check(self):
        """Run only one lint check"""

    def test_run_two_lint_check(self):
        """Run two lint check"""

    def test_run_all_lint_check(self):
        """Run all lint check"""

    def test_no_lint_files(self):
        """No lint files exsits - not running any lint check"""

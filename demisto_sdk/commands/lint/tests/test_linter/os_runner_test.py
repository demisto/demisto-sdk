from pathlib import Path
from typing import List

import pytest

from demisto_sdk.commands.lint.linter import Linter


class TestFlake8:
    def test_run_flake8_success(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        linter.run_command_os.return_value = ('', '', 0)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b0, "Exit code should be 0"
        assert output == '', "Output should be empty"

    def test_run_flake8_fail_lint(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = (expected_output, '', 1)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_flake8_usage_stderr(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = ('not good', expected_output, 1)

        exit_code, output = linter_obj._run_flake8(lint_files=lint_files, py_num=3.7)

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


class TestVulture:
    def test_run_vulture_success(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        linter.run_command_os.return_value = ('', '', 0)

        exit_code, output = linter_obj._run_vulture(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b0, "Exit code should be 0"
        assert output == '', "Output should be empty"

    def test_run_vulture_fail_lint(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = (expected_output, '', 1)

        exit_code, output = linter_obj._run_vulture(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"

    def test_run_vulture_usage_stderr(self, linter_obj: Linter, lint_files: List[Path], mocker):
        from demisto_sdk.commands.lint import linter

        mocker.patch.object(linter, 'run_command_os')
        expected_output = 'Error code found'
        linter.run_command_os.return_value = ('not good', expected_output, 1)

        exit_code, output = linter_obj._run_vulture(lint_files=lint_files, py_num=3.7)

        assert exit_code == 0b1, "Exit code should be 1"
        assert output == expected_output, "Output should be empty"


class TestRunLintInHost:
    """Flake8/Bandit/Mypy/Vulture"""

    @pytest.mark.parametrize(argnames="no_flake8, no_xsoar_linter, no_bandit, no_mypy, no_vulture",
                             argvalues=[(True, False, True, True, False),
                                        (False, False, True, True, True),
                                        (True, False, True, False, True),
                                        (True, False, False, True, True)])
    @pytest.mark.usefixtures("linter_obj", "mocker", "lint_files")
    def test_run_one_lint_check_success(self, mocker, linter_obj, lint_files, no_flake8: bool, no_xsoar_linter: bool,
                                        no_bandit: bool, no_mypy: bool, no_vulture: bool):
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": False,
            "version_two": False,
            "lint_files": lint_files,
            "additional_requirements": []
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        linter_obj._run_flake8.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_run_bandit')
        linter_obj._run_bandit.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        linter_obj._run_xsoar_linter.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_run_mypy')
        linter_obj._run_mypy.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_run_vulture')
        linter_obj._run_vulture.return_value = (0b0, '')
        linter_obj._run_lint_in_host(no_flake8=no_flake8,
                                     no_xsoar_linter=no_xsoar_linter,
                                     no_bandit=no_bandit,
                                     no_mypy=no_mypy,
                                     no_vulture=no_vulture)
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_flake8:
            linter_obj._run_flake8.assert_called_once()
            assert linter_obj._pkg_lint_status.get("flake8_errors") is None
        if not no_xsoar_linter:
            linter_obj._run_xsoar_linter.assert_called_once()
            assert linter_obj._pkg_lint_status.get("xsoar_linter_errors") is None
        elif not no_bandit:
            linter_obj._run_bandit.assert_called_once()
            assert linter_obj._pkg_lint_status.get("bandit_errors") is None
        elif not no_mypy:
            linter_obj._run_mypy.assert_called_once()
            assert linter_obj._pkg_lint_status.get("mypy_errors") is None
        elif not no_vulture:
            linter_obj._run_vulture.assert_called_once()
            assert linter_obj._pkg_lint_status.get("vulture_errors") is None

    @pytest.mark.parametrize(argnames="no_flake8, no_xsoar_linter, no_bandit, no_mypy, no_vulture",
                             argvalues=[(True, True, True, True, False),
                                        (False, True, True, True, True),
                                        (True, True, True, False, True),
                                        (True, True, False, True, True),
                                        (True, False, True, True, True)])
    @pytest.mark.usefixtures("linter_obj", "mocker", "lint_files")
    def test_run_one_lint_check_fail(self, mocker, linter_obj, lint_files, no_flake8: bool, no_xsoar_linter: bool,
                                     no_bandit: bool, no_mypy: bool, no_vulture: bool):
        from demisto_sdk.commands.lint.linter import EXIT_CODES
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": False,
            "version_two": False,
            "lint_files": lint_files,
            "additional_requirements": []
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        linter_obj._run_flake8.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        linter_obj._run_xsoar_linter.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_bandit')
        linter_obj._run_bandit.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_mypy')
        linter_obj._run_mypy.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_vulture')
        linter_obj._run_vulture.return_value = (0b1, 'Error')
        linter_obj._run_lint_in_host(no_flake8=no_flake8,
                                     no_xsoar_linter=no_xsoar_linter,
                                     no_bandit=no_bandit,
                                     no_mypy=no_mypy,
                                     no_vulture=no_vulture)
        if not no_flake8:
            linter_obj._run_flake8.assert_called_once()
            assert linter_obj._pkg_lint_status.get("flake8_errors") == 'Error'
            assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['flake8']
        elif not no_xsoar_linter:
            linter_obj._run_xsoar_linter.assert_called_once()
            assert linter_obj._pkg_lint_status.get("XSOAR_linter_errors") == 'Error'
            assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['XSOAR_linter']
        elif not no_bandit:
            linter_obj._run_bandit.assert_called_once()
            assert linter_obj._pkg_lint_status.get("bandit_errors") == 'Error'
            assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['bandit']
        elif not no_mypy:
            linter_obj._run_mypy.assert_called_once()
            assert linter_obj._pkg_lint_status.get("mypy_errors") == 'Error'
            assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['mypy']
        elif not no_vulture:
            linter_obj._run_vulture.assert_called_once()
            assert linter_obj._pkg_lint_status.get("vulture_errors") == 'Error'
            assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['vulture']

    @pytest.mark.usefixtures("linter_obj", "mocker", "lint_files")
    def test_run_all_lint_fail_all(self, mocker, linter_obj, lint_files):
        from demisto_sdk.commands.lint.linter import EXIT_CODES
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": False,
            "version_two": False,
            "lint_files": lint_files,
            "additional_requirements": []
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        linter_obj._run_flake8.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        linter_obj._run_xsoar_linter.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_bandit')
        linter_obj._run_bandit.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_mypy')
        linter_obj._run_mypy.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_vulture')
        linter_obj._run_vulture.return_value = (0b1, 'Error')
        linter_obj._run_lint_in_host(no_flake8=False,
                                     no_bandit=False,
                                     no_xsoar_linter=False,
                                     no_mypy=False,
                                     no_vulture=False)
        linter_obj._run_flake8.assert_called_once()
        assert linter_obj._pkg_lint_status.get("flake8_errors") == 'Error'
        linter_obj._run_xsoar_linter.assert_called_once()
        assert linter_obj._pkg_lint_status.get("XSOAR_linter_errors") == 'Error'
        linter_obj._run_bandit.assert_called_once()
        assert linter_obj._pkg_lint_status.get("bandit_errors") == 'Error'
        linter_obj._run_mypy.assert_called_once()
        assert linter_obj._pkg_lint_status.get("mypy_errors") == 'Error'
        linter_obj._run_vulture.assert_called_once()
        assert linter_obj._pkg_lint_status.get("vulture_errors") == 'Error'
        assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['flake8'] + EXIT_CODES['bandit'] + \
            EXIT_CODES['mypy'] + EXIT_CODES['vulture'] + EXIT_CODES['XSOAR_linter']

    def test_no_lint_files(self, mocker, linter_obj):
        """No lint files exsits - not running any lint check"""
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": False,
            "version_two": False,
            "lint_files": [],
            "additional_requirements": []
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        mocker.patch.object(linter_obj, '_run_bandit')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        mocker.patch.object(linter_obj, '_run_mypy')
        mocker.patch.object(linter_obj, '_run_vulture')

        linter_obj._run_lint_in_host(no_flake8=False,
                                     no_bandit=False,
                                     no_xsoar_linter=False,
                                     no_mypy=False,
                                     no_vulture=False)

        linter_obj._run_flake8.assert_not_called()
        linter_obj._run_bandit.assert_not_called()
        linter_obj._run_xsoar_linter.assert_not_called()
        linter_obj._run_mypy.assert_not_called()
        linter_obj._run_vulture.assert_not_called()

    @pytest.mark.usefixtures("linter_obj", "mocker", "lint_files")
    def test_fail_lint_on_only_test_file(self, mocker, linter_obj, lint_files):
        """
        Given
        - Only one file was collected for linting.
        - The collected file is a unittest file.
        - All linters are enabled.

        When
        - Running the Linter class's _run_lint_in_host() method.

        Then
        - Only the flake8 linter should run
        - The flake8 linter is passed the unittest file
        """
        from demisto_sdk.commands.lint.linter import EXIT_CODES
        unittest_path = lint_files[0].parent / 'intergration_sample_test.py'
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", 3.7]],
            "test": False,
            "version_two": False,
            "lint_files": [],
            "lint_unittest_files": [unittest_path],
            "additional_requirements": [],
            "python_version": 3.7,
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        linter_obj._run_flake8.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        linter_obj._run_xsoar_linter.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_bandit')
        linter_obj._run_bandit.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_mypy')
        linter_obj._run_mypy.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_vulture')
        linter_obj._run_vulture.return_value = (0b1, 'Error')
        linter_obj._run_lint_in_host(no_flake8=False,
                                     no_bandit=False,
                                     no_xsoar_linter=False,
                                     no_mypy=False,
                                     no_vulture=False)
        linter_obj._run_flake8.assert_called_once()
        assert linter_obj._pkg_lint_status.get("flake8_errors") == 'Error'
        linter_obj._run_bandit.assert_not_called()
        linter_obj._run_mypy.assert_not_called()
        linter_obj._run_xsoar_linter.assert_not_called()
        linter_obj._run_vulture.assert_not_called()
        assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['flake8']

    @pytest.mark.usefixtures("linter_obj", "mocker", "lint_files")
    def test_fail_lint_on_normal_and_test_file(self, mocker, linter_obj, lint_files):
        """
        Given
        - Two files are collected for linting.
        - One is a normal python code file and the other is a unittest python file.
        - All linters are enabled.

        When
        - Running the Linter class's _run_lint_in_host() method.

        Then
        - The flake8 linter should run on the normal file and the unittest file
        - The other linters should only run on the normal file
        """
        from demisto_sdk.commands.lint.linter import EXIT_CODES
        unittest_path = lint_files[0].parent / 'intergration_sample_test.py'
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", 3.7]],
            "test": False,
            "version_two": False,
            "lint_files": lint_files,
            "lint_unittest_files": [unittest_path],
            "additional_requirements": [],
            "python_version": 3.7,
        })
        mocker.patch.object(linter_obj, '_run_flake8')
        linter_obj._run_flake8.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_xsoar_linter')
        linter_obj._run_xsoar_linter.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_bandit')
        linter_obj._run_bandit.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_mypy')
        linter_obj._run_mypy.return_value = (0b1, 'Error')
        mocker.patch.object(linter_obj, '_run_vulture')
        linter_obj._run_vulture.return_value = (0b1, 'Error')
        linter_obj._run_lint_in_host(no_flake8=False,
                                     no_bandit=False,
                                     no_mypy=False,
                                     no_xsoar_linter=False,
                                     no_vulture=False)
        linter_obj._run_flake8.assert_called_once()
        linter_obj._run_bandit.assert_called_once()
        linter_obj._run_xsoar_linter.assert_called_once()
        linter_obj._run_mypy.assert_called_once()
        linter_obj._run_vulture.assert_called_once()
        assert linter_obj._pkg_lint_status.get("exit_code") == EXIT_CODES['flake8'] + EXIT_CODES['bandit'] + \
            EXIT_CODES['mypy'] + EXIT_CODES['vulture'] + EXIT_CODES['XSOAR_linter']

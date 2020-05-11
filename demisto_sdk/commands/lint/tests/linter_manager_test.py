import os
from unittest.mock import MagicMock, patch

import pytest
from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.common.git_tools import git_path


@patch('builtins.print')
@pytest.mark.parametrize(argnames="return_exit_code, skipped_code, pkgs_type",
                         argvalues=[(0b0, 0b0, [TYPE_PWSH, TYPE_PYTHON])])
def test_report_pass_lint_checks(mocker, return_exit_code: int, skipped_code: int, pkgs_type: list):
    from demisto_sdk.commands.lint import lint_manager
    lint_manager.LintManager.report_pass_lint_checks(return_exit_code, skipped_code, pkgs_type)
    assert mocker.call_count == 8


def test_report_failed_image_creation():
    from demisto_sdk.commands.lint import lint_manager
    from demisto_sdk.commands.lint.helpers import EXIT_CODES
    pkgs_status = MagicMock()
    lint_status = {
        "fail_packs_image": ['pack']
    }
    pkgs_status.return_value = {
        'pack': {
            "images": [{"image": 'alpine', "image_errors": "some_errors"}]
        }
    }
    lint_manager.LintManager.report_failed_image_creation(lint_status=lint_status,
                                                          pkgs_status=pkgs_status,
                                                          return_exit_code=EXIT_CODES["image"])
    assert not pkgs_status.called


def test_create_failed_unit_tests_report_with_failed_tests():
    """
    Given`:
        - Lint manager dictionary with two failed packs -Infoblox and HelloWorld

    When:
        - Creating failed unit tests report

    Then:
        - Ensure report file is created.
        - Ensure report file contains exactly two packs.
        - Ensure both pack appear in the report.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {
        "fail_packs_flake8": [],
        "fail_packs_bandit": [],
        "fail_packs_mypy": ['Infoblox'],
        "fail_packs_vulture": [],
        "fail_packs_pylint": ['HelloWorld'],
        "fail_packs_pytest": ['Infoblox'],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
    }
    path = f'{git_path()}/demisto_sdk/commands/lint/tests'
    lint_manager.LintManager._create_failed_packs_report(lint_status, path)
    file_path = f'{path}/failed_lint_report.txt'
    assert os.path.isfile(file_path)
    with open(file_path, 'r') as file:
        content = file.read()
        fail_list = content.split('\n')
        assert len(fail_list) == 2
        assert 'HelloWorld' in fail_list
        assert 'Infoblox' in fail_list
    os.remove(file_path)


def test_create_failed_unit_tests_report_no_failed_tests():
    """
    Given:
        - Lint manager dictionary with no failed packs.

    When:
        - Creating failed unit tests report.

    Then:
        - Ensure report file is not created.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {
        "fail_packs_flake8": [],
        "fail_packs_bandit": [],
        "fail_packs_mypy": [],
        "fail_packs_vulture": [],
        "fail_packs_pylint": [],
        "fail_packs_pytest": [],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
    }
    path = f'{git_path()}/demisto_sdk/commands/lint/tests'
    lint_manager.LintManager._create_failed_packs_report(lint_status, path)
    file_path = f'{path}/failed_lint_report.txt'
    assert not os.path.isfile(file_path)

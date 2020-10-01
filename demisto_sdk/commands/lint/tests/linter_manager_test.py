import os
from pathlib import PosixPath
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
    assert mocker.call_count == 9


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
        "fail_xsoar_linter": [],
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
        "fail_xsoar_linter": [],
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


def test_report_warning_lint_checks_not_packages_tests(capsys):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating warnings lint check report.

    Then:
        - Ensure that the correct warnings printed to stdout.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {'fail_packs_flake8': ['Maltiverse'], 'fail_packs_XSOAR_linter': ['Maltiverse'],
                   'fail_packs_bandit': [], 'fail_packs_mypy': ['Maltiverse'], 'fail_packs_vulture': [],
                   'fail_packs_pylint': ['Maltiverse'], 'fail_packs_pytest': ['Maltiverse'],
                   'fail_packs_pwsh_analyze': [], 'fail_packs_pwsh_test': [], 'fail_packs_image': [],
                   'warning_packs_flake8': [], 'warning_packs_XSOAR_linter': ['Maltiverse'], 'warning_packs_bandit': [],
                   'warning_packs_mypy': [], 'warning_packs_vulture': [], 'warning_packs_pylint': [],
                   'warning_packs_pytest': [], 'warning_packs_pwsh_analyze': [], 'warning_packs_pwsh_test': [],
                   'warning_packs_image': []}
    pkgs_status = {
        'Maltiverse': {'pkg': 'Maltiverse', 'pack_type': 'python', 'path': '/Users/test_user/dev/demisto/content',
                       'errors': [], 'images': [{'image': 'demisto/python3:3.8.2.6981', 'image_errors': '',
                                                 'pylint_errors': "************* Module "
                                                                  "Maltiverse\nMaltiverse.py:521:0: E0602: Undefined "
                                                                  "variable 'z' (undefined-variable)\n",
                                                 'pytest_errors': "============================= test session starts "
                                                                  "==============================\nplatform linux -- "
                                                                  "Python 3.8.2, pytest-6.0.2, py-1.9.0, "
                                                                  "pluggy-0.13.1\nrootdir: /devwork\nplugins: "
                                                                  "forked-1.3.0, json-0.4.0, requests-mock-1.8.0, "
                                                                  "datadir-ng-1.1.1, xdist-2.1.0, mock-3.3.1, "
                                                                  "asyncio-0.14.0\ncollected 0 items / 1 "
                                                                  "error\n\n==================================== "
                                                                  "ERRORS "
                                                                  "====================================\n"
                                                                  "_____________________ ERROR collecting "
                                                                  "Maltiverse_test.py "
                                                                  "______________________\nMaltiverse_test.py:1: in "
                                                                  "<module>\n    from Maltiverse import Client, "
                                                                  "ip_command, url_command, domain_command, "
                                                                  "file_command\nMaltiverse.py:521: in <module>\n    "
                                                                  "z\nE   NameError: name 'z' is not "
                                                                  "defined\n-------------- generated json report: "
                                                                  "/devwork/report_pytest.json "
                                                                  "--------------\n=========================== short "
                                                                  "test summary info "
                                                                  "============================\nERROR "
                                                                  "Maltiverse_test.py - NameError: name 'z' is not "
                                                                  "defined\n!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error "
                                                                  "during collection "
                                                                  "!!!!!!!!!!!!!!!!!!!!\n"
                                                                  "=============================== 1 error in 0.16s "
                                                                  "===============================\n",
                                                 'pytest_json': {'report': {'environment': {}, 'tests': [],
                                                                            'summary': {'num_tests': 0,
                                                                                        'duration': 0.1635439395904541},
                                                                            'created_at': '2020-09-24 15:38:19.053978'}},
                                                 'pwsh_analyze_errors': '', 'pwsh_test_errors': ''}],
                       'flake8_errors': "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
                                        "/Maltiverse.py:508:1: E302 expected 2 blank lines, "
                                        "found "
                                        "1\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:511:1: E302 expected 2 blank lines, "
                                        "found "
                                        "1\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:516:5: F841 local variable 'client' is assigned to "
                                        "but never "
                                        "used\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:521:1: E305 expected 2 blank lines after class or "
                                        "function definition, found 1\n",
                       'XSOAR_linter_errors': 'Maltiverse.py:513:4: E9002: Print is found, Please remove all prints '
                                              'from the code. (print-exists)',
                       'bandit_errors': None,
                       'mypy_errors': "Maltiverse.py:521:1: error: Name 'z' is not defined  [name-defined]\n    z\n   "
                                      " ^\nFound 1 error in 1 file (checked 1 source file)\n",
                       'vulture_errors': None, 'flake8_warnings': None,
                       'XSOAR_linter_warnings': 'Maltiverse.py:511:0: W9010: try and except statements were not found '
                                                'in main function. Please add them ('
                                                'try-except-main-doesnt-exists)\nMaltiverse.py:511:0: W9012: '
                                                'return_error should be used in main function. Please add it. ('
                                                'return-error-does-not-exist-in-main)',
                       'bandit_warnings': None, 'mypy_warnings': None, 'vulture_warnings': None, 'exit_code': 565,
                       'warning_code': 512}}

    lint_manager.LintManager.report_warning_lint_checks(lint_status=lint_status, return_warning_code=512,
                                                        pkgs_status=pkgs_status, all_packs=False)
    captured = capsys.readouterr()
    assert "Maltiverse.py:511:0: W9010: try and except statements were not found in main function. Please add them (" \
           "try-except-main-doesnt-exists)" in captured.out
    assert "Maltiverse.py:511:0: W9012: return_error should be used in main function. Please add it. (" \
           "return-error-does-not-exist-in-main)" in captured.out
    assert "Xsoar_linter warnings" in captured.out


def test_report_warning_lint_checks_all_packages_tests(capsys):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating warnings lint check report.
        - All packages param is set to True - the same as running lint -a

    Then:
        - Ensure that there are no warnings printed to stdout.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {'fail_packs_flake8': ['Maltiverse'], 'fail_packs_XSOAR_linter': ['Maltiverse'],
                   'fail_packs_bandit': [], 'fail_packs_mypy': ['Maltiverse'], 'fail_packs_vulture': [],
                   'fail_packs_pylint': ['Maltiverse'], 'fail_packs_pytest': ['Maltiverse'],
                   'fail_packs_pwsh_analyze': [], 'fail_packs_pwsh_test': [], 'fail_packs_image': [],
                   'warning_packs_flake8': [], 'warning_packs_XSOAR_linter': ['Maltiverse'], 'warning_packs_bandit': [],
                   'warning_packs_mypy': [], 'warning_packs_vulture': [], 'warning_packs_pylint': [],
                   'warning_packs_pytest': [], 'warning_packs_pwsh_analyze': [], 'warning_packs_pwsh_test': [],
                   'warning_packs_image': []}
    pkgs_status = {
        'Maltiverse': {'pkg': 'Maltiverse', 'pack_type': 'python', 'path': '/Users/test_user/dev/demisto/content',
                       'errors': [], 'images': [{'image': 'demisto/python3:3.8.2.6981', 'image_errors': '',
                                                 'pylint_errors': "************* Module "
                                                                  "Maltiverse\nMaltiverse.py:521:0: E0602: Undefined "
                                                                  "variable 'z' (undefined-variable)\n",
                                                 'pytest_errors': "============================= test session starts "
                                                                  "==============================\nplatform linux -- "
                                                                  "Python 3.8.2, pytest-6.0.2, py-1.9.0, "
                                                                  "pluggy-0.13.1\nrootdir: /devwork\nplugins: "
                                                                  "forked-1.3.0, json-0.4.0, requests-mock-1.8.0, "
                                                                  "datadir-ng-1.1.1, xdist-2.1.0, mock-3.3.1, "
                                                                  "asyncio-0.14.0\ncollected 0 items / 1 "
                                                                  "error\n\n==================================== "
                                                                  "ERRORS "
                                                                  "====================================\n"
                                                                  "_____________________ ERROR collecting "
                                                                  "Maltiverse_test.py "
                                                                  "______________________\nMaltiverse_test.py:1: in "
                                                                  "<module>\n    from Maltiverse import Client, "
                                                                  "ip_command, url_command, domain_command, "
                                                                  "file_command\nMaltiverse.py:521: in <module>\n    "
                                                                  "z\nE   NameError: name 'z' is not "
                                                                  "defined\n-------------- generated json report: "
                                                                  "/devwork/report_pytest.json "
                                                                  "--------------\n=========================== short "
                                                                  "test summary info "
                                                                  "============================\nERROR "
                                                                  "Maltiverse_test.py - NameError: name 'z' is not "
                                                                  "defined\n!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error "
                                                                  "during collection "
                                                                  "!!!!!!!!!!!!!!!!!!!!\n"
                                                                  "=============================== 1 error in 0.16s "
                                                                  "===============================\n",
                                                 'pytest_json': {'report': {'environment': {}, 'tests': [],
                                                                            'summary': {'num_tests': 0,
                                                                                        'duration': 0.1635439395904541},
                                                                            'created_at': '2020-09-24 15:38:19.053978'}},
                                                 'pwsh_analyze_errors': '', 'pwsh_test_errors': ''}],
                       'flake8_errors': "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
                                        "/Maltiverse.py:508:1: E302 expected 2 blank lines, "
                                        "found "
                                        "1\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:511:1: E302 expected 2 blank lines, "
                                        "found "
                                        "1\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:516:5: F841 local variable 'client' is assigned to "
                                        "but never "
                                        "used\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
                                        "/Maltiverse/Maltiverse.py:521:1: E305 expected 2 blank lines after class or "
                                        "function definition, found 1\n",
                       'XSOAR_linter_errors': 'Maltiverse.py:513:4: E9002: Print is found, Please remove all prints '
                                              'from the code. (print-exists)',
                       'bandit_errors': None,
                       'mypy_errors': "Maltiverse.py:521:1: error: Name 'z' is not defined  [name-defined]\n    z\n   "
                                      " ^\nFound 1 error in 1 file (checked 1 source file)\n",
                       'vulture_errors': None, 'flake8_warnings': None,
                       'XSOAR_linter_warnings': 'Maltiverse.py:511:0: W9010: try and except statements were not found '
                                                'in main function. Please add them ('
                                                'try-except-main-doesnt-exists)\nMaltiverse.py:511:0: W9012: '
                                                'return_error should be used in main function. Please add it. ('
                                                'return-error-does-not-exist-in-main)',
                       'bandit_warnings': None, 'mypy_warnings': None, 'vulture_warnings': None, 'exit_code': 565,
                       'warning_code': 512}}

    lint_manager.LintManager.report_warning_lint_checks(lint_status=lint_status, return_warning_code=512,
                                                        pkgs_status=pkgs_status, all_packs=True)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_report_summary_with_warnings(capsys):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating summary of the lint.

    Then:
        - Ensure that there are warnings printed in the summary and failed packs.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {'fail_packs_flake8': ['Maltiverse'], 'fail_packs_XSOAR_linter': ['Maltiverse'],
                   'fail_packs_bandit': [], 'fail_packs_mypy': ['Maltiverse'], 'fail_packs_vulture': [],
                   'fail_packs_pylint': ['Maltiverse'], 'fail_packs_pytest': ['Maltiverse'],
                   'fail_packs_pwsh_analyze': [], 'fail_packs_pwsh_test': [], 'fail_packs_image': [],
                   'warning_packs_flake8': [], 'warning_packs_XSOAR_linter': ['Maltiverse'], 'warning_packs_bandit': [],
                   'warning_packs_mypy': [], 'warning_packs_vulture': [], 'warning_packs_pylint': [],
                   'warning_packs_pytest': [], 'warning_packs_pwsh_analyze': [], 'warning_packs_pwsh_test': [],
                   'warning_packs_image': []}
    pkg = [PosixPath('/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse')]
    lint_manager.LintManager.report_summary(pkg=pkg, lint_status=lint_status)
    captured = capsys.readouterr()
    assert "Packages PASS: \x1b[32m0\x1b[0m" in captured.out
    assert "Packages WARNING (can either PASS or FAIL): \x1b[33m1\x1b[0m" in captured.out
    assert "Packages FAIL: [31m1[0m" in captured.out


def test_report_summary_no_warnings(capsys):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating summary of the lint.

    Then:
        - Ensure that there are no warnings printed in the summary and all passed.
    """
    from demisto_sdk.commands.lint import lint_manager
    lint_status = {'fail_packs_flake8': [], 'fail_packs_XSOAR_linter': [],
                   'fail_packs_bandit': [], 'fail_packs_mypy': [], 'fail_packs_vulture': [],
                   'fail_packs_pylint': [], 'fail_packs_pytest': [],
                   'fail_packs_pwsh_analyze': [], 'fail_packs_pwsh_test': [], 'fail_packs_image': [],
                   'warning_packs_flake8': [], 'warning_packs_XSOAR_linter': [], 'warning_packs_bandit': [],
                   'warning_packs_mypy': [], 'warning_packs_vulture': [], 'warning_packs_pylint': [],
                   'warning_packs_pytest': [], 'warning_packs_pwsh_analyze': [], 'warning_packs_pwsh_test': [],
                   'warning_packs_image': []}
    pkg = [PosixPath('/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse')]
    lint_manager.LintManager.report_summary(pkg=pkg, lint_status=lint_status)
    captured = capsys.readouterr()
    assert "Packages PASS: \x1b[32m1\x1b[0m" in captured.out
    assert "Packages WARNING (can either PASS or FAIL): \x1b[33m0\x1b[0m" in captured.out
    assert "Packages FAIL: [31m0[0m" in captured.out

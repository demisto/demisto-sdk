from pathlib import Path, PosixPath
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    TYPE_PWSH,
    TYPE_PYTHON,
    FileType,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.lint.lint_manager import LintManager
from demisto_sdk.commands.lint.linter import DockerImageFlagOption
from TestSuite.test_tools import ChangeCWD


def mock_lint_manager(mocker):
    mocker.patch.object(LintManager, "_get_packages", return_value=[])
    mocker.patch.object(LintManager, "_gather_facts", return_value={"content_repo": ""})
    return LintManager(
        input="",
        git=False,
        all_packs=False,
        prev_ver=DEMISTO_GIT_PRIMARY_BRANCH,
        json_file_path="path",
    )


@pytest.mark.parametrize(
    argnames="return_exit_code, skipped_code, pkgs_type",
    argvalues=[(0b0, 0b0, [TYPE_PWSH, TYPE_PYTHON])],
)
def test_report_pass_lint_checks(
    mocker, return_exit_code: int, skipped_code: int, pkgs_type: list, caplog
):
    from demisto_sdk.commands.lint import lint_manager

    lint_manager.LintManager.report_pass_lint_checks(
        return_exit_code, skipped_code, pkgs_type
    )
    assert len(caplog.records) == 9


def test_report_failed_image_creation():
    from demisto_sdk.commands.lint import lint_manager
    from demisto_sdk.commands.lint.helpers import EXIT_CODES

    pkgs_status = MagicMock()
    lint_status = {"fail_packs_image": ["pack"]}
    pkgs_status.return_value = {
        "pack": {"images": [{"image": "alpine", "image_errors": "some_errors"}]}
    }
    lint_manager.LintManager.report_failed_image_creation(
        lint_status=lint_status,
        pkgs_status=pkgs_status,
        return_exit_code=EXIT_CODES["image"],
    )
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
        "fail_packs_mypy": ["Infoblox"],
        "fail_packs_vulture": [],
        "fail_packs_pylint": ["HelloWorld"],
        "fail_packs_pytest": ["Infoblox"],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
    }
    path = f"{git_path()}/demisto_sdk/commands/lint/tests"
    lint_manager.LintManager._create_failed_packs_report(lint_status, path)
    file_path = f"{path}/failed_lint_report.txt"
    assert Path(file_path).is_file()
    with open(file_path) as file:
        content = file.read()
        fail_list = content.split("\n")
        assert len(fail_list) == 2
        assert "HelloWorld" in fail_list
        assert "Infoblox" in fail_list
    Path(file_path).unlink()


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
    path = f"{git_path()}/demisto_sdk/commands/lint/tests"
    lint_manager.LintManager._create_failed_packs_report(lint_status, path)
    file_path = f"{path}/failed_lint_report.txt"
    assert not Path(file_path).is_file()


def test_report_warning_lint_checks_not_packages_tests(mocker, caplog):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating warnings lint check report.

    Then:
        - Ensure that the correct warnings printed to stdout.
    """

    lint_status = {
        "fail_packs_flake8": ["Maltiverse"],
        "fail_packs_XSOAR_linter": ["Maltiverse"],
        "fail_packs_bandit": [],
        "fail_packs_mypy": ["Maltiverse"],
        "fail_packs_vulture": [],
        "fail_packs_pylint": ["Maltiverse"],
        "fail_packs_pytest": ["Maltiverse"],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
        "warning_packs_flake8": [],
        "warning_packs_XSOAR_linter": ["Maltiverse"],
        "warning_packs_bandit": [],
        "warning_packs_mypy": [],
        "warning_packs_vulture": [],
        "warning_packs_pylint": [],
        "warning_packs_pytest": [],
        "warning_packs_pwsh_analyze": [],
        "warning_packs_pwsh_test": [],
        "warning_packs_image": [],
    }
    pkgs_status = {
        "Maltiverse": {
            "pkg": "Maltiverse",
            "pack_type": "python",
            "path": "/Users/test_user/dev/demisto/content",
            "errors": [],
            "images": [
                {
                    "image": "demisto/python3:3.8.2.6981",
                    "image_errors": "",
                    "pylint_errors": "************* Module "
                    "Maltiverse\nMaltiverse.py:521:0: E0602: Undefined "
                    "variable 'z' (undefined-variable)\n",
                    "pytest_errors": "============================= test session starts "
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
                    "pytest_json": {
                        "report": {
                            "environment": {},
                            "tests": [],
                            "summary": {"num_tests": 0, "duration": 0.1635439395904541},
                            "created_at": "2020-09-24 15:38:19.053978",
                        }
                    },
                    "pwsh_analyze_errors": "",
                    "pwsh_test_errors": "",
                }
            ],
            "flake8_errors": "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
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
            "XSOAR_linter_errors": "Maltiverse.py:513:4: E9002: Print is found, Please remove all prints "
            "from the code. (print-exists)",
            "bandit_errors": None,
            "mypy_errors": "Maltiverse.py:521:1: error: Name 'z' is not defined  [name-defined]\n    z\n   "
            " ^\nFound 1 error in 1 file (checked 1 source file)\n",
            "vulture_errors": None,
            "flake8_warnings": None,
            "XSOAR_linter_warnings": "Maltiverse.py:511:0: W9010: try and except statements were not found "
            "in main function. Please add them ("
            "try-except-main-doesnt-exists)\nMaltiverse.py:511:0: W9012: "
            "return_error should be used in main function. Please add it. ("
            "return-error-does-not-exist-in-main)",
            "bandit_warnings": None,
            "mypy_warnings": None,
            "vulture_warnings": None,
            "exit_code": 565,
            "warning_code": 512,
        }
    }

    mock_lint_manager(mocker).report_warning_lint_checks(
        lint_status=lint_status,
        return_warning_code=512,
        pkgs_status=pkgs_status,
        all_packs=False,
    )
    assert all(
        tuple(
            string in caplog.text
            for string in (
                "Maltiverse.py:511:0: W9010: try and except statements were not found in main function. Please add them (",
                "try-except-main-doesnt-exists)",
                "Maltiverse.py:511:0: W9012: return_error should be used in main function. Please add it. (",
                "return-error-does-not-exist-in-main)",
                "Xsoar_linter warnings",
            )
        )
    )


def test_report_warning_lint_checks_all_packages_tests(capsys, mocker):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating warnings lint check report.
        - All packages param is set to True - the same as running lint -a

    Then:
        - Ensure that there are no warnings printed to stdout.
    """
    lint_status = {
        "fail_packs_flake8": ["Maltiverse"],
        "fail_packs_XSOAR_linter": ["Maltiverse"],
        "fail_packs_bandit": [],
        "fail_packs_mypy": ["Maltiverse"],
        "fail_packs_vulture": [],
        "fail_packs_pylint": ["Maltiverse"],
        "fail_packs_pytest": ["Maltiverse"],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
        "warning_packs_flake8": [],
        "warning_packs_XSOAR_linter": ["Maltiverse"],
        "warning_packs_bandit": [],
        "warning_packs_mypy": [],
        "warning_packs_vulture": [],
        "warning_packs_pylint": [],
        "warning_packs_pytest": [],
        "warning_packs_pwsh_analyze": [],
        "warning_packs_pwsh_test": [],
        "warning_packs_image": [],
    }
    pkgs_status = {
        "Maltiverse": {
            "pkg": "Maltiverse",
            "pack_type": "python",
            "path": "/Users/test_user/dev/demisto/content",
            "errors": [],
            "images": [
                {
                    "image": "demisto/python3:3.8.2.6981",
                    "image_errors": "",
                    "pylint_errors": "************* Module "
                    "Maltiverse\nMaltiverse.py:521:0: E0602: Undefined "
                    "variable 'z' (undefined-variable)\n",
                    "pytest_errors": "============================= test session starts "
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
                    "pytest_json": {
                        "report": {
                            "environment": {},
                            "tests": [],
                            "summary": {"num_tests": 0, "duration": 0.1635439395904541},
                            "created_at": "2020-09-24 15:38:19.053978",
                        }
                    },
                    "pwsh_analyze_errors": "",
                    "pwsh_test_errors": "",
                }
            ],
            "flake8_errors": "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
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
            "XSOAR_linter_errors": "Maltiverse.py:513:4: E9002: Print is found, Please remove all prints "
            "from the code. (print-exists)",
            "bandit_errors": None,
            "mypy_errors": "Maltiverse.py:521:1: error: Name 'z' is not defined  [name-defined]\n    z\n   "
            " ^\nFound 1 error in 1 file (checked 1 source file)\n",
            "vulture_errors": None,
            "flake8_warnings": None,
            "XSOAR_linter_warnings": "Maltiverse.py:511:0: W9010: try and except statements were not found "
            "in main function. Please add them ("
            "try-except-main-doesnt-exists)\nMaltiverse.py:511:0: W9012: "
            "return_error should be used in main function. Please add it. ("
            "return-error-does-not-exist-in-main)",
            "bandit_warnings": None,
            "mypy_warnings": None,
            "vulture_warnings": None,
            "exit_code": 565,
            "warning_code": 512,
        }
    }

    mock_lint_manager(mocker).report_warning_lint_checks(
        lint_status=lint_status,
        return_warning_code=512,
        pkgs_status=pkgs_status,
        all_packs=True,
    )
    captured = capsys.readouterr()
    assert captured.out == ""


def test_report_summary_with_warnings(caplog):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating summary of the lint.

    Then:
        - Ensure that there are warnings printed in the summary and failed packs.
    """

    from demisto_sdk.commands.lint import lint_manager

    lint_status = {
        "fail_packs_flake8": ["Maltiverse"],
        "fail_packs_XSOAR_linter": ["Maltiverse"],
        "fail_packs_bandit": [],
        "fail_packs_mypy": ["Maltiverse"],
        "fail_packs_vulture": [],
        "fail_packs_pylint": ["Maltiverse"],
        "fail_packs_pytest": ["Maltiverse"],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
        "warning_packs_flake8": [],
        "warning_packs_XSOAR_linter": ["Maltiverse"],
        "warning_packs_bandit": [],
        "warning_packs_mypy": [],
        "warning_packs_vulture": [],
        "warning_packs_pylint": [],
        "warning_packs_pytest": [],
        "warning_packs_pwsh_analyze": [],
        "warning_packs_pwsh_test": [],
        "warning_packs_image": [],
    }
    pkg = [
        PosixPath(
            "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
        )
    ]
    pkgs_status = {"Maltiverse": {"exit_code": 1}}
    lint_manager.LintManager.report_summary(
        pkg=pkg, pkgs_status=pkgs_status, lint_status=lint_status
    )
    assert "Packages PASS: " in caplog.text
    assert "Packages WARNING (can either PASS or FAIL): " in caplog.text
    assert "Packages FAIL: " in caplog.text


def test_report_summary_no_warnings(caplog):
    """
    Given:
        - Lint manager dictionary with one pack which has warnings.

    When:
        - Creating summary of the lint.

    Then:
        - Ensure that there are no warnings printed in the summary and all passed.
    """

    from demisto_sdk.commands.lint import lint_manager

    lint_status = {
        "fail_packs_flake8": [],
        "fail_packs_XSOAR_linter": [],
        "fail_packs_bandit": [],
        "fail_packs_mypy": [],
        "fail_packs_vulture": [],
        "fail_packs_pylint": [],
        "fail_packs_pytest": [],
        "fail_packs_pwsh_analyze": [],
        "fail_packs_pwsh_test": [],
        "fail_packs_image": [],
        "warning_packs_flake8": [],
        "warning_packs_XSOAR_linter": [],
        "warning_packs_bandit": [],
        "warning_packs_mypy": [],
        "warning_packs_vulture": [],
        "warning_packs_pylint": [],
        "warning_packs_pytest": [],
        "warning_packs_pwsh_analyze": [],
        "warning_packs_pwsh_test": [],
        "warning_packs_image": [],
    }
    pkg = [
        PosixPath(
            "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse"
        )
    ]
    pkgs_status = {"Maltiverse": {"exit_code": 0}}
    lint_manager.LintManager.report_summary(
        pkg=pkg, lint_status=lint_status, pkgs_status=pkgs_status
    )
    assert all(
        [
            "Packages PASS: " in caplog.text,
            "Packages WARNING (can either PASS or FAIL): " in caplog.text,
            "Packages FAIL: " in caplog.text,
        ],
    )


def test_create_json_output_flake8(repo, mocker):
    """
    Given:
        - flake8 error entries.

    When:
        - Running flake8_error_formatter.

    Then:
        - Ensure that the JSON error entries are entered as expected.
    """
    mocked_lint_manager = mock_lint_manager(mocker)
    from demisto_sdk.commands.lint import lint_manager

    mocker.patch.object(lint_manager, "find_type", return_value=FileType.INTEGRATION)
    mocker.patch.object(lint_manager, "get_file_displayed_name", return_value="Display")
    check = {
        "linter": "flake8",
        "pack": "myPack",
        "type": "error",
        "messages": "Packs/myPack/Integrations/INT1/INT1.py:160:9: E225 missing whitespace around operator\n"
        "Packs/myPack/Integrations/INT2/INT2.py:160:9: E225 missing whitespace around operator",
    }
    json_contents = []
    mocked_lint_manager.flake8_error_formatter(check, json_contents)
    expected_format = [
        {
            "filePath": "Packs/myPack/Integrations/INT1/INT1.py",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "flake8",
            "severity": "error",
            "errorCode": "E225",
            "message": "missing whitespace around operator",
            "row": "160",
            "col": "9",
        },
        {
            "filePath": "Packs/myPack/Integrations/INT2/INT2.py",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "flake8",
            "severity": "error",
            "errorCode": "E225",
            "message": "missing whitespace around operator",
            "row": "160",
            "col": "9",
        },
    ]
    assert json_contents == expected_format


def test_create_json_output_mypy(repo, mocker):
    """
    Given:
        - mypy error entries.

    When:
        - Running mypy_error_formatter.

    Then:
        - Ensure that the JSON error entries are entered as expected.
    """
    mocked_lint_manager = mock_lint_manager(mocker)
    from demisto_sdk.commands.lint import lint_manager

    pack = repo.create_pack("Pack")
    integration = pack.create_integration(name="INT")
    integration.create_default_integration()
    mocker.patch.object(lint_manager, "find_type", return_value=FileType.INTEGRATION)
    mocker.patch.object(lint_manager, "get_file_displayed_name", return_value="Display")
    check = {
        "linter": "mypy",
        "pack": "myPack",
        "type": "error",
        "messages": f"{integration.code.path}:280:12: error:"
        'Item "None" of "Optional[datetime]" has no attribute "timestamp"  [union-attr]\n'
        f"            if incident_created_time.timestamp() > latest_created_time.tim...\n"
        f"               ^\n"
        f"{integration.code.path}:11:2: note: "
        f"See https://mypy.readthedocs.io/en/latest/running_mypy.html#missing-imports\n"
        f"{integration.code.path}:284:37: error:\n"
        f'Item "None" of "Optional[datetime]" has no attribute "timestamp"  [union-attr]\n'
        f"            if last_fetch.timestamp() < incident_created_time.timestamp():\n"
        f"                                        ^\n"
        f"Found 6 errors in 1 file (checked 1 source file)",
    }
    json_contents = []
    with ChangeCWD(repo.path):
        mocked_lint_manager.mypy_error_formatter(check, json_contents)

    expected_format = [
        {
            "filePath": f"{integration.code.path}",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "mypy",
            "severity": "error",
            "message": 'Item "None" of "Optional[datetime]" has no attribute "timestamp"  [union-attr]\n'
            "            if incident_created_time.timestamp() > latest_created_time.tim...\n"
            "               ^",
            "row": "280",
            "col": "12",
        },
        {
            "filePath": f"{integration.code.path}",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "mypy",
            "severity": "error",
            "message": "See https://mypy.readthedocs.io/en/latest/running_mypy.html#missing-imports",
            "row": "11",
            "col": "2",
        },
        {
            "filePath": f"{integration.code.path}",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "mypy",
            "severity": "error",
            "message": 'Item "None" of "Optional[datetime]" has no attribute "timestamp"  [union-attr]\n'
            "            if last_fetch.timestamp() < incident_created_time.timestamp():\n"
            "                                        ^",
            "row": "284",
            "col": "37",
        },
    ]
    assert json_contents == expected_format


def test_create_json_output_bandit(repo, mocker):
    """
    Given:
        - bandit error entries.

    When:
        - Running bandit_error_formatter.

    Then:
        - Ensure that the JSON error entries are entered as expected.
    """
    mocked_lint_manager = mock_lint_manager(mocker)
    from demisto_sdk.commands.lint import lint_manager

    mocker.patch.object(lint_manager, "find_type", return_value=FileType.INTEGRATION)
    mocker.patch.object(lint_manager, "get_file_displayed_name", return_value="Display")
    check = {
        "linter": "flake8",
        "pack": "myPack",
        "type": "error",
        "messages": "Packs/myPack/Integrations/INT1/INT1.py:117: "
        "B110 [Severity: LOW Confidence: HIGH] Try, Except, Pass detected.",
    }
    json_contents = []
    mocked_lint_manager.bandit_error_formatter(check, json_contents)
    expected_format = [
        {
            "filePath": "Packs/myPack/Integrations/INT1/INT1.py",
            "fileType": "py",
            "errorType": "Code",
            "name": "Display",
            "entityType": "integration",
            "linter": "bandit",
            "severity": "error",
            "errorCode": "B110",
            "message": "Severity: LOW Confidence: HIGH - Try, Except, Pass detected.",
            "row": "117",
        }
    ]
    assert json_contents == expected_format


def test_create_json_output_vulture(repo, mocker):
    """
    Given:
        - vulture error entries.

    When:
        - Running vulture_error_formatter.

    Then:
        - Ensure that the JSON error entries are entered as expected.
    """
    mocked_lint_manager = mock_lint_manager(mocker)
    from demisto_sdk.commands.lint import lint_manager

    mocker.patch.object(lint_manager, "find_type", return_value=FileType.INTEGRATION)
    mocker.patch.object(
        lint_manager, "find_file", return_value="Packs/myPack/Integrations/INT1/INT1.py"
    )
    mocker.patch.object(lint_manager, "get_file_displayed_name", return_value="Display")
    check = {
        "linter": "vulture",
        "pack": "myPack",
        "type": "error",
        "messages": "INT1.py:289: unreachable code after 'return' (100% confidence)",
    }
    json_contents = []
    mocked_lint_manager.vulture_error_formatter(check, json_contents)
    expected_format = [
        {
            "filePath": "Packs/myPack/Integrations/INT1/INT1.py",
            "fileType": "py",
            "errorType": "Code",
            "name": "Display",
            "entityType": "integration",
            "linter": "vulture",
            "severity": "error",
            "message": "unreachable code after 'return' (100% confidence)",
            "row": "289",
        }
    ]
    assert json_contents == expected_format


def test_create_json_output_xsoar_linter(repo, mocker):
    """
    Given:
        - XSOAR linter error entries.

    When:
        - Running xsoar_linter_error_formatter.

    Then:
        - Ensure that the JSON error entries are entered as expected.
    """
    mocked_lint_manager = mock_lint_manager(mocker)
    from demisto_sdk.commands.lint import lint_manager

    mocker.patch.object(lint_manager, "find_type", return_value=FileType.INTEGRATION)
    mocker.patch.object(lint_manager, "get_file_displayed_name", return_value="Display")
    check = {
        "linter": "xsoar_linter",
        "pack": "myPack",
        "type": "error",
        "messages": "Packs/myPack/Integrations/INT1/INT1.py:105:8: "
        "E9001 FileShareLink.prepare_request_object: Sys.exit use is found, Please use return instead.",
    }
    json_contents = []
    mocked_lint_manager.xsoar_linter_error_formatter(check, json_contents)
    expected_format = [
        {
            "filePath": "Packs/myPack/Integrations/INT1/INT1.py",
            "fileType": "py",
            "entityType": "integration",
            "errorType": "Code",
            "name": "Display",
            "linter": "xsoar_linter",
            "severity": "error",
            "errorCode": "E9001",
            "message": "FileShareLink.prepare_request_object: Sys.exit use is found, Please use return instead.",
            "row": "105",
            "col": "8",
        }
    ]
    assert json_contents == expected_format


class NodeDependencyMock:
    def __init__(self, path):
        self.path = path


class NodeMock:
    def __init__(self, imported_by):
        self.imported_by = imported_by


@pytest.mark.parametrize(
    "changed_files, api_module_nodes, dependent_items, packages_of_dependent_items, cdam_flag",
    [
        pytest.param(
            [PosixPath("Packs/ApiModules/Scripts/SomeApiModule")],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack/Scripts/SomeScript/SomeScript.py"
                            )
                        ]
                    )
                ]
            ],
            ["Packs/SomePack/Scripts/SomeScript/SomeScript.py"],
            [PosixPath("Packs/SomePack/Scripts/SomeScript")],
            True,
            id="single api module change with dependency",
        ),
        pytest.param(
            [PosixPath("Packs/ApiModules/Scripts/SomeApiModule")],
            [[NodeMock(imported_by=[])]],
            [],
            [],
            True,
            id="single api module change with no dependencies",
        ),
        pytest.param(
            [PosixPath("Packs/SomePack/Scripts/SomePackScript")],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomeOtherPack/Scripts/SomeScript/SomeScript.py"
                            )
                        ]
                    )
                ]
            ],
            [],
            [],
            True,
            id="non api module change with dependency",
        ),
        pytest.param(
            [PosixPath("Packs/ApiModules/Scripts/SomeApiModule")],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack1/Scripts/SomeScript1/SomeScript1.py"
                            ),
                            NodeDependencyMock(
                                path="Packs/SomePack2/Scripts/SomeScript2/SomeScript2.py"
                            ),
                        ]
                    )
                ]
            ],
            [
                "Packs/SomePack1/Scripts/SomeScript1/SomeScript1.py",
                "Packs/SomePack2/Scripts/SomeScript2/SomeScript2.py",
            ],
            [
                PosixPath("Packs/SomePack1/Scripts/SomeScript1"),
                PosixPath("Packs/SomePack2/Scripts/SomeScript2"),
            ],
            True,
            id="single api module change with 2 dependencies",
        ),
        pytest.param(
            [
                PosixPath("Packs/ApiModules/Scripts/SomeApiModule1"),
                PosixPath("Packs/ApiModules/Scripts/SomeApiModule2"),
            ],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack1/Scripts/SomeScript1/SomeScript1.py"
                            )
                        ]
                    )
                ],
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack2/Scripts/SomeScript2/SomeScript2.py"
                            )
                        ]
                    )
                ],
            ],
            [
                "Packs/SomePack1/Scripts/SomeScript1/SomeScript1.py",
                "Packs/SomePack2/Scripts/SomeScript2/SomeScript2.py",
            ],
            [
                PosixPath("Packs/SomePack1/Scripts/SomeScript1"),
                PosixPath("Packs/SomePack2/Scripts/SomeScript2"),
            ],
            True,
            id="2 api module changes with 1 dependency each",
        ),
        pytest.param(
            [PosixPath("Packs/ApiModules/Scripts/SomeApiModule")],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack/Scripts/SomeScript/SomeScript.py"
                            )
                        ]
                    )
                ]
            ],
            [],
            [],
            False,
            id="single api module change with dependency, no cdam flag",
        ),
        pytest.param(
            [
                PosixPath("Packs/ApiModules/Scripts/SomeApiModule"),
                PosixPath("Packs/SomePack/Scripts/SomeScript"),
            ],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack/Scripts/SomeScript/SomeScript.py"
                            )
                        ]
                    )
                ],
                [None],
            ],
            ["Packs/SomePack/Scripts/SomeScript/SomeScript.py"],
            [PosixPath("Packs/SomePack/Scripts/SomeScript")],
            True,
            id="single api module change with dependency also changed",
        ),
    ],
)
def test_get_api_module_dependent_items(
    mocker,
    changed_files,
    api_module_nodes,
    dependent_items,
    packages_of_dependent_items,
    cdam_flag,
):
    """
    Given:
        - Changed API modules with various dependencies.

    When:
        - Running lint on API modules

    Then:
        - Ensure that lint runs on all relevant dependencies as well.
    """
    get_packages_mock = mocker.patch.object(
        LintManager,
        "_get_packages",
        side_effect=[changed_files, packages_of_dependent_items],
    )
    mocker.patch.object(LintManager, "_gather_facts", return_value={"content_repo": ""})

    mocker.patch.object(ContentGraphInterface, "__init__", return_value=None)
    mocker.patch.object(
        ContentGraphInterface, "__enter__", return_value=ContentGraphInterface
    )
    mocker.patch.object(ContentGraphInterface, "__exit__", return_value=None)
    mocker.patch("demisto_sdk.commands.lint.lint_manager.update_content_graph")
    mocker.patch.object(ContentGraphInterface, "search", side_effect=api_module_nodes)
    lint_manager = LintManager(
        input="",
        git=False,
        all_packs=False,
        prev_ver=DEMISTO_GIT_PRIMARY_BRANCH,
        json_file_path="path",
        check_dependent_api_module=cdam_flag,
    )

    # Asserts sets are equal
    assert set(lint_manager._pkgs) == set(packages_of_dependent_items + changed_files)
    # Assert no duplicates
    assert len(lint_manager._pkgs) == len(
        set(packages_of_dependent_items + changed_files)
    )
    if packages_of_dependent_items:
        get_packages_mock.assert_called_with(content_repo="", input=dependent_items)


@pytest.mark.parametrize(
    "changed_files, api_module_nodes, dependent_items, packages_of_dependent_items_returned, "
    "packages_of_dependent_items, cdam_flag",
    [
        pytest.param(
            [
                PosixPath("Packs/ApiModules/Scripts/SomeApiModule"),
                PosixPath("Packs/SomePack/Scripts/SomeScript"),
            ],
            [
                [
                    NodeMock(
                        imported_by=[
                            NodeDependencyMock(
                                path="Packs/SomePack/Scripts/SomeScript/SomeScript.py"
                            )
                        ]
                    )
                ],
                [None],
            ],
            ["Packs/SomePack/Scripts/SomeScript/SomeScript.py"],
            ["Packs/SomePack/Scripts/SomeScript/SomeScript.py"],
            [PosixPath("Packs/SomePack/Scripts/SomeScript")],
            True,
            id="single api module change with dependency also changed",
        ),
    ],
)
def test_get_api_module_dependent_items_which_were_changed(
    mocker,
    changed_files,
    api_module_nodes,
    dependent_items,
    packages_of_dependent_items_returned,
    packages_of_dependent_items,
    cdam_flag,
):
    """
    Given:
        - Changed API modules with changed dependencies and dependencies.
        - get_pack_path returning file path instead of pack path.

    When:
        - Running lint on API modules and changed dependencies.

    Then:
        - Ensure that lint runs on all relevant dependencies and collects them once.
    """
    get_packages_mock = mocker.patch.object(
        LintManager,
        "_get_packages",
        side_effect=[changed_files, packages_of_dependent_items_returned],
    )
    mocker.patch.object(LintManager, "_gather_facts", return_value={"content_repo": ""})

    mocker.patch.object(ContentGraphInterface, "__init__", return_value=None)
    mocker.patch.object(
        ContentGraphInterface, "__enter__", return_value=ContentGraphInterface
    )
    mocker.patch.object(ContentGraphInterface, "__exit__", return_value=None)
    mocker.patch("demisto_sdk.commands.lint.lint_manager.update_content_graph")
    mocker.patch.object(ContentGraphInterface, "search", side_effect=api_module_nodes)
    lint_manager = LintManager(
        input="",
        git=False,
        all_packs=False,
        prev_ver=DEMISTO_GIT_PRIMARY_BRANCH,
        json_file_path="path",
        check_dependent_api_module=cdam_flag,
    )

    # Asserts sets are equal
    assert set(lint_manager._pkgs) == set(packages_of_dependent_items + changed_files)
    # Assert no duplicates
    assert len(lint_manager._pkgs) == len(
        set(packages_of_dependent_items + changed_files)
    )
    if packages_of_dependent_items:
        get_packages_mock.assert_called_with(content_repo="", input=dependent_items)


@pytest.mark.parametrize(
    "docker_image_flag",
    [
        DockerImageFlagOption.FROM_YML.value,
        DockerImageFlagOption.ALL_IMAGES.value,
        DockerImageFlagOption.NATIVE_DEV.value,
        DockerImageFlagOption.NATIVE.value,
        DockerImageFlagOption.NATIVE_GA.value,
        DockerImageFlagOption.NATIVE_MAINTENANCE.value,
    ],
)
def test_invalid_docker_image_target_flag(mocker, docker_image_flag):
    """
    Given:
        - docker_image_target but docker_image_flag is not native:target

    When:
        - Running lint with docker_image_target and the invalid docker_image_flag.

    Then:
        - Ensure the right error is raised.
    """
    mocked_lint_manager = mock_lint_manager(mocker)

    with pytest.raises(ValueError) as err_info:
        mocked_lint_manager.run(
            parallel=False,
            no_flake8=True,
            no_bandit=True,
            no_mypy=True,
            no_vulture=True,
            no_xsoar_linter=True,
            no_pylint=True,
            no_test=True,
            no_pwsh_test=True,
            no_pwsh_analyze=True,
            no_coverage=True,
            keep_container=False,
            test_xml="",
            failure_report="",
            coverage_report="",
            docker_timeout=60,
            docker_image_flag=docker_image_flag,
            docker_image_target="some_docker_image",
        )

    expected_err_str = (
        "Recieved docker image target some_docker_image without docker image flag native:target. "
        "Aborting."
    )

    assert expected_err_str in err_info.value.args[0]

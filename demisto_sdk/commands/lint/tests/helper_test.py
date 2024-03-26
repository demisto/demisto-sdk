import importlib
import os
from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import TYPE_PYTHON
from demisto_sdk.commands.lint.helpers import (
    add_tmp_lint_files,
    generate_coverage_report,
    split_warnings_errors,
)

EXIT_CODES = {
    "flake8": 0b1,
    "xsoar_linter": 0b1000000000,
    "bandit": 0b10,
    "mypy": 0b100,
    "vulture": 0b1000,
    "pytest": 0b10000,
    "pylint": 0b100000,
    "pwsh_analyze": 0b1000000,
    "pwsh_test": 0b10000000,
    "image": 0b100000000,
}


@pytest.mark.parametrize(
    argnames="no_flake8, no_xsoar_linter, no_bandit, no_mypy, no_pylint, no_vulture, no_test, no_pwsh_analyze, "
    "no_pwsh_test, docker_engine, expected_value",
    argvalues=[
        (True, False, True, True, True, True, True, True, True, True, 0b11111111),
        (True, False, False, True, True, True, True, True, True, True, 0b11111101),
        (True, False, False, True, True, True, True, False, True, True, 0b10111101),
    ],
)
def test_build_skipped_exit_code(
    no_flake8: bool,
    no_xsoar_linter: bool,
    no_bandit: bool,
    no_mypy: bool,
    no_pylint: bool,
    no_vulture: bool,
    no_test: bool,
    no_pwsh_analyze: bool,
    no_pwsh_test: bool,
    docker_engine: bool,
    expected_value: int,
):
    from demisto_sdk.commands.lint.helpers import build_skipped_exit_code

    env_var = os.environ.get("CI")
    # On you local env
    if not env_var:
        assert expected_value == build_skipped_exit_code(
            no_flake8,
            no_bandit,
            no_mypy,
            no_pylint,
            no_vulture,
            no_xsoar_linter,
            no_test,
            no_pwsh_analyze,
            no_pwsh_test,
            docker_engine,
        )
    # On circle runs
    else:
        assert 0 == build_skipped_exit_code(
            no_flake8,
            no_bandit,
            no_mypy,
            no_pylint,
            no_vulture,
            no_xsoar_linter,
            no_test,
            no_pwsh_analyze,
            no_pwsh_test,
            docker_engine,
        )


@pytest.mark.parametrize(
    argnames="archive_response, expected_count, expected_exception",
    argvalues=[
        ([False, True], 2, False),
        ([True], 1, False),
        ([False, False], 2, True),
    ],
)
def test_copy_dir_to_container(
    mocker, archive_response: bool, expected_count: int, expected_exception: bool
):
    from demisto_sdk.commands.lint import helpers

    mocker.patch.object(helpers, "docker")
    mocker.patch.object(helpers, "tarfile")
    mocker.patch.object(helpers, "os")
    mock_container = mocker.MagicMock()
    mock_container_path = mocker.MagicMock()
    mock_host_path = mocker.MagicMock()
    mock_container.put_archive.side_effect = archive_response
    if expected_exception:
        with pytest.raises(Exception):
            helpers.copy_dir_to_container(
                mock_container, mock_container_path, mock_host_path
            )
    else:
        helpers.copy_dir_to_container(
            mock_container, mock_container_path, mock_host_path
        )

    assert mock_container.put_archive.call_count == expected_count


MSG = [
    (
        "flake8",
        "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse/Maltiverse.py:6:1: F401 "
        "'typing.Tuple' imported but unused\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations"
        "/Maltiverse/Maltiverse.py:6:1: F401 'typing.Dict' imported but "
        "unused\n/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse/Maltiverse.py:6:1: F401 "
        "'typing.Any' imported but unused",
        [],
        [],
        [
            "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse/Maltiverse.py:6:1: F401 "
            "'typing.Tuple' imported but unused",
            "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse/Maltiverse.py:6:1: F401 "
            "'typing.Dict' imported but unused",
            "/Users/test_user/dev/demisto/content/Packs/Maltiverse/Integrations/Maltiverse/Maltiverse.py:6:1: F401 "
            "'typing.Any' imported but unused",
        ],
    ),
    (
        "xsoar_linter",
        "************* Module Maltiverse\nMaltiverse.py:509:0: W9010: try and except statements were not found in "
        "main function. Please add them (try-except-main-doesnt-exists)\nMaltiverse.py:509:0: W9012: return_error "
        "should be used in main function. Please add it. (return-error-does-not-exist-in-main)\nMaltiverse.py:511:4: "
        "E9002: Print is found, Please remove all prints from the code. (print-exists)",
        [
            "Maltiverse.py:511:4: E9002: Print is found, Please remove all prints from the code. (print-exists)"
        ],
        [
            "Maltiverse.py:509:0: W9010: try and except statements were not found in main function. Please add them ("
            "try-except-main-doesnt-exists)",
            "Maltiverse.py:509:0: W9012: return_error should be used in main function. Please add it. ("
            "return-error-does-not-exist-in-main)",
        ],
        ["************* Module Maltiverse"],
    ),
    (
        "xsoar_linter",
        "************* Module VirusTotal-Private_API\nW: 20,10: Initialize of params was found outside of main"
        " function. Please use demisto.params() only inside mainfunc (init-params-outside-main)",
        [],
        [
            "W: 20,10: Initialize of params was found outside of main function. Please use demisto.params()"
            " only inside mainfunc (init-params-outside-main)"
        ],
        ["************* Module VirusTotal-Private_API"],
    ),
    (
        "mypy",
        "Maltiverse.py:31:12: error: Incompatible return value type (got\nDict[Any, Any]', expected 'str')["
        "return-value]     \nreturn params^\n    Found 1 error in 1 file (checked 1 source file)",
        [],
        [],
        [
            "Maltiverse.py:31:12: error: Incompatible return value type (got",
            "Dict[Any, Any]', expected 'str')[return-value]     ",
            "return params^",
            "    Found 1 error in 1 file (checked 1 source file)",
        ],
    ),
    (
        "mypy",
        "Ebox.py:31:12: error: Incompatible return value type (got\nDict[Any, Any]', expected 'str')["
        "return-value]     \nreturn params^\n    Found 1 error in 1 file (checked 1 source file)",
        [],
        [],
        [
            "Ebox.py:31:12: error: Incompatible return value type (got",
            "Dict[Any, Any]', expected 'str')[return-value]     ",
            "return params^",
            "    Found 1 error in 1 file (checked 1 source file)",
        ],
    ),
]


@pytest.mark.parametrize(
    "linter_name, input_msg, output_error, output_warning, output_other", MSG
)
def test_split_warnings_errors(
    linter_name, input_msg, output_error, output_warning, output_other
):
    """
    Given:
        - linter name releated to input_msg which was returned from this specific linter.

    When:
        - Running split_warnings_errors on the given inupt.

    Then:
        - Ensure that the error, warning, other return values equal to expected.
    """
    error, warning, other = split_warnings_errors(input_msg)
    assert error == output_error
    assert warning == output_warning
    assert other == output_other


def test_add_tmp_lint_files(repo):
    """
    Given:
        - A pack that contains two modules and an integration that imports those two modules.

    When:
        - Running add_tmp_lint_files on the given input.

    Then:
        - Ensure both modules are copied by the command shutil.copy.
    """
    pack = repo.create_pack(name="ApiModules")
    pack.create_script(name="TEST1ApiModule", code="# TEST1ApiModule")
    pack.create_script(name="TEST2ApiModule", code="# TEST2ApiModule")
    integration_code = "from TEST1ApiModule import *\nfrom TEST2ApiModule import *"
    integration = pack.create_integration(name="test", code=integration_code)

    content_repo = Path(repo.path)
    pack_path = Path(pack.path)
    lint_files = [Path(integration.code.path)]

    with add_tmp_lint_files(
        content_repo=content_repo,
        pack_path=pack_path,
        lint_files=lint_files,
        modules={},
        pack_type=TYPE_PYTHON,
    ):
        assert all(
            (pack_path / module).exists()
            for module in ["TEST1ApiModule.py", "TEST2ApiModule.py"]
        )


def test_add_tmp_lint_files__multi_level_api_modules(repo):
    """
    Given:
        - A pack that contains an integration that imports multi level ApiModules.

    When:
        - Running add_tmp_lint_files on the given input.

    Then:
        - Ensure entire hierarchy of the ApiModules are copied.
    """
    pack = repo.create_pack(name="ApiModules")
    pack.create_script(name="BaseApiModule", code="# base ApiModule")
    pack.create_script(name="SubApiModule", code="from BaseApiModule import *")
    pack.create_script(name="SubSubApiModule", code="from SubApiModule import *")
    integration_code = "from SubSubApiModule import *"
    integration = pack.create_integration(name="test", code=integration_code)

    content_repo = Path(repo.path)
    pack_path = Path(pack.path)
    lint_files = [Path(integration.code.path)]

    with add_tmp_lint_files(
        content_repo=content_repo,
        pack_path=pack_path,
        lint_files=lint_files,
        modules={},
        pack_type=TYPE_PYTHON,
    ):
        assert all(
            (pack_path / module).exists()
            for module in ["BaseApiModule.py", "SubApiModule.py", "SubSubApiModule.py"]
        )


class TestGenerateCoverageReport:
    coverage = importlib.import_module("coverage")

    @staticmethod
    def mock_path_exists(mocker):
        mocker.patch("pathlib.Path.exists", return_value=True)

    def test_generate_coverage_report_with_report(self, mocker):
        mock_report = mocker.patch.object(self.coverage.Coverage, "report")
        self.mock_path_exists(mocker)
        generate_coverage_report()
        mock_report.assert_called_once()

    def test_generate_coverage_report_with_html(self, mocker):
        mock_html_report = mocker.patch.object(self.coverage.Coverage, "html_report")
        self.mock_path_exists(mocker)
        generate_coverage_report(report=False, html=True)
        mock_html_report.assert_called_once_with(directory="coverage_report/html")

    def test_generate_coverage_report_with_xml(self, mocker):
        mock_xml_report = mocker.patch.object(self.coverage.Coverage, "xml_report")
        self.mock_path_exists(mocker)
        generate_coverage_report(report=False, xml=True)
        mock_xml_report.assert_called_once_with(outfile="coverage_report/coverage.xml")

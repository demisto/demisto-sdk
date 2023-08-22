import logging
import os
from os.path import join
from typing import Optional

import pytest

from demisto_sdk.commands.common.constants import PACK_METADATA_SUPPORT
from demisto_sdk.commands.common.errors import (
    FOUND_FILES_AND_ERRORS,
    FOUND_FILES_AND_IGNORED_ERRORS,
    PRESET_ERROR_TO_CHECK,
    PRESET_ERROR_TO_IGNORE,
    Errors,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from TestSuite.pack import Pack
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST = (
    BaseValidator.create_reverse_ignored_errors_list(
        PRESET_ERROR_TO_CHECK["deprecated"]
    )
)


@pytest.mark.parametrize(
    "ignored_errors, error_code",
    [
        ({"file_name": ["SC109"]}, "SC109"),  # SC109 can not be ignored
        (
            {"file_name": ["PA116", "PA117"]},
            "PA117",  # PA116 can be ignored, PA117 can not be ignored
        ),
        (
            {"file_name": ["PB109", "PB104"]},
            "PB109",  # PB104 can be ignored, PB109 can not be ignored
        ),
        ({"file_name": ["RM"]}, "RM109"),  # RM109 can not be ignored
        ({"file_name": ["RM"]}, "RM105"),  # RM106 can not be ignored
        ({"file_name": ["RM", "SC"]}, "SC102"),  # SC102 can not be ignored
    ],
)
def test_handle_error_on_unignorable_error_codes(
    mocker, monkeypatch, ignored_errors, error_code
):
    """
    Given
    - error code which is not allowed to be ignored.
    - error codes/prefix error codes as the ignored errors from the pack-ignore file.

    When
    - Running handle_error method

    Then
    - Ensure that the correct error message is returned
    - Ensure that the correct error message is printed out.
    - Ensure that the un-ignorable errors are in FOUND_FILES_AND_ERRORS list.
    - Ensure that the un-ignorable errors are not in FOUND_FILES_AND_IGNORED_ERRORS list.
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    monkeypatch.setenv("COLUMNS", "1000")

    base_validator = BaseValidator(ignored_errors=ignored_errors)
    expected_error = f"file_name: [{error_code}] can not be ignored in .pack-ignore\n"

    result = base_validator.handle_error(
        error_message="",
        error_code=error_code,
        file_path="file_name",
        suggested_fix="fix",
    )
    assert expected_error in result
    assert str_in_call_args_list(logger_error.call_args_list, expected_error)
    assert f"file_name - [{error_code}]" in FOUND_FILES_AND_ERRORS
    assert f"file_name - [{error_code}]" not in FOUND_FILES_AND_IGNORED_ERRORS


@pytest.mark.parametrize(
    "is_github_actions, suggested_fix, is_warning, expected_result",
    [
        (
            True,
            "fix",
            False,
            "::error file=PATH,line=1,endLine=1,title=Validation Error SC102::Error-message%0Afix\n",
        ),
        (
            True,
            None,
            False,
            "::error file=PATH,line=1,endLine=1,title=Validation Error SC102::Error-message\n",
        ),
        (True, None, True, ""),
        (False, "fix", False, ""),
        (False, None, False, ""),
    ],
)
def test_handle_error_github_annotation(
    monkeypatch,
    capsys,
    is_github_actions: bool,
    suggested_fix: Optional[str],
    is_warning: bool,
    expected_result: str,
):
    """
    Given
    - is_github_actions - True to mock running in CI
    - suggested_fix - a suggestion for fixing the error
    - warning
    - expected_result

    When
    - executing handle_error function

    Then
    - Ensure the message was printed if needed, and not if not
    - Ensure the message includes the suggested_fix if exists
    """
    monkeypatch.setenv("GITHUB_ACTIONS", is_github_actions)
    base_validator = BaseValidator()
    base_validator.handle_error(
        error_message="Error-message",
        error_code="SC102",
        file_path="PATH",
        suggested_fix=suggested_fix,
        warning=is_warning,
    )
    captured = capsys.readouterr()
    assert captured.out == expected_result


def test_handle_error(mocker, caplog):
    """
    Given
    - An ignore errors list associated with a file.
    - An error, message, code and file paths.

    When
    - Running handle_error method.

    Then
    - Ensure the resulting error messages are correctly formatted.
    - Ensure ignored error codes return None.
    - Ensure non ignored errors are in FOUND_FILES_AND_ERRORS list.
    - Ensure ignored error are not in FOUND_FILES_AND_ERRORS and in FOUND_FILES_AND_IGNORED_ERRORS
    """
    base_validator = BaseValidator(
        ignored_errors={"file_name": ["BA101"]}, print_as_warnings=True
    )

    # passing the flag checks - checked separately
    base_validator.checked_files.union({"PATH", "file_name"})

    formatted_error = base_validator.handle_error("Error-message", "SC102", "PATH")
    assert formatted_error == "PATH: [SC102] - Error-message\n"
    assert "PATH - [SC102]" in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error(
        "another-error-message", "IN101", "path/to/file_name"
    )
    assert formatted_error == "path/to/file_name: [IN101] - another-error-message\n"
    assert "path/to/file_name - [IN101]" in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error(
        "ignore-file-specific", "BA101", "path/to/file_name"
    )
    assert formatted_error is None
    assert "path/to/file_name - [BA101]" not in FOUND_FILES_AND_ERRORS
    assert "path/to/file_name - [BA101]" in FOUND_FILES_AND_IGNORED_ERRORS
    assert "path/to/file_name: [BA101] - ignore-file-specific\n" in caplog.text

    formatted_error = base_validator.handle_error(
        "Error-message", "ST109", "path/to/file_name"
    )
    assert formatted_error == "path/to/file_name: [ST109] - Error-message\n"
    assert "path/to/file_name - [ST109]" in FOUND_FILES_AND_ERRORS


def test_handle_error_file_with_path(pack):
    """
    Given
    - An ignore errors list associated with a file_path.
    - An error, message, code and file paths.

    When
    - Running handle_error method.

    Then
    _ Ensure ignoring right file when full path mentioned in .pack-ignore.
    - Ensure the resulting error messages are correctly formatted.
    - Ensure ignored error codes which can be ignored return None.
    - Ensure non ignored errors are in FOUND_FILES_AND_ERRORS list.
    - Ensure ignored error are not in FOUND_FILES_AND_ERRORS and in FOUND_FILES_AND_IGNORED_ERRORS
    """
    integration = pack.create_integration("TestIntegration")
    rel_path_integration_readme = integration.readme.path[
        integration.readme.path.find("Packs") :
    ]
    rel_path_pack_readme = pack.readme.path[pack.readme.path.find("Packs") :]

    pack_ignore_text = f"""[file:{rel_path_integration_readme}]
    ignore=ST109

    [file:{rel_path_pack_readme}]
    ignore=BA101"""
    pack.pack_ignore.write_text(pack_ignore_text)

    base_validator = BaseValidator(
        ignored_errors={
            rel_path_pack_readme: ["BA101"],
            rel_path_integration_readme: ["PA113"],
        },
        print_as_warnings=True,
    )

    formatted_error = base_validator.handle_error(
        "Error-message", "BA101", integration.readme.path
    )
    assert formatted_error == f"{integration.readme.path}: [BA101] - Error-message\n"
    assert f"{integration.readme.path} - [BA101]" in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error(
        "Error-message", "PA113", integration.readme.path
    )
    assert formatted_error is None
    assert f"{integration.readme.path} - [PA113]" not in FOUND_FILES_AND_ERRORS
    assert f"{integration.readme.path} - [PA113]" in FOUND_FILES_AND_IGNORED_ERRORS

    formatted_error = base_validator.handle_error(
        "Error-message", "PA113", pack.readme.path
    )
    assert formatted_error == f"{pack.readme.path}: [PA113] - Error-message\n"
    assert f"{pack.readme.path} - [PA113]" in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error(
        "Error-message", "BA101", pack.readme.path
    )
    assert formatted_error is None
    assert f"{pack.readme.path} - [BA101]" not in FOUND_FILES_AND_ERRORS
    assert f"{pack.readme.path} - [BA101]" in FOUND_FILES_AND_IGNORED_ERRORS


def test_check_deprecated_where_ignored_list_exists(repo):
    """
    Given
    - deprecated integration yml.
    - A pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the predefined deprecated ignored errors contains the default error list.
    - Ensure the ignored errors pack ignore does not contain the default error list, but only the pack-ignore errors.
    - Ensure the predefined by support ignored errors does not contain anything.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    integration.yml.write_dict({"deprecated": True})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={"integration.yml": ["BA101"]})
        base_validator.check_deprecated(files_path)
    assert base_validator.predefined_deprecated_ignored_errors == {
        files_path: DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST
    }
    assert base_validator.ignored_errors == {"integration.yml": ["BA101"]}
    assert not base_validator.predefined_by_support_ignored_errors


def test_check_deprecated_where_ignored_list_does_not_exist(repo):
    """
    Given
    - An deprecated integration yml.
    - No pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the predefined deprecated ignored errors contains the default error list.
    - Ensure the ignored errors pack ignore does not contain anything.
    - Ensure the predefined by support ignored errors does not contain anything.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    integration.yml.write_dict({"deprecated": True})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert base_validator.predefined_deprecated_ignored_errors == {
        files_path: DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST
    }
    assert not base_validator.ignored_errors
    assert not base_validator.predefined_by_support_ignored_errors


def test_check_deprecated_non_deprecated_integration_no_ignored_errors(repo):
    """
    Given
    - An non-deprecated integration yml.
    - No pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure there is no resulting ignored errors list.
    - Ensure there is no result in the predefined_deprecated_ignored_errors list.
    - Ensure there is no result in the predefined_by_support_ignored_errors list.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    integration.yml.write_dict({"deprecated": False})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert "integration" not in base_validator.ignored_errors
    assert "integration" not in base_validator.predefined_deprecated_ignored_errors
    assert "integration" not in base_validator.predefined_by_support_ignored_errors


def test_check_deprecated_non_deprecated_integration_with_ignored_errors(repo):
    """
    Given
    - An non-deprecated integration yml.
    - A pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the resulting ignored errors list is the pre-existing one.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    integration.yml.write_dict({"deprecated": False})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={"integration.yml": ["BA101"]})
        base_validator.check_deprecated(files_path)
    assert base_validator.ignored_errors["integration.yml"] == ["BA101"]


def test_check_deprecated_playbook(repo):
    """
    Given
    - An non-deprecated playbook yml.

    When
    - Running check_deprecated method.

    Then
    - Ensure the predefined deprecated ignored errors list includes the deprecated default error list only.
    """
    pack = repo.create_pack("pack")
    playbook = pack.create_integration("playbook-somePlaybook")
    test_file_path = join(git_path(), "demisto_sdk", "tests", "test_files")
    valid_deprecated_playbook_file_path = join(
        test_file_path,
        "Packs",
        "CortexXDR",
        "Playbooks",
        "Valid_Deprecated_Playbook.yml",
    )
    playbook.yml.write_dict(get_yaml(valid_deprecated_playbook_file_path))
    files_path = playbook.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert base_validator.predefined_deprecated_ignored_errors == {
        files_path: DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST
    }


def test_check_support_status_xsoar_file(repo, mocker):
    """
    Given
    - An xsoar supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the resulting ignored errors list does not include the integration file name.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    meta_json = {PACK_METADATA_SUPPORT: "xsoar"}
    mocker.patch.object(
        BaseValidator, "get_metadata_file_content", return_value=meta_json
    )
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml.rel_path)

        assert "integration.yml" not in base_validator.ignored_errors


def test_check_support_status_partner_file(repo, mocker):
    """
    Given
    - An partner supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the 'predefined by support ignored_errors' list includes the partner ignore-list.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    meta_json = {PACK_METADATA_SUPPORT: "partner"}
    mocker.patch.object(
        BaseValidator, "get_metadata_file_content", return_value=meta_json
    )
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml.rel_path)

        assert (
            base_validator.predefined_by_support_ignored_errors[
                integration.yml.rel_path
            ]
            == PRESET_ERROR_TO_IGNORE["partner"]
        )


def test_check_support_status_community_file(repo, mocker):
    """
    Given
    - An community supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the 'predefined by support ignored errors' list includes the community ignore-list.
    """
    pack = repo.create_pack("pack")
    integration = pack.create_integration("integration")
    meta_json = {PACK_METADATA_SUPPORT: "community"}
    mocker.patch.object(
        BaseValidator, "get_metadata_file_content", return_value=meta_json
    )
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml.rel_path)

        assert (
            base_validator.predefined_by_support_ignored_errors[
                integration.yml.rel_path
            ]
            == PRESET_ERROR_TO_IGNORE["community"]
        )


class TestJsonOutput:
    def test_json_output(self, repo):
        """
        Given
        - Scenario 1:
        - A ui applicable error.
        - No pre existing json_outputs file.

        - Scenario 2:
        - A non ui applicable warning.
        - A pre existing json_outputs file.

        When
        - Running json_output method.

        Then
        - Scenario 1:
        - Ensure the json outputs file is created and it hold the json error in the `outputs` field.
        - Scenario 2:
        - Ensure the json outputs file is modified and holds the json warning in the `outputs` field.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("MyInt")
        integration.create_default_integration()
        json_path = os.path.join(repo.path, "valid_json.json")
        base = BaseValidator(json_file_path=json_path)
        (
            ui_applicable_error_message,
            ui_applicable_error_code,
        ) = Errors.wrong_display_name("param1", "param2")
        (
            non_ui_applicable_error_message,
            non_ui_applicable_error_code,
        ) = Errors.wrong_subtype()
        expected_json_1 = [
            {
                "filePath": integration.yml.path,
                "fileType": "yml",
                "entityType": "integration",
                "errorType": "Settings",
                "name": "Sample",
                "severity": "error",
                "errorCode": ui_applicable_error_code,
                "message": ui_applicable_error_message,
                "relatedField": "<parameter-name>.display",
            }
        ]

        expected_json_2 = [
            {
                "filePath": integration.yml.path,
                "fileType": "yml",
                "entityType": "integration",
                "errorType": "Settings",
                "name": "Sample",
                "severity": "error",
                "errorCode": ui_applicable_error_code,
                "message": ui_applicable_error_message,
                "relatedField": "<parameter-name>.display",
                "linter": "validate",
            },
            {
                "filePath": integration.yml.path,
                "fileType": "yml",
                "entityType": "integration",
                "errorType": "Settings",
                "name": "Sample",
                "severity": "warning",
                "errorCode": non_ui_applicable_error_code,
                "message": non_ui_applicable_error_message,
                "relatedField": "subtype",
                "linter": "validate",
            },
        ]

        with ChangeCWD(repo.path):
            # create new file
            base.json_output(
                integration.yml.path,
                ui_applicable_error_code,
                ui_applicable_error_message,
                False,
            )
            with open(base.json_file_path) as f:
                json_output = json.load(f)

            assert json_output.sort() == expected_json_1.sort()

            # update existing file
            base.json_output(
                integration.yml.path,
                non_ui_applicable_error_code,
                non_ui_applicable_error_message,
                True,
            )
            with open(base.json_file_path) as f:
                json_output = json.load(f)

            assert json_output == expected_json_2

    def test_json_output_with_json_file(self, repo):
        """
        Given
        - A ui applicable error.
        - An existing and an empty json_outputs file.

        When
        - Running json_output method.

        Then
        - Ensure the json outputs file is created and it hold the json error in the `outputs` field.
        - Ensure it's not failing because the file is empty.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("MyInt")
        integration.create_default_integration()
        json_path = os.path.join(repo.path, "valid_json.json")
        open(json_path, "x")
        base = BaseValidator(json_file_path=json_path)
        (
            ui_applicable_error_message,
            ui_applicable_error_code,
        ) = Errors.wrong_display_name("param1", "param2")
        expected_json_1 = [
            {
                "filePath": integration.yml.path,
                "fileType": "yml",
                "entityType": "integration",
                "errorType": "Settings",
                "name": "Sample",
                "severity": "error",
                "errorCode": ui_applicable_error_code,
                "message": ui_applicable_error_message,
                "ui": True,
                "relatedField": "<parameter-name>.display",
                "linter": "validate",
            }
        ]

        with ChangeCWD(repo.path):
            # create new file
            base.json_output(
                integration.yml.path,
                ui_applicable_error_code,
                ui_applicable_error_message,
                False,
            )
            with open(base.json_file_path) as f:
                json_output = json.load(f)

            assert json_output.sort() == expected_json_1.sort()

    def test_json_output_with_unified_yml_image_error(self, repo):
        """
        Given
        - A ui applicable image error that occurred in a unified yml.
        - An existing and an empty json_outputs file.

        When
        - Running json_output method.

        Then
        - Ensure the json outputs file is created and it hold the json error in the `outputs` field.
        - Ensure the entityType is 'image'.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("MyInt")
        integration.create_default_integration()
        json_path = os.path.join(repo.path, "valid_json.json")
        open(json_path, "x")
        base = BaseValidator(json_file_path=json_path)
        ui_applicable_error_message, ui_applicable_error_code = Errors.image_too_large()
        expected_json_1 = [
            {
                "filePath": integration.yml.path,
                "fileType": "yml",
                "entityType": "image",
                "errorType": "Settings",
                "name": "Sample",
                "severity": "error",
                "errorCode": ui_applicable_error_code,
                "message": ui_applicable_error_message,
                "ui": True,
                "relatedField": "image",
                "validate": "linter",
            }
        ]

        with ChangeCWD(repo.path):
            # create new file
            base.json_output(
                integration.yml.path,
                ui_applicable_error_code,
                ui_applicable_error_message,
                False,
            )
            with open(base.json_file_path) as f:
                json_output = json.load(f)

            assert json_output.sort() == expected_json_1.sort()


def test_content_items_naming(repo):
    """
    Given: Pack with XSIAM content items.
    When: validating pack items.
    Then: validate the naming conventions are used.
    """
    pack = repo.create_pack("pack")

    def create_invalid_rule(pack: Pack, creation_def):
        """
        Creates parsing/modeling rule with invalid name of xif file.
        Args:
            pack: pack to create rule in
            creation_def: creation function to create the rule
        Returns:
            invalid rule
        """
        if creation_def in (pack.create_parsing_rule, pack.create_modeling_rule):
            invalid_rule = creation_def("test_rule")
            xif_path = invalid_rule.rules.path.split("/")
            xif_path[-1] = "test_invalid_rule.xif"
            invalid_rule.rules.path = "/".join(xif_path)
            return invalid_rule

    invalid_entities_paths = [
        pack.create_xdrc_template("test").path,
        pack.create_correlation_rule("test_correlation").path,
        pack.create_xsiam_dashboard("test_dashboard").path,
        pack.create_xsiam_report("test_report").path,
        create_invalid_rule(pack, pack.create_parsing_rule).rules.path,
        create_invalid_rule(pack, pack.create_modeling_rule).rules.path,
    ]

    valid_entities_paths = [
        pack.create_modeling_rule("pack").yml.path,
        pack.create_parsing_rule("pack").yml.path,
        pack.create_correlation_rule("pack_test").path,
        pack.create_xsiam_dashboard("pack_test").path,
        pack.create_xsiam_report("pack_test").path,
    ]

    base_validator = BaseValidator(ignored_errors={})
    for entity in invalid_entities_paths:
        assert not base_validator.validate_xsiam_content_item_title(entity)

    for entity in valid_entities_paths:
        assert base_validator.validate_xsiam_content_item_title(entity)

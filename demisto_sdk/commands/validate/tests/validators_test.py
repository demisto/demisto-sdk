import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest
import toml
from more_itertools import map_reduce
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.constants import (
    DEPLOYMENT_JSON_FILENAME,
    INTEGRATIONS_DIR,
    ExecutionMode,
    GitStatuses,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.initializer import (
    ConnectorAwareInitializer,
    Initializer,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_connector_object,
    create_integration_object,
    create_pack_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.commands.validate.validation_results import ResultWriter
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name_all_statuses import (
    IDNameAllStatusesValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    VALIDATION_CATEGORIES,
    BaseValidator,
    FixResult,
    ValidationResult,
    get_all_validators,
    is_error_ignored,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC100_breaking_backwards_subtype import (
    BreakingBackwardsSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO106_docker_image_is_latest_tag import (
    DockerImageTagIsNotOutdated,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place_all_files import (
    MarketplacesFieldValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA108_pack_metadata_name_not_valid import (
    PackMetadataNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA114_pack_metadata_version_should_be_raised import (
    PackMetadataVersionShouldBeRaisedValidator,
)

INTEGRATION = create_integration_object()
INTEGRATION.path = Path(
    f"{CONTENT_PATH}/Packs/pack_0/Integrations/integration_0/integration_0.yml"
)


def get_validate_manager(mocker):
    validation_results = ResultWriter()
    config_reader = ConfigReader(category="test")
    initializer = Initializer()
    mocker.patch.object(Initializer, "gather_objects_to_run_on", return_value=({}, {}))
    return ValidateManager(
        validation_results=validation_results,
        config_reader=config_reader,
        initializer=initializer,
    )


@pytest.mark.parametrize(
    "validations_to_run, sub_classes, expected_results",
    [
        (
            [],
            [
                IDNameValidator,
                BreakingBackwardsSubtypeValidator,
                PackMetadataNameValidator,
            ],
            [],
        ),
        (
            ["BA101", "BC100"],
            [
                IDNameAllStatusesValidator,
                BreakingBackwardsSubtypeValidator,
                PackMetadataNameValidator,
            ],
            [IDNameAllStatusesValidator(), BreakingBackwardsSubtypeValidator()],
        ),
        (
            ["TE"],
            [
                IDNameValidator,
                BreakingBackwardsSubtypeValidator,
                PackMetadataNameValidator,
            ],
            [],
        ),
        (
            ["BA101", "TE103"],
            [
                IDNameAllStatusesValidator,
                BreakingBackwardsSubtypeValidator,
                PackMetadataNameValidator,
            ],
            [IDNameAllStatusesValidator()],
        ),
    ],
)
def test_filter_validators(
    mocker: MockerFixture, validations_to_run, sub_classes, expected_results
):
    """
    Given
    a list of validation_to_run (config file select section mock), and a list of sub_classes (a mock for the BaseValidator sub classes)
        - Case 1: An empty validation_to_run list, and a list of three BaseValidator sub classes.
        - Case 2: A list with 2 validations to run where both validations exist, and a list of three BaseValidator sub classes.
        - Case 3: A list with only 1 item which is a prefix of an existing error code of the validations, and a list of three BaseValidator sub classes.
        - Case 4: A list with two validation to run where only one validation exist, and a list of three BaseValidator sub classes.
    When
    - Calling the filter_validators function.
    Then
        - Case 1: Make sure the retrieved list is empty.
        - Case 2: Make sure the retrieved list contains the two validations co-oping with the two error codes from validation_to_run.
        - Case 3: Make sure the retrieved list is empty.
        - Case 4: Make sure the retrieved list contains only the validation with the error_code that actually co-op with the validation_to_run.
    """
    validate_manager = get_validate_manager(mocker)
    mocker.patch.object(ConfiguredValidations, "select", validations_to_run)
    with patch.object(BaseValidator, "__subclasses__", return_value=sub_classes):
        with patch(
            "demisto_sdk.commands.validate.validators.base_validator.get_all_validators_specific_validation",
            return_value=[],
        ):
            results = validate_manager.filter_validators()
            assert results == expected_results


@pytest.mark.parametrize(
    "category_to_run, execution_mode, config_file_content, expected_results, ignore_support_level, specific_validations, codes_to_ignore",
    [
        pytest.param(
            None,
            ExecutionMode.USE_GIT,
            {
                "use_git": {"select": ["BA101", "BC100", "PA108"]},
                "ignorable_errors": ["E002", "W001"],
            },
            ConfiguredValidations(
                ["BA101", "BC100", "PA108"], [], ["E002", "W001"], {}
            ),
            False,
            [],
            ["E002", "W001"],
            id="Case 1",
        ),
        pytest.param(
            "custom_category",
            ExecutionMode.USE_GIT,
            {
                "ignorable_errors": ["BA101"],
                "custom_category": {
                    "select": ["BA101", "BC100", "PA108"],
                },
                "use_git": {"select": ["TE105", "TE106", "TE107", "BA101"]},
            },
            ConfiguredValidations(["BC100", "PA108"], [], ["BA101"], {}),
            False,
            [],
            ["BA101"],
            id="Case 2",
        ),
        pytest.param(
            None,
            ExecutionMode.SPECIFIC_FILES,
            {"path_based_validations": {"select": ["BA101", "BC100", "PA108"]}},
            ConfiguredValidations(["BA101", "BC100", "PA108"], [], [], {}),
            False,
            [],
            [],
            id="Case 3",
        ),
        pytest.param(
            None,
            ExecutionMode.USE_GIT,
            {
                "support_level": {"community": {"ignore": ["BA101", "BC100", "PA108"]}},
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            ConfiguredValidations(
                ["TE105", "TE106", "TE107"],
                [],
                [],
                {"community": {"ignore": ["BA101", "BC100", "PA108"]}},
            ),
            False,
            [],
            [],
            id="Case 4",
        ),
        pytest.param(
            None,
            ExecutionMode.USE_GIT,
            {
                "support_level": {"community": {"ignore": ["BA101", "BC100", "PA108"]}},
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            ConfiguredValidations(["TE105", "TE106", "TE107"], [], [], {}),
            True,
            [],
            [],
            id="Case 5",
        ),
        pytest.param(
            None,
            True,
            {"use_git": {"select": ["BA101", "BC100", "PA108"]}},
            ConfiguredValidations(["TE100", "TE101"], [], [], {}),
            False,
            ["TE100", "TE101"],
            [],
            id="Case 6",
        ),
    ],
)
def test_gather_validations_from_conf(
    mocker: MockerFixture,
    category_to_run: Optional[str],
    execution_mode: ExecutionMode,
    config_file_content: Dict,
    expected_results: ConfiguredValidations,
    ignore_support_level: bool,
    specific_validations: List[str],
    codes_to_ignore: List[str],
):
    """
    Given
    a category_to_run, a use_git flag, a config file content, and a ignore_support_level flag.
        - Case 1: No category to run, execution_mode set to use_git, config file content with only use_git.select section, and ignore_support_level set to False, and an empty specific validations list.
        - Case 2: A custom category to run, execution_mode set to use_git, config file content with use_git.select, and custom_category with both ignorable_errors and select sections, and ignore_support_level set to False, and an empty specific validations list.
        - Case 3: No category to run, execution_mode not set to use_git, config file content with path_based_validations.select section, and ignore_support_level set to False, and an empty specific validations list.
        - Case 4: No category to run, execution_mode set to use_git, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to False, and an empty specific validations list.
        - Case 5: No category to run, execution_mode set to use_git, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to True, and an empty specific validations list.
        - Case 6: No category to run, execution_mode set to use_git, config file content with only use_git.select section, ignore_support_level set to False, and a specific validations list with 2 error codes.

    When
    - Calling the gather_validations_from_conf function.
    Then
        - Case 1: Make sure the retrieved results contains only use_git.select results.
        - Case 2: Make sure the retrieved results contains the custom category results and ignored the use_git results.
        - Case 3: Make sure the retrieved results contains the path_based_validations results.
        - Case 4: Make sure the retrieved results contains both the support level and the use_git sections.
        - Case 5: Make sure the retrieved results contains only the use_git section.
        - Case 6: Make sure the retrieved results contains only the specific validations section.
    """
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader(
        category=category_to_run, explicitly_selected=specific_validations
    )
    results: ConfiguredValidations = config_reader.read(
        mode=execution_mode,
        ignore_support_level=ignore_support_level,
        codes_to_ignore=codes_to_ignore,
    )
    assert results.select == expected_results.select
    assert results.ignorable_errors == expected_results.ignorable_errors
    assert results.warning == expected_results.warning
    assert results.support_level_dict == expected_results.support_level_dict


@pytest.mark.parametrize(
    "results, fixing_results, expected_results",
    [
        (
            [
                ValidationResult(
                    validator=IDNameValidator(),
                    message="",
                    content_object=INTEGRATION,
                )
            ],
            [],
            {
                "validations": [
                    {
                        "file path": str(INTEGRATION.path),
                        "error code": "BA101",
                        "message": "",
                    }
                ],
                "fixed validations": [],
                "invalid content items": [],
                "Validations that caught exceptions": [],
            },
        ),
        (
            [],
            [],
            {
                "validations": [],
                "fixed validations": [],
                "invalid content items": [],
                "Validations that caught exceptions": [],
            },
        ),
        (
            [
                ValidationResult(
                    validator=IDNameValidator(),
                    message="",
                    content_object=INTEGRATION,
                )
            ],
            [
                FixResult(
                    validator=IDNameValidator(),
                    message="Fixed this issue",
                    content_object=INTEGRATION,
                )
            ],
            {
                "validations": [
                    {
                        "file path": str(INTEGRATION.path),
                        "error code": "BA101",
                        "message": "",
                    }
                ],
                "fixed validations": [
                    {
                        "file path": str(INTEGRATION.path),
                        "error code": "BA101",
                        "message": "Fixed this issue",
                    }
                ],
                "invalid content items": [],
                "Validations that caught exceptions": [],
            },
        ),
    ],
)
def test_write_results_to_json_file(results, fixing_results, expected_results):
    """
    Given
    results and fixing_results lists.
        - Case 1: One validation result.
        - Case 2: Both lists are empty.
        - Case 3: Both lists has one item.
    When
    - Calling the write_results_to_json_file function.
    Then
        - Case 1: Make sure the results hold both list where the fixing results is empty.
        - Case 2: Make sure the results hold both list where both are empty.
        - Case 3: Make sure the results hold both list where both hold 1 result each.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json"
    ) as temp_file:
        temp_file_path = temp_file.name
        validation_results = ResultWriter(json_file_path=temp_file_path)
        validation_results.validation_results = results
        validation_results.fixing_results = fixing_results
        validation_results.write_results_to_json_file()
        with open(temp_file_path, "r") as file:
            loaded_data = json.load(file)
            assert loaded_data == expected_results


@pytest.mark.parametrize(
    "only_throw_warnings, results, expected_exit_code, expected_warnings_call_count, expected_error_call_count, expected_error_code_in_warnings, expected_error_code_in_errors",
    [
        (
            ["BA101"],
            [
                ValidationResult(
                    validator=IDNameValidator(),
                    message="",
                    content_object=INTEGRATION,
                )
            ],
            0,
            1,
            1,
            ["BA101"],
            [],
        ),
        (
            [],
            [
                ValidationResult(
                    validator=IDNameValidator(),
                    message="",
                    content_object=INTEGRATION,
                )
            ],
            1,
            1,
            2,
            [],
            ["BA101"],
        ),
        (
            ["BC100"],
            [
                ValidationResult(
                    validator=IDNameValidator(),
                    message="",
                    content_object=INTEGRATION,
                ),
                ValidationResult(
                    validator=BreakingBackwardsSubtypeValidator(),
                    message="",
                    content_object=INTEGRATION,
                ),
            ],
            1,
            2,
            2,
            ["BC100"],
            ["BA101"],
        ),
    ],
)
def test_post_results(
    only_throw_warnings,
    results,
    expected_exit_code,
    expected_warnings_call_count,
    expected_error_call_count,
    expected_error_code_in_warnings,
    expected_error_code_in_errors,
    caplog,
):
    """
    Given
    an only_throw_warnings list, and a list of results.
        - Case 1: One failed validation with its error_code in the only_throw_warnings list.
        - Case 2: One failed validation with its error_code not in the only_throw_warnings list.
        - Case 3: One failed validation with its error_code in the only_throw_warnings list and one failed validation with its error_code not in the only_throw_warnings list.
    When
    - Calling the post_results function.
    Then
        - Make sure the error and warning loggers was called the correct number of times with the right error codes, and that the exit code was calculated correctly.
        - Case 1: Make sure the exit_code is 0 (success), and that the warning logger was called once with 'BA101' and the error logger wasn't called.
        - Case 2: Make sure the exit_code is 1 (failure), and that the error logger was called once with 'BA101' and the warning logger wasn't called.
        - Case 3: Make sure the exit_code is 1 (failure), and that the error logger was called once with 'BA101' and the warning logger was called once with 'BC100'
    """
    validation_results = ResultWriter()
    validation_results.validation_results = results
    exit_code = validation_results.post_results(
        ConfiguredValidations(warning=only_throw_warnings)
    )
    assert exit_code == expected_exit_code

    log_by_level = map_reduce(caplog.records, lambda log: log.levelno)
    warnings = log_by_level.get(30, ())
    assert len(warnings) == expected_warnings_call_count
    for code in expected_error_code_in_warnings:
        assert code in " ".join({log.message for log in warnings})

    errors = log_by_level.get(40, ())
    assert len(errors) == expected_error_call_count
    for code in expected_error_code_in_errors:
        assert code in " ".join({log.message for log in errors})


@pytest.mark.parametrize(
    "failing_error_codes, warning_error_codes, config_file_content, exit_code, expected_msg",
    [
        (
            ["BA100", "CR102", "CL101", "TE111"],
            [],
            ConfiguredValidations(
                ignorable_errors=["BA100"], selected_path_based_section=["CR102"]
            ),
            1,
            "<red>Validate summary\nThe following errors were thrown as a part of this pr: BA100, CR102, CL101, TE111.\nThe following errors can be ignored: BA100.\nThe following errors cannot be ignored: CR102, CL101, TE111.\nIf the AG100 validation in the pre-commit GitHub Action fails, the pull request cannot be force-merged.\nThe following errors don't run as part of the nightly flow and therefore can be force merged: BA100, CL101, TE111.\n</red><red>######################################################################################################\nNote that the following errors cannot be force merged and therefore must be handled: CR102.\n######################################################################################################\n</red>",
        ),
        (
            ["BA100", "CR102", "CL101", "TE111"],
            [],
            ConfiguredValidations(selected_path_based_section=["CR102", "BA100"]),
            1,
            "<red>Validate summary\nThe following errors were thrown as a part of this pr: BA100, CR102, CL101, TE111.\nThe following errors cannot be ignored: BA100, CR102, CL101, TE111.\nIf the AG100 validation in the pre-commit GitHub Action fails, the pull request cannot be force-merged.\nThe following errors don't run as part of the nightly flow and therefore can be force merged: CL101, TE111.\n</red><red>#############################################################################################################\nNote that the following errors cannot be force merged and therefore must be handled: BA100, CR102.\n#############################################################################################################\n</red>",
        ),
        (
            ["BA100", "CR102", "CL101", "TE111"],
            ["BC111"],
            ConfiguredValidations(ignorable_errors=["BA100", "TE111"]),
            1,
            "<red>Validate summary\nThe following errors were reported as warnings: BC111.\nThe following errors were thrown as a part of this pr: BA100, CR102, CL101, TE111.\nThe following errors can be ignored: BA100, TE111.\nThe following errors cannot be ignored: CR102, CL101.\nIf the AG100 validation in the pre-commit GitHub Action fails, the pull request cannot be force-merged.\nThe following errors don't run as part of the nightly flow and therefore can be force merged: BA100, CR102, CL101, TE111.\n</red>",
        ),
        (
            ["BA100", "CR102", "CL101", "TE111"],
            [],
            ConfiguredValidations(
                ignorable_errors=["BA100"],
                selected_path_based_section=["BA100", "CR102", "CL101", "TE111"],
            ),
            1,
            "<red>Validate summary\nThe following errors were thrown as a part of this pr: BA100, CR102, CL101, TE111.\nThe following errors can be ignored: BA100.\nThe following errors cannot be ignored: CR102, CL101, TE111.\nIf the AG100 validation in the pre-commit GitHub Action fails, the pull request cannot be force-merged.\n</red><red>###########################################################################################################################\nNote that the following errors cannot be force merged and therefore must be handled: BA100, CR102, CL101, TE111.\n###########################################################################################################################\n</red>",
        ),
    ],
)
def test_summarize_validation_results(
    mocker,
    failing_error_codes,
    warning_error_codes,
    config_file_content,
    exit_code,
    expected_msg,
):
    """
    Given
    set of failing error codes and a ConfiguredValidations object with specified ignorable_errors and selected_path_based_section.
        - Case 1: 4 failed errors, 1 ignorable, and 1 path based.
        - Case 2: 4 failed errors, none are ignorable, and 2 are path based.
        - Case 3: 4 failed errors, 2 ignorable, and none are path based.
        - Case 4: 4 failed errors, 1 ignorable, and all are path based.
    When
    - Calling the summarize_validation_results function.
    Then
        - Make sure the error logger was called the correct message.
        - Case 1: The error log should not mention warnings section, and be called with 1 ignorable error, 3 forcemergeable errors, 3 non ignorable errors, and 1 error that must be handled.
        - Case 2: The error log should not mention warnings section, and omit the ignorable error section, post 2 forcemergeable errors, 4 non ignorable errors, and 2 error that must be handled.
        - Case 3: The error log should mention warnings section, and be called with 2 ignorable errors, 4 forcemergeable errors, 2 non ignorable errors, no errors that must be handled, and a summary that says the PR is forcemergeable.
        - Case 4: The error log should not mention warnings section, and be called with 1 ignorable error, no forcemergeable errors, 3 non ignorable errors, section and 4 error that must be handled.
    """
    mock = mocker.patch.object(logger, "error")
    validation_results = ResultWriter()
    validation_results.summarize_validation_results(
        failing_error_codes, warning_error_codes, config_file_content, exit_code
    )
    msg = ""
    for args in mock.call_args_list:
        msg += args[0][0]
    assert expected_msg == msg


@pytest.mark.parametrize(
    "validator, expected_results",
    [
        (IDNameAllStatusesValidator(), True),
        (PackMetadataNameValidator(), False),
        (BreakingBackwardsSubtypeValidator(), False),
    ],
)
def test_should_run(validator, expected_results):
    """
    Given:
    A validator.
        - Case 1: IDNameAllStatusesValidator which support Integration content type.
        - Case 2: PackMetadataNameValidator which doesn't support Integration content type.
        - Case 3: BreakingBackwardsSubtypeValidator which support Integration content type only for modified and renamed git statuses.
    When:
    - Calling the should_run function on a given integration.
    Then:
    Make sure the right result is returned.
        - Case 1: Should return True.
        - Case 2: Should return False.
        - Case 3: Should return False.
    """
    assert expected_results == validator.should_run(
        INTEGRATION, [], {}, running_execution_mode=ExecutionMode.USE_GIT
    )


def test_should_run_api_module():
    """
    Given:
    A validator.
        - Case 1: A docker image validator and an APIModule script.
    When:
    - Calling the should_run function.
    Then:
    Make sure the right result is returned.
        - Case 1: Should return False.
    """
    script = create_script_object()
    script.path = script.path.parent / "testAPIModule.yml"
    validator = DockerImageTagIsNotOutdated()
    assert not validator.should_run(
        script, [], {}, running_execution_mode=ExecutionMode.USE_GIT
    )


class _FakeRelatedFile:
    def __init__(self, file_path: str):
        self.file_path = file_path


class _FakeContentItem:
    """Minimal stand-in for a ContentItem for is_error_ignored tests.

    Emulates the two lookup paths used by is_error_ignored:
    - per-file ignore on the item itself via ``ignored_errors``
    - per-related-file ignore via ``ignored_errors_related_files``
    The related-file attribute (e.g. ``skill_content``) is only present when
    ``has_related_file`` is True, mirroring an AgentixSkill; an AgentixAction
    has no such attribute so the getattr raises AttributeError.
    """

    def __init__(
        self,
        own_ignored,
        related_ignored=None,
        has_related_file=False,
    ):
        self.ignored_errors = list(own_ignored)
        self._related_ignored = list(related_ignored or [])
        if has_related_file:
            self.skill_content = _FakeRelatedFile("skill_body.md")

    def ignored_errors_related_files(self, _file_path):
        return self._related_ignored


def test_is_error_ignored_falls_through_to_main_when_related_file_missing():
    """
    Given:
    - A validator error code that declares a related_file_type (SKILL_CONTENT).
    - A content item that has NO related file (like an AgentixAction) but does
      list the code under its own per-file `[file:...]` ignore section.
    When:
    - Calling is_error_ignored with the related_file_type.
    Then:
    - The main content per-file ignore is honored (returns True), because the
      lookup falls through when no related file matches.
    """
    item = _FakeContentItem(
        own_ignored=["AG112"], related_ignored=[], has_related_file=False
    )
    assert (
        is_error_ignored(
            "AG112",
            ["AG112"],
            item,
            related_file_type=[RelatedFileType.SKILL_CONTENT],
        )
        is True
    )


def test_is_error_ignored_related_file_still_matches():
    """
    Given:
    - A content item that has a related file which lists the code to ignore
      (like an AgentixSkill using the SKILL_CONTENT section).
    When:
    - Calling is_error_ignored with the related_file_type.
    Then:
    - The related-file ignore is honored (returns True), preserving prior
      behavior.
    """
    item = _FakeContentItem(
        own_ignored=[], related_ignored=["AG112"], has_related_file=True
    )
    assert (
        is_error_ignored(
            "AG112",
            ["AG112"],
            item,
            related_file_type=[RelatedFileType.SKILL_CONTENT],
        )
        is True
    )


def test_is_error_ignored_not_ignored_anywhere():
    """
    Given:
    - A content item that lists the code in neither its own per-file section nor
      any related file section.
    When:
    - Calling is_error_ignored with the related_file_type.
    Then:
    - The code is not ignored (returns False).
    """
    item = _FakeContentItem(own_ignored=[], related_ignored=[], has_related_file=False)
    assert (
        is_error_ignored(
            "AG112",
            ["AG112"],
            item,
            related_file_type=[RelatedFileType.SKILL_CONTENT],
        )
        is False
    )


def test_object_collection_with_readme_path(repo):
    """
    Given:
    - A path to integration readme
    When:
    - Calling the paths_to_basecontent_set.
    Then:
    - Make sure that an integration was parsed.
    """

    yml_content = load_yaml("integration.yml")
    pack = repo.create_pack("pack_no_1")
    integration = pack.create_integration(yml=yml_content)
    integration.code.write("from MicrosoftApiModule import *")
    integration.readme.write("test")
    readme_path = integration.readme.path
    initializer = Initializer()
    obj_set, _, _ = initializer.paths_to_basecontent_set({Path(readme_path)})
    obj = obj_set.pop()
    assert obj is not None
    assert obj.content_type == ContentType.INTEGRATION


def test_object_collection_with_pack_path(repo):
    """
    Given:
    - A path to a pack that contain an integration.
    When:
    - Calling the gather_objects_to_run_on.
    Then:
    - Make sure that both the pack and the integration object were returned.
    """

    yml_content = load_yaml("integration.yml")
    pack = repo.create_pack("pack_no_1")
    integration = pack.create_integration(yml=yml_content)
    integration.code.write("from MicrosoftApiModule import *")
    integration.readme.write("test")
    initializer = Initializer(
        file_path=str(pack.path), execution_mode=ExecutionMode.SPECIFIC_FILES
    )
    obj_set, _ = initializer.gather_objects_to_run_on()
    obj_types = {obj.content_type for obj in obj_set}
    assert obj_types == {ContentType.INTEGRATION, ContentType.PACK}


def test_all_files_gather_includes_connectors(mocker):
    """
    Given:
    - ALL_FILES (-a) execution mode where ContentDTO.from_path parses both a
      pack and a connector from the repository.
    When:
    - Calling the base Initializer.gather_objects_to_run_on.
    Then:
    - Make sure the parsed Connector object is included in the returned set and
      is not discarded (so connector-only validators such as CO100 run under -a
      exactly as they do under -g).
    """
    from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

    pack = create_pack_object()
    connector = create_connector_object()
    fake_dto = ContentDTO.construct(packs=[pack], connectors=[connector])
    mocker.patch.object(ContentDTO, "from_path", return_value=fake_dto)

    initializer = Initializer(execution_mode=ExecutionMode.ALL_FILES)
    obj_set, _ = initializer.gather_objects_to_run_on()

    assert connector in obj_set


def test_load_files_with_pack_path(repo):
    """
    Given:
    - A path to a pack that contain an integration.
    When:
    - Calling the load_files.
    Then:
    - Make sure that only the path to the pack was returned in PosixPath form.
    """
    pack = repo.create_pack("pack_no_1")
    pack.create_integration()
    initializer = Initializer()
    loaded_files_set = initializer.load_files([str(pack.path)])
    assert len(loaded_files_set) == 1
    assert loaded_files_set.pop() == pack.path


def test_load_files_with_integration_dir(repo):
    """
    Given:
    - A path to the integration dir of a pack.
    When:
    - Calling the load_files.
    Then:
    - Make sure that all the files from that dir was returned.
    """
    pack = repo.create_pack("pack_no_1")
    integration = pack.create_integration()
    initializer = Initializer()
    integration_dir = f"{pack.path}/{INTEGRATIONS_DIR}"
    loaded_files_set = initializer.load_files([integration_dir])
    assert len(loaded_files_set) != 1
    assert all(
        Path(path) in loaded_files_set
        for path in (
            integration.yml.path,
            integration.readme.path,
            integration.code.path,
            integration.description.path,
        )
    )


def test_load_files_with_private_pack_path(repo, tmp_path):
    """
    Given:
    - A relative PACK-level path (e.g. ``Packs/MyPack``) that only exists under
      an external ``--private-content-path`` repository (not in the main
      checkout).
    When:
    - Calling load_files with ``private_content_path`` set.
    Then:
    - The files are resolved from the private repo and tracked in
      ``private_content_files`` (regression for pack-level private input that
      was previously short-circuited).
    """
    private_root = tmp_path / "content-private"
    pack_dir = private_root / "Packs" / "MyPack" / "Scripts" / "MyScript"
    pack_dir.mkdir(parents=True)
    script_yml = pack_dir / "MyScript.yml"
    script_yml.write_text("commonfields:\n  id: MyScript\n")

    initializer = Initializer(private_content_path=private_root)
    loaded = initializer.load_files(["Packs/MyPack"])

    assert script_yml in loaded
    assert script_yml in initializer.private_content_files


def test_load_files_with_relative_connectors_path(tmp_path):
    """
    Given:
    - A relative connectors path (e.g. ``connectors/foo`` or
      ``connectors/foo/connector.yaml``) that only exists under an external
      ``--connectors-content-path`` (UCC) repository.
    When:
    - Calling load_files with ``connectors_content_path`` set.
    Then:
    - The connector files are resolved from the UCC repo and tracked in
      ``connectors_content_files`` (regression for the -ccp relative-path case).
    """
    ucc_root = tmp_path / "unified-connectors-content"
    connector_dir = ucc_root / "connectors" / "foo"
    connector_dir.mkdir(parents=True)
    connector_yaml = connector_dir / "connector.yaml"
    connector_yaml.write_text("name: foo\n")
    handler = connector_dir / "components" / "handlers" / "xsoar"
    handler.mkdir(parents=True)
    handler_yaml = handler / "handler.yaml"
    handler_yaml.write_text("handler: foo\n")

    # Relative directory input.
    initializer = Initializer(connectors_content_path=ucc_root)
    loaded = initializer.load_files(["connectors/foo"])
    assert connector_yaml in loaded
    assert handler_yaml in loaded
    assert connector_yaml in initializer.connectors_content_files

    # Relative single-file input.
    initializer_file = Initializer(connectors_content_path=ucc_root)
    loaded_file = initializer_file.load_files(["connectors/foo/connector.yaml"])
    assert loaded_file == {connector_yaml}
    assert connector_yaml in initializer_file.connectors_content_files


def test_collect_related_files_main_items(repo):
    """
    Given:
    - A path to integration code, modeling_rule schema, and pack readme.
    When:
    - Calling the collect_related_files_main_items.
    Then:
    - Make sure that the right main passes were returned:
        - integration code should return the integration yml path.
        - modeling_rule schema should return the modeling_rule yml path.
        - pack readme should return the pack_metadata.json pack..
    """
    pack = repo.create_pack("pack_no_1")
    initializer = Initializer()
    integration = pack.create_integration()
    modeling_rule = pack.create_modeling_rule({})
    results = initializer.collect_related_files_main_items(
        {
            Path(integration.code.path),
            Path(modeling_rule.schema.path),
            Path(pack.readme.path),
        }
    )
    assert results == {
        Path(integration.yml.path),
        Path(modeling_rule.yml.path),
        Path(pack.pack_metadata.path),
    }


@pytest.mark.parametrize(
    "pack_name",
    (
        "AgentixAction_CortexGetUserDefinedParsingRules",
        "AgentixAction_CortexGetUserDefinedModelingRules",
    ),
)
@pytest.mark.parametrize(
    "file_attributes",
    (
        ["readme"],
        ["pack_ignore"],
        ["secrets"],
        ["author_image"],
        ["readme", "pack_ignore", "secrets", "author_image"],
    ),
)
def test_collect_related_files_main_items_pack_name_contains_rules_dir_substring(
    repo, pack_name, file_attributes
):
    """
    Given:
    - A pack whose name contains "ParsingRules" or "ModelingRules" as a substring
      (e.g. an AgentixAction pack such as
      "AgentixAction_CortexGetUserDefinedParsingRules"), along with one or more of
      its pack-level auxiliary files (README, .pack-ignore, .secrets-ignore,
      Author_image.png).
    When:
    - Calling collect_related_files_main_items.
    Then:
    - The auxiliary files must resolve to the pack_metadata.json (via is_pack_item),
      and must NOT be short-circuited into the ModelingRules/ParsingRules branch
      just because the pack name contains the substring "ParsingRules" or
      "ModelingRules".
      Regression test for BA102 spam on packs whose names contain "ParsingRules"
      or "ModelingRules".
    """
    pack = repo.create_pack(pack_name)
    initializer = Initializer()
    results = initializer.collect_related_files_main_items(
        {Path(getattr(pack, attribute).path) for attribute in file_attributes}
    )
    assert results == {Path(pack.pack_metadata.path)}


def test_get_items_status(repo):
    """
    Given:
    - A dictionary with:
        - A path to integration code with ADDED git status.
        - A path to script code with ADDED git status.
        - A path to integration yml with MODIFIED git status.
        - A path to modeling_rule schema with MODIFIED git status.
        - A path to pack readme with ADDED git status.
        - A path to pack metadata with MODIFIED git status.
    When:
    - Calling the collect_related_files_main_items.
    Then:
    - Make sure that the right amount of paths are returned and that the right statuses were given:
        - The integration code and yml should return the integration yml path with the yml status (MODIFIED).
        - The modeling_rule schema should return the modeling_rule yml path with no status.
        - The pack readme and pack_metadata.json should return the pack_metadata.json path with the pack_metadata.json status (MODIFIED).
        - The script code should return the script yml path with script code status (ADDED).
    """
    pack = repo.create_pack("pack_no_1")
    initializer = Initializer()
    integration = pack.create_integration()
    modeling_rule = pack.create_modeling_rule({})
    script = pack.create_script()
    statuses_dict = {
        Path(integration.code.path): GitStatuses.ADDED,
        Path(script.code.path): GitStatuses.ADDED,
        Path(integration.yml.path): GitStatuses.MODIFIED,
        Path(modeling_rule.schema.path): GitStatuses.MODIFIED,
        Path(pack.readme.path): GitStatuses.ADDED,
        Path(pack.pack_metadata.path): GitStatuses.MODIFIED,
    }
    results = initializer.get_items_status(statuses_dict)
    expected_results = {
        Path(integration.yml.path): GitStatuses.MODIFIED,
        Path(modeling_rule.yml.path): None,
        Path(pack.pack_metadata.path): GitStatuses.MODIFIED,
        Path(script.yml.path): GitStatuses.ADDED,
    }
    assert len(results.keys()) == 4
    assert all(
        expected_results[item_path] == git_status
        for item_path, git_status in results.items()
    )


def test_validation_prefix():
    """
    Given   All validators
    When    Checking for their prefixes
    Then    Make sure it's from the allowed list of prefixes
    """
    prefix_to_validator = map_reduce(get_all_validators(), lambda v: v.error_category)
    invalid = {
        validation
        for prefix, validation in prefix_to_validator.items()
        if prefix not in VALIDATION_CATEGORIES
    }
    assert not invalid, sorted(invalid)


def test_rationale():
    """
    Tests that all validators have a non-empty rationale.
    If this test failed when you modified a validator, go ahead and add the rationale attribute, explaining *why* the validation exists.
    """
    assert not [
        validator for validator in get_all_validators() if not validator.rationale
    ]


def test_description():
    """
    Tests that all validators have a non-empty description.
    If this test failed when you modified a validator, go ahead and add the description attribute, explaining *what* the validation checks in content.
    """
    assert not [
        validator for validator in get_all_validators() if not validator.description
    ]


def test_get_unfiltered_changed_files_from_git_case_untracked_files_identify(mocker):
    """
    Given:
        An Initializer instance where the fetched git files are not equal to the amount of files written
         in the contribution_files_relative_paths file.
    When:
        Calling get_unfiltered_changed_files_from_git in a scenario where modified_files, added_files,
         and rename_files are empty, and the contribution_files_relative_paths file contains some file names.
    Then:
        Ensure that the error is raised and the function does not return modified_files,
         added_files, or rename_files.
    """
    initializer = Initializer()
    initializer.validate_git_installed()
    mocker.patch.object(GitUtil, "modified_files", return_value=set())
    mocker.patch.object(GitUtil, "added_files", return_value=set())
    mocker.patch.object(GitUtil, "renamed_files", return_value=set())
    mocker.patch.dict(os.environ, {"CONTRIB_BRANCH": "true"})
    with open("contribution_files_relative_paths.txt", "w") as file:
        temp_file = Path("contribution_files_relative_paths.txt")
        file.write("untrack_file")
    try:
        _, _, _ = initializer.get_unfiltered_changed_files_from_git()
    except ValueError as e:
        assert "Error: Mismatch in the number of files." in str(e)
    finally:
        if Path.exists(temp_file):
            Path.unlink(temp_file)


def test_collect_files_to_run_merges_connectors_content_repo_diff(mocker):
    """
    Given:
        An Initializer with ``connectors_content_path`` set (the -ccp flag used
        together with -g), where the main content repo has one changed file and
        the UCC repo has its own changed connector files.
    When:
        Calling collect_files_to_run.
    Then:
        Ensure the UCC repo is git-diffed directly (via
        get_unfiltered_changed_files_from_git on the UCC path) and its changed
        connector files are merged into the returned modified/added/renamed sets
        and tracked in ``connectors_content_files`` - so only the connectors
        actually changed in the UCC repo are collected, mirroring the
        content-private behavior.
    """
    ucc_path = Path("/tmp/ucc")
    content_modified = {Path("Packs/MyPack/Integrations/MyInt/MyInt.yml")}
    ucc_modified = {Path("connectors/datadog/connector.yaml")}
    ucc_added = {Path("connectors/okta/connector.yaml")}

    initializer = Initializer(connectors_content_path=ucc_path)
    initializer.validate_git_installed()

    # First call: main content repo diff. Second call: UCC repo diff.
    mocker.patch.object(
        initializer,
        "get_unfiltered_changed_files_from_git",
        side_effect=[
            (content_modified, set(), set()),
            (ucc_modified, ucc_added, set()),
        ],
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())
    # The UCC deleted-files branch constructs a fresh GitUtil on the UCC path.
    mocker.patch(
        "demisto_sdk.commands.validate.initializer.GitUtil",
        return_value=mocker.MagicMock(deleted_files=lambda **_: set()),
    )

    modified_files, added_files, renamed_files, deleted_files = (
        initializer.collect_files_to_run(file_path="")
    )

    # UCC changes merged into the combined result.
    assert ucc_modified.issubset(modified_files)
    assert content_modified.issubset(modified_files)
    assert ucc_added.issubset(added_files)
    # UCC changes tracked separately so path redirection can target the UCC repo.
    assert initializer.connectors_content_files == ucc_modified | ucc_added


def test_collect_files_to_run_skips_connectors_diff_when_no_ccp(mocker):
    """
    Given:
        An Initializer WITHOUT ``connectors_content_path`` set.
    When:
        Calling collect_files_to_run.
    Then:
        Ensure the UCC repo is never git-diffed (the content repo is diffed
        exactly once) and ``connectors_content_files`` stays empty - a
        regression guard that -ccp has no effect unless provided.
    """
    initializer = Initializer()
    initializer.validate_git_installed()
    diff_mock = mocker.patch.object(
        initializer,
        "get_unfiltered_changed_files_from_git",
        return_value=(set(), set(), set()),
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())

    initializer.collect_files_to_run(file_path="")

    diff_mock.assert_called_once_with()
    assert initializer.connectors_content_files == set()


def test_ignored_with_run_all(mocker):
    """
    This UT verifies that when running with -a on validators that run on all files,
    we don't fail content_items that should be ignored although they raised an error.

    Given:
        A ValidateManager object with one integration and one script, one validator ignored by the integration
    When:
        Calling run_validations with -a and throwing an error only for the integration.
    Then:
        - Ensure that the error received from the validator didn't fail run_validations.
    """
    validate_manager = get_validate_manager(mocker)
    validate_manager.configured_validations = ConfiguredValidations(
        select=["GR100"],
        warning=[],
        ignorable_errors=["GR100"],
        support_level_dict={},
    )
    validate_manager.initializer.execution_mode = ExecutionMode.ALL_FILES
    validator = MarketplacesFieldValidatorAllFiles()
    validate_manager.validators = [validator]
    mocker.patch.object(Integration, "ignored_errors", ["GR100"])
    mocker.patch.object(Script, "ignored_errors", [])
    integration = create_integration_object()
    script = create_script_object()
    mocker.patch.object(
        MarketplacesFieldValidatorAllFiles,
        "obtain_invalid_content_items",
        return_value=[
            ValidationResult(
                validator=validator,
                message="error",
                content_object=integration,
            )
        ],
    )
    validate_manager.objects_to_run = [integration, script]
    assert 0 == validate_manager.run_validations()


def test_check_metadata_version_bump_on_content_changes(mocker, repo):
    """
    Given: pack with newly added integration.
    When: Initializing ValidateManager using git.
    Then: Ensure PackMetadataVersionShouldBeRaisedValidator is initialized and the external args are properly passed.
    """
    pack = create_pack_object(["currentVersion"], ["1.1.1"])
    integration = create_integration_object()
    pack.content_items.integration.extend(integration)
    validation_results = ResultWriter()
    config_reader = ConfigReader(explicitly_selected=["PA114"])
    mocker.patch.object(
        Initializer,
        "get_files_using_git",
        return_value=({BaseContent.from_path(Path(integration.path)), pack}, {}, {}),
    )
    mocker.patch.object(
        BaseContent,
        "from_path",
        return_value=BaseContent.from_path(Path(pack.path), metadata_only=True),
    )
    initializer = Initializer(
        prev_ver="some_prev_ver", execution_mode=ExecutionMode.USE_GIT
    )

    validate_manager = ValidateManager(
        validation_results=validation_results,
        config_reader=config_reader,
        initializer=initializer,
    )

    version_bump_validator = None
    for validator in validate_manager.validators:
        if isinstance(validator, PackMetadataVersionShouldBeRaisedValidator):
            version_bump_validator = validator

    # Assert the PA114 validation will run
    assert version_bump_validator


@pytest.mark.parametrize(
    "config_file_content, expected_results, allow_ignore_all_errors",
    [
        pytest.param(
            {
                "use_git": {
                    "select": ["BA101", "BC100", "PA108"],
                    "warning": ["BA100"],
                },
                "ignorable_errors": ["PA108"],
            },
            ConfiguredValidations(
                ["BA101", "BC100", "PA108"], ["BA100"], ["PA108"], {}
            ),
            False,
        ),
        pytest.param(
            {
                "use_git": {
                    "select": ["BA101", "BC100", "PA108"],
                    "warning": ["BA100"],
                },
                "ignorable_errors": ["PA108"],
            },
            ConfiguredValidations(
                ["BA101", "BC100", "PA108"],
                ["BA100"],
                ["BA101", "BC100", "PA108", "BA100"],
                {},
            ),
            True,
        ),
    ],
)
def test_config_reader_ignore_all_flag(
    mocker: MockerFixture,
    config_file_content: Dict,
    expected_results: ConfiguredValidations,
    allow_ignore_all_errors: bool,
):
    """
    Given
    a config file content mock and a allow_ignore_all_errors flag
        - Case 1: allow_ignore_all_errors set to False.
        - Case 2: allow_ignore_all_errors set to True.
    When
    - Calling the gather_validations_from_conf function.
    Then
        - Case 1: Make sure the retrieved results contains the ignorable_errors mentioned in the ignorable_errors section.
        - Case 2: Make sure the retrieved results contains all the error codes that appears in the select & warning sections.
    """
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader(allow_ignore_all_errors=allow_ignore_all_errors)
    results: ConfiguredValidations = config_reader.read()
    assert results.select == expected_results.select
    assert results.ignorable_errors == expected_results.ignorable_errors
    assert results.warning == expected_results.warning
    assert results.support_level_dict == expected_results.support_level_dict


def test_is_pack_item_deployment_json():
    """
    Given:
        - A path to a deployment.json file in a pack.
    When:
        - Calling is_pack_item with the path.
    Then:
        - Should return True, indicating it's a pack-level item.
    """
    initializer = Initializer()
    assert (
        initializer.is_pack_item(f"Packs/SomePack/{DEPLOYMENT_JSON_FILENAME}") is True
    )


def test_deployment_json_in_zero_depth_files():
    """
    Given:
        - The ZERO_DEPTH_FILES constant.
    When:
        - Checking if deployment.json is included.
    Then:
        - deployment.json should be in ZERO_DEPTH_FILES.
    """
    from demisto_sdk.scripts.validate_content_path import ZERO_DEPTH_FILES

    assert DEPLOYMENT_JSON_FILENAME in ZERO_DEPTH_FILES


# ============================================================
# ConnectorAwareInitializer - initializer function tests
# ============================================================


class TestConnectorAwareInitializerCrossMatch:
    """Tests for ConnectorAwareInitializer._cross_match_and_expand (handler-level)."""

    def test_direct_match_links_handler_and_integration(self):
        """
        Given: Both a connector and its referenced integration in the sets.
        When: _cross_match_and_expand is called.
        Then: handler.related_integration points to the integration,
              integration.related_content points to the handler,
              and graph search is NOT invoked.
        """
        # Default handler template has xsoar-integration-id: "TestIntegration"
        # Default integration template has object_id: "TestIntegration"
        integration = create_integration_object()
        connector = create_connector_object()

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with (
            patch.object(
                ConnectorAwareInitializer, "_graph_search_integration"
            ) as mock_graph,
            patch.object(
                ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
            ),
        ):
            initializer._cross_match_and_expand({integration}, {connector})
            mock_graph.assert_not_called()

        handler = connector.xsoar_handlers[0]
        assert handler.related_integration is integration
        assert integration.related_content is handler

    def test_unrelated_integration_removed_by_cleanup(self):
        """
        Given: An integration that no connector handler references.
        When: _cross_match_and_expand is called.
        Then: Integration is removed from the result by the cleanup step.
        """
        integration = create_integration_object(
            paths=["commonfields.id", "name"],
            values=["UnrelatedInt", "UnrelatedInt"],
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            result = initializer._cross_match_and_expand({integration}, set())

        assert integration not in result
        assert len(result) == 0

    def test_graph_search_discovers_connector(self):
        """
        Given: An integration in the set, and a connector in the graph
               whose handler references that integration.
        When: _cross_match_and_expand is called.
        Then: Phase 2a graph search discovers the connector and links handler.
        """
        integration = create_integration_object()
        discovered_connector = create_connector_object(connector_id="discovered")

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with patch.object(
            ConnectorAwareInitializer,
            "_all_graph_connectors",
            return_value=[discovered_connector],
        ):
            result = initializer._cross_match_and_expand({integration}, set())

        assert discovered_connector in result
        discovered_handler = discovered_connector.xsoar_handlers[0]
        assert discovered_handler.related_integration is integration

    def test_graph_search_for_unmatched_handler(self):
        """
        Given: A connector with a handler whose referenced integration is NOT
               in the set.
        When: _cross_match_and_expand is called.
        Then: Phase 2b graph search is invoked for the integration ID.
        """
        connector = create_connector_object()
        graph_integration = create_integration_object()

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with (
            patch.object(
                ConnectorAwareInitializer,
                "_all_graph_connectors",
                return_value=[],
            ),
            patch.object(
                ConnectorAwareInitializer,
                "_graph_search_integration",
                return_value=[graph_integration],
            ) as mock_graph,
        ):
            result = initializer._cross_match_and_expand(set(), {connector})
            mock_graph.assert_called_once_with("TestIntegration")

        handler = connector.xsoar_handlers[0]
        assert handler.related_integration is graph_integration
        assert graph_integration in result

    def test_graph_found_deprecated_integration_is_linked_but_not_validated(self):
        """
        Given: A connector handler whose referenced integration is found in the
               graph but is DEPRECATED.
        When: _cross_match_and_expand runs the graph-expand phase.
        Then: The handler's related_integration is populated (so CO164 sees it
              as existing), but the deprecated integration is NOT added to the
              returned validation set (integration validators must not run on
              it).
        """
        connector = create_connector_object()
        deprecated_integration = create_integration_object()
        deprecated_integration.deprecated = True

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with (
            patch.object(
                ConnectorAwareInitializer,
                "_all_graph_connectors",
                return_value=[],
            ),
            patch.object(
                ConnectorAwareInitializer,
                "_graph_search_integration",
                return_value=[deprecated_integration],
            ),
        ):
            result = initializer._cross_match_and_expand(set(), {connector})

        handler = connector.xsoar_handlers[0]
        # Linked so CO164 can distinguish "exists" from "missing".
        assert handler.related_integration is deprecated_integration
        # But NOT a validation target.
        assert deprecated_integration not in result

    def test_graph_found_non_platform_integration_is_neither_linked_nor_added(self):
        """
        Given: A connector handler whose referenced integration is found in the
               graph but is NOT in the PLATFORM marketplace.
        When: _cross_match_and_expand runs the graph-expand phase.
        Then: The integration is treated as out of scope: it is neither linked
              to the handler nor added to the validation set.
        """
        from demisto_sdk.commands.common.constants import MarketplaceVersions

        connector = create_connector_object()
        non_platform_integration = create_integration_object()
        non_platform_integration.deprecated = False
        non_platform_integration.marketplaces = [MarketplaceVersions.XSOAR]

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with (
            patch.object(
                ConnectorAwareInitializer,
                "_all_graph_connectors",
                return_value=[],
            ),
            patch.object(
                ConnectorAwareInitializer,
                "_graph_search_integration",
                return_value=[non_platform_integration],
            ),
        ):
            result = initializer._cross_match_and_expand(set(), {connector})

        handler = connector.xsoar_handlers[0]
        assert handler.related_integration is None
        assert non_platform_integration not in result

    def test_multiple_handlers_each_matched_independently(self):
        """
        Given: A connector with 2 XSOAR handlers referencing different integrations,
               both integrations are in the set.
        When: _cross_match_and_expand is called.
        Then: Each handler is matched to its own integration independently.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-sf",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "Salesforce",
                            "xsoar-pack-id": "Salesforce",
                            "xsoar-content-id": "test-connector",
                        },
                    },
                },
                {
                    "id": "xsoar-sf-iam",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "SalesforceIAM",
                            "xsoar-pack-id": "SalesforceIAM",
                            "xsoar-content-id": "test-connector",
                        },
                    },
                },
            ]
        )
        integration1 = create_integration_object(
            paths=["commonfields.id", "name"],
            values=["Salesforce", "Salesforce"],
        )
        integration2 = create_integration_object(
            paths=["commonfields.id", "name"],
            values=["SalesforceIAM", "SalesforceIAM"],
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with (
            patch.object(
                ConnectorAwareInitializer, "_graph_search_integration"
            ) as mock_graph,
            patch.object(
                ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
            ),
        ):
            initializer._cross_match_and_expand(
                {integration1, integration2}, {connector}
            )
            mock_graph.assert_not_called()

        handlers = connector.xsoar_handlers
        sf_handler = next(h for h in handlers if h.xsoar_integration_id == "Salesforce")
        iam_handler = next(
            h for h in handlers if h.xsoar_integration_id == "SalesforceIAM"
        )
        assert sf_handler.related_integration is integration1
        assert iam_handler.related_integration is integration2

    def test_connector_table_is_fetched_once_across_unmatched_integrations(self):
        """
        Given: Several connectors whose handlers reference integrations that are
               NOT in the working set (so both graph-expand phases run), and an
               unmatched integration with no connector in the set.
        When: _cross_match_and_expand is called.
        Then: The connector table - which has no usable index for the
              handler->integration reference and therefore requires a full scan -
              is fetched exactly once regardless of how many unmatched
              integrations there are. Integrations keep using indexed per-id
              lookups, so they are queried once per unmatched handler.
        """
        connector_a = create_connector_object(
            connector_id="conn-a",
            handlers=[
                {
                    "id": "xsoar-a",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "IntA",
                            "xsoar-pack-id": "IntA",
                            "xsoar-content-id": "conn-a",
                        },
                    },
                },
            ],
        )
        connector_b = create_connector_object(
            connector_id="conn-b",
            handlers=[
                {
                    "id": "xsoar-b",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "IntB",
                            "xsoar-pack-id": "IntB",
                            "xsoar-content-id": "conn-b",
                        },
                    },
                },
            ],
        )
        graph_int_a = create_integration_object(
            paths=["commonfields.id", "name"], values=["IntA", "IntA"]
        )
        graph_int_b = create_integration_object(
            paths=["commonfields.id", "name"], values=["IntB", "IntB"]
        )
        # Integrations in the set with no matching connector handler present.
        # There must be more than one: the per-integration scan this test guards
        # against would only be observable with multiple unmatched integrations.
        unmatched_integration_1 = create_integration_object(
            paths=["commonfields.id", "name"], values=["Orphan1", "Orphan1"]
        )
        unmatched_integration_2 = create_integration_object(
            paths=["commonfields.id", "name"], values=["Orphan2", "Orphan2"]
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        integrations_by_id = {"IntA": graph_int_a, "IntB": graph_int_b}

        with (
            patch.object(
                ConnectorAwareInitializer,
                "_all_graph_connectors",
                return_value=[],
            ) as mock_connectors,
            patch.object(
                ConnectorAwareInitializer,
                "_graph_search_integration",
                side_effect=lambda int_id: [integrations_by_id[int_id]]
                if int_id in integrations_by_id
                else [],
            ) as mock_integrations,
        ):
            initializer._cross_match_and_expand(
                {unmatched_integration_1, unmatched_integration_2},
                {connector_a, connector_b},
            )

        # The full connector scan happens once, not once per unmatched
        # integration (there are two of them here).
        assert mock_connectors.call_count == 1
        # Integrations resolve via indexed point lookups - one per handler.
        assert sorted(c.args[0] for c in mock_integrations.call_args_list) == [
            "IntA",
            "IntB",
        ]

        assert connector_a.xsoar_handlers[0].related_integration is graph_int_a
        assert connector_b.xsoar_handlers[0].related_integration is graph_int_b


class TestConnectorAwareInitializerStash:
    """Tests for the CO192 stash populated by
    ``ConnectorAwareInitializer._remove_unmatched_integrations`` and read
    through ``get_integrations_without_connector_handler``.

    Focus:

    * Unmatched integrations are stashed BEFORE eviction (so CO192 sees
      what the initializer just dropped).
    * The stash is a frozen set (validators must not mutate the
      initializer's view).
    * Every ``gather_objects_to_run_on`` call resets/re-assigns the stash,
      so a run with everything covered does not inherit a previous run's
      value.
    * The gather post-filter drops partner/community-supported integrations
      (they are out of scope for the connector flow, so they must not
      appear in the CO192 stash as false positives).
    """

    @pytest.fixture(autouse=True)
    def _reset_stash(self):
        # Isolate every test from a prior test's stash. The stash is a
        # class attribute, so leakage across cases is easy to miss.
        ConnectorAwareInitializer._integrations_without_connector_handler = frozenset()
        yield
        ConnectorAwareInitializer._integrations_without_connector_handler = frozenset()

    def test_unmatched_integration_populates_stash(self):
        """
        Given: An integration in the working set with no connector handler
               referencing it (Phase 1 fails, Phase 2a graph returns no
               connectors).
        When: ``_cross_match_and_expand`` runs to completion.
        Then: The integration is dropped from the returned set AND is
              stashed on ``_integrations_without_connector_handler``. CO192
              reads this stash instead of ``content_items``.
        """
        integration = create_integration_object(
            paths=["commonfields.id", "name"],
            values=["UnrelatedInt", "UnrelatedInt"],
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            result = initializer._cross_match_and_expand({integration}, set())

        assert integration not in result  # matches existing cleanup behaviour
        stash = ConnectorAwareInitializer.get_integrations_without_connector_handler()
        assert isinstance(stash, frozenset)
        # Compare by object_id -- pydantic models may go through
        # copy/hash-round-trip when placed into a frozenset in some code
        # paths, so identity assertions can be flaky across pydantic
        # versions. object_id captures the behavioural contract ("the same
        # integration ended up in the stash").
        assert integration.object_id in {i.object_id for i in stash}

    def test_covered_integration_is_not_stashed(self):
        """
        Given: An integration and a connector whose handler references it
               (Phase 1 pairs them).
        When: ``_cross_match_and_expand`` runs to completion.
        Then: The stash is emptied (assigned an empty frozenset) - the
              integration must not appear in the CO192 report.
        """
        connector = create_connector_object()
        integration = create_integration_object()

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        # Seed the stash with a stale value from a hypothetical previous run
        # so the assertion below actually proves the cleanup step overwrites
        # it rather than accidentally leaving the fixture's reset in place.
        ConnectorAwareInitializer._integrations_without_connector_handler = frozenset(
            {create_integration_object()}
        )

        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            initializer._cross_match_and_expand({integration}, {connector})

        assert (
            ConnectorAwareInitializer.get_integrations_without_connector_handler()
            == frozenset()
        )

    def test_stash_is_frozen(self):
        """
        Given: The stash's default (empty frozenset).
        When: A caller tries to mutate it.
        Then: An AttributeError is raised. This is what stops a buggy
              validator from corrupting the initializer's view by
              ``got.add(...)``-ing on the returned set.
        """
        stash = ConnectorAwareInitializer.get_integrations_without_connector_handler()

        assert isinstance(stash, frozenset)
        with pytest.raises(AttributeError):
            stash.add(create_integration_object())  # type: ignore[attr-defined]

    def test_stash_reset_across_runs(self):
        """
        Given: A first run that stashes an uncovered integration.
        When: A second run that has nothing uncovered goes through
              ``_remove_unmatched_integrations``.
        Then: The stash is reset to an empty frozenset - the second run
              does not inherit the first run's value.
        """
        first_uncovered = create_integration_object(
            paths=["commonfields.id", "name"], values=["Uncov1", "Uncov1"]
        )
        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            initializer._cross_match_and_expand({first_uncovered}, set())

        assert first_uncovered.object_id in {
            i.object_id
            for i in ConnectorAwareInitializer.get_integrations_without_connector_handler()
        }

        # Second run: everything covered.
        integration = create_integration_object()
        connector = create_connector_object()
        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            initializer._cross_match_and_expand({integration}, {connector})

        assert (
            ConnectorAwareInitializer.get_integrations_without_connector_handler()
            == frozenset()
        )

    def test_multiple_unmatched_all_stashed(self):
        """
        Given: Several unmatched integrations in one run.
        When: ``_cross_match_and_expand`` runs to completion.
        Then: All of them appear in the stash (CO192 emits one result per
              offender rather than aggregating).
        """
        int_a = create_integration_object(
            paths=["commonfields.id", "name"], values=["OrphA", "OrphA"]
        )
        int_b = create_integration_object(
            paths=["commonfields.id", "name"], values=["OrphB", "OrphB"]
        )
        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)

        with patch.object(
            ConnectorAwareInitializer, "_all_graph_connectors", return_value=[]
        ):
            initializer._cross_match_and_expand({int_a, int_b}, set())

        stash = ConnectorAwareInitializer.get_integrations_without_connector_handler()
        stash_ids = {i.object_id for i in stash}
        assert {"OrphA", "OrphB"}.issubset(stash_ids)


class TestConnectorAwareInitializerGatherObjects:
    """Tests for ConnectorAwareInitializer.gather_objects_to_run_on filtering."""

    def test_non_xsoar_connector_filtered_out(self, mocker: MockerFixture):
        """
        Given: A connector with NO XSOAR handlers (only cwp).
        When: gather_objects_to_run_on filters objects.
        Then: Connector is excluded from the result.
        """
        from demisto_sdk.commands.content_graph.objects.connector import Connector

        connector = create_connector_object(
            handlers=[
                {
                    "id": "cwp-handler",
                    "metadata": {
                        "module": "cwp",
                        "version": "1.0.0",
                        "description": "CWP handler",
                        "tags": ["test"],
                        "ownership": {"team": "cwp", "maintainers": ["@test"]},
                    },
                }
            ]
        )
        integration = create_integration_object()

        # Use ALL_FILES mode so the code falls through to super().gather_objects_to_run_on()
        mocker.patch(
            "demisto_sdk.commands.validate.initializer.Initializer.gather_objects_to_run_on",
            return_value=({connector, integration}, set()),
        )
        mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=lambda ints, cons: ints | cons,
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)
        initializer.execution_mode = ExecutionMode.ALL_FILES
        filtered, _ = initializer.gather_objects_to_run_on()

        connectors_in_result = [o for o in filtered if isinstance(o, Connector)]
        assert len(connectors_in_result) == 0

    def test_non_platform_integration_filtered_out(self, mocker: MockerFixture):
        """
        Given: An integration that does NOT have PLATFORM in its marketplaces.
        When: gather_objects_to_run_on filters objects.
        Then: Integration is excluded from the result.
        """
        integration = create_integration_object(
            paths=["marketplaces"],
            values=[["xsoar"]],
        )

        mocker.patch(
            "demisto_sdk.commands.validate.initializer.Initializer.gather_objects_to_run_on",
            return_value=({integration}, set()),
        )
        mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=lambda ints, cons: ints | cons,
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)
        initializer.execution_mode = ExecutionMode.ALL_FILES
        filtered, _ = initializer.gather_objects_to_run_on()

        integrations_in_result = [o for o in filtered if isinstance(o, Integration)]
        assert len(integrations_in_result) == 0

    def test_deprecated_integration_filtered_out(self, mocker: MockerFixture):
        """
        Given: An integration that is deprecated.
        When: gather_objects_to_run_on filters objects.
        Then: Integration is excluded from the result.
        """
        connector = create_connector_object()
        integration = create_integration_object()
        integration.deprecated = True

        mocker.patch(
            "demisto_sdk.commands.validate.initializer.Initializer.gather_objects_to_run_on",
            return_value=({connector, integration}, set()),
        )
        mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=lambda ints, cons: ints | cons,
        )

        initializer = ConnectorAwareInitializer.__new__(ConnectorAwareInitializer)
        initializer.execution_mode = ExecutionMode.ALL_FILES
        filtered, _ = initializer.gather_objects_to_run_on()

        integrations_in_result = [o for o in filtered if isinstance(o, Integration)]
        assert len(integrations_in_result) == 0


class TestConnectorRelatedFileDeduplication:
    """Tests for collect_related_files_main_items connector deduplication."""

    def test_connector_files_deduplicate_to_connector_yaml(self):
        """
        Given: Multiple connector-related files modified (handler.yaml + capabilities.yaml).
        When: collect_related_files_main_items is called.
        Then: Both resolve to a single connectors/<name>/connector.yaml path.
        """
        initializer = Initializer()

        handler_path = Path(
            "connectors/salesforce/components/handlers/xsoar/handler.yaml"
        )
        capabilities_path = Path("connectors/salesforce/capabilities.yaml")

        with (
            patch(
                "demisto_sdk.commands.validate.initializer._is_connector_path",
                return_value=True,
            ),
            patch(
                "demisto_sdk.commands.validate.initializer._get_connector_dir",
                return_value=Path("connectors/salesforce"),
            ),
            patch.object(
                initializer,
                "is_unrelated_path",
                return_value=False,
            ),
            patch.object(
                initializer,
                "is_pack_item",
                return_value=False,
            ),
        ):
            result = initializer.collect_related_files_main_items(
                {handler_path, capabilities_path}
            )

        assert result == {Path("connectors/salesforce/connector.yaml")}
        assert len(result) == 1

    def test_get_items_status_maps_connector_files_to_connector_yaml(self):
        """
        Given: Connector-related files collected by the git flow -- a renamed
            connector image (png) and a modified handler.yaml.
        When: get_items_status (the ``-g`` reducer) is called.
        Then: Both resolve to the single connectors/<name>/connector.yaml path,
            the raw png is NOT collected (so it is never handed to the parser),
            and no pack_metadata.json is added for connector paths.
        """
        initializer = Initializer()

        png_path = Path(
            "connectors/aws-automation-and-collection/"
            "aws-automation-and-collection.png"
        )
        handler_path = Path(
            "connectors/aws-automation-and-collection/"
            "components/handlers/xsoar/handler.yaml"
        )
        connector_yaml = Path("connectors/aws-automation-and-collection/connector.yaml")

        with (
            patch(
                "demisto_sdk.commands.validate.initializer._is_connector_path",
                return_value=True,
            ),
            patch(
                "demisto_sdk.commands.validate.initializer._get_connector_dir",
                return_value=Path("connectors/aws-automation-and-collection"),
            ),
            patch.object(initializer, "is_unrelated_path", return_value=False),
            patch.object(initializer, "is_pack_item", return_value=False),
        ):
            results = initializer.get_items_status(
                {
                    png_path: GitStatuses.RENAMED,
                    handler_path: GitStatuses.MODIFIED,
                }
            )

        # Only the connector.yaml is collected.
        assert set(results.keys()) == {connector_yaml}
        # The raw png must never reach the parser.
        assert png_path not in results
        # No bogus pack_metadata.json is produced for connector paths.
        assert not any("pack_metadata.json" in str(p) for p in results)


class TestConnectorStatusMergePrecedence:
    """Tests that a connector changed under multiple git statuses is reported once."""

    @pytest.mark.parametrize(
        "existing, incoming, expected",
        [
            (GitStatuses.MODIFIED, GitStatuses.ADDED, GitStatuses.MODIFIED),
            (GitStatuses.ADDED, GitStatuses.MODIFIED, GitStatuses.MODIFIED),
            (GitStatuses.ADDED, GitStatuses.RENAMED, GitStatuses.RENAMED),
            (GitStatuses.ADDED, None, GitStatuses.ADDED),
            (None, GitStatuses.ADDED, GitStatuses.ADDED),
            (None, None, None),
            (GitStatuses.MODIFIED, GitStatuses.RENAMED, GitStatuses.MODIFIED),
        ],
    )
    def test_merge_git_statuses_precedence(self, existing, incoming, expected):
        """
        Given: Two git statuses that collapse onto the same content item.
        When: _merge_git_statuses resolves them.
        Then: The higher-precedence status is returned (MODIFIED always wins).
        """
        from demisto_sdk.commands.validate.initializer import _merge_git_statuses

        assert _merge_git_statuses(existing, incoming) == expected

    @pytest.mark.parametrize(
        "file_statuses",
        [
            # MODIFIED handler first, then ADDED .connector-ignore
            [
                (
                    Path("connectors/zoom/components/handlers/xsoar/handler.yaml"),
                    GitStatuses.MODIFIED,
                ),
                (Path("connectors/zoom/.connector-ignore"), GitStatuses.ADDED),
            ],
            # Reversed order: ADDED .connector-ignore first, then MODIFIED handler
            [
                (Path("connectors/zoom/.connector-ignore"), GitStatuses.ADDED),
                (
                    Path("connectors/zoom/components/handlers/xsoar/handler.yaml"),
                    GitStatuses.MODIFIED,
                ),
            ],
        ],
    )
    def test_added_and_modified_connector_collapses_to_modified(self, file_statuses):
        """
        Given: A connector with a MODIFIED handler.yaml and a newly ADDED
            .connector-ignore file (the exact scenario reported for zoom).
        When: get_items_status reduces the changed files -- in either iteration
            order.
        Then: A single connector.yaml entry is produced, and its status is
            MODIFIED (never ADDED), because the connector already exists.
        """
        initializer = Initializer()
        connector_yaml = Path("connectors/zoom/connector.yaml")

        with (
            patch(
                "demisto_sdk.commands.validate.initializer._is_connector_path",
                return_value=True,
            ),
            patch(
                "demisto_sdk.commands.validate.initializer._get_connector_dir",
                return_value=Path("connectors/zoom"),
            ),
            patch.object(initializer, "is_unrelated_path", return_value=False),
            patch.object(initializer, "is_pack_item", return_value=False),
        ):
            results = initializer.get_items_status(dict(file_statuses))

        assert set(results.keys()) == {connector_yaml}
        assert results[connector_yaml] == GitStatuses.MODIFIED


class TestHydrateIntegrationParams:
    """Tests for ``ConnectorAwareInitializer._hydrate_integration_params``.

    ``Integration.params`` is declared ``Field([], exclude=True)`` — it is
    never persisted to Neo4j, so an Integration returned by
    ``_graph_search_integration`` comes back with ``params == []``. Any
    connector-aware validator that reaches into
    ``handler.related_integration.params`` (CO116, CO121, CO190, …)
    silently false-positives on every param lookup unless the helper
    re-parses the on-disk YML and copies the fresh list back.

    Coverage targets:

    * The four early-return branches (``integration is None``, ``params``
      already populated, ``path`` missing, ``from_path`` raises).
    * The success path — ``from_path`` is called with the integration's
      ``path`` and ``integration.params`` is mutated **in place**, not
      reassigned to a new object. Downstream callers already hold a
      reference (``handler.related_integration``, ``matched_ids``, the
      ``integrations`` set) and would silently see stale data if the
      helper swapped the object.
    * The 'fresh integration also has empty params' branch — the helper
      is a no-op then, not an erroneous ``params = []`` reassignment.
    """

    @staticmethod
    def _fake_integration(**attrs):
        """Stand-in for a graph-hydrated Integration.

        The helper only reads ``integration.params``, ``integration.path``
        and (for the log message) ``integration.object_id``, and only
        writes ``integration.params``. A ``SimpleNamespace`` is enough
        and avoids the cost of constructing a full Pydantic model.
        """
        return SimpleNamespace(**attrs)

    def test_none_integration_is_noop(self, mocker):
        """
        Given: ``integration is None``.
        When: ``_hydrate_integration_params`` runs.
        Then: It returns without calling ``IntegrationModel.from_path``.
              Guarding here prevents an ``AttributeError`` on the
              subsequent ``getattr(integration, "params", …)`` when the
              caller passes a missing match.
        """
        from_path_spy = mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path"
        )

        ConnectorAwareInitializer._hydrate_integration_params(None)

        from_path_spy.assert_not_called()

    def test_already_populated_params_are_not_touched(self, mocker):
        """
        Given: An integration whose ``params`` list is already populated
               (loaded from disk, not from the graph).
        When: The helper runs.
        Then: It short-circuits — ``from_path`` is NOT called and the
              existing list is left exactly as-is (same object identity).
              Any re-parse here would be wasted I/O and would also risk
              overwriting caller-attached state.
        """
        existing_params = [SimpleNamespace(name="url"), SimpleNamespace(name="api_key")]
        integration = self._fake_integration(
            params=existing_params,
            path=Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml"),
            object_id="Foo",
        )
        from_path_spy = mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path"
        )

        ConnectorAwareInitializer._hydrate_integration_params(integration)

        from_path_spy.assert_not_called()
        assert integration.params is existing_params

    def test_missing_path_is_noop(self, mocker):
        """
        Given: A graph-hydrated integration with empty ``params`` and no
               ``path`` (some graph shapes don't attach one).
        When: The helper runs.
        Then: It returns without calling ``from_path``. Attempting to
              re-parse ``Path(None)`` would raise ``TypeError`` and mask
              the real (upstream) shape defect.
        """
        integration = self._fake_integration(params=[], path=None, object_id="Foo")
        from_path_spy = mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path"
        )

        ConnectorAwareInitializer._hydrate_integration_params(integration)

        from_path_spy.assert_not_called()
        assert integration.params == []

    def test_success_path_mutates_in_place_and_calls_from_path_with_path(self, mocker):
        """
        Given: A graph-hydrated integration with ``params == []`` and a
               valid on-disk ``path``; ``IntegrationModel.from_path``
               returns a fresh integration whose ``params`` list is
               populated.
        When: The helper runs.
        Then:
          * ``from_path`` is called with ``Path(integration.path)`` (the
            helper wraps the value defensively — a plain string caller
            must still work).
          * The fresh params are copied onto the EXISTING object in
            place — same ``integration`` reference — because downstream
            code (``handler.related_integration``, ``matched_ids``, the
            ``integrations`` set) already holds that reference. A
            reassignment to a new object would leave those references
            pointing at the stale, empty-params instance.
          * The stored list is a fresh copy (``list(...)``), not the
            same object as ``fresh.params`` — otherwise mutations on
            the graph object would leak into the fresh Pydantic model.
        """
        int_path = Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml")
        integration = self._fake_integration(params=[], path=int_path, object_id="Foo")
        original_ref = integration

        fresh_params = [SimpleNamespace(name="url"), SimpleNamespace(name="api_key")]
        fresh = SimpleNamespace(params=fresh_params)
        from_path_spy = mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path",
            return_value=fresh,
        )

        ConnectorAwareInitializer._hydrate_integration_params(integration)

        from_path_spy.assert_called_once_with(int_path)
        # Same object identity — mutated in place.
        assert integration is original_ref
        # Params content copied over.
        assert integration.params == fresh_params
        # But NOT the same list — a defensive copy protects the fresh
        # Pydantic model from downstream mutation.
        assert integration.params is not fresh_params

    def test_from_path_exception_is_swallowed_and_params_untouched(self, mocker):
        """
        Given: A graph-hydrated integration with empty ``params`` and a
               ``path`` where ``from_path`` raises (malformed YML, deleted
               file, permission error…).
        When: The helper runs.
        Then: The exception is swallowed (validators must keep running
              across other integrations) and ``params`` remains ``[]``.
              A CO116/CO121/CO190 false-positive downstream is preferable
              to crashing every connector validator for one bad file, and
              the caller's ``logger.debug`` records the failure.
        """
        integration = self._fake_integration(
            params=[],
            path=Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml"),
            object_id="Foo",
        )
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path",
            side_effect=RuntimeError("simulated parser failure"),
        )

        # Must not raise.
        ConnectorAwareInitializer._hydrate_integration_params(integration)

        assert integration.params == []

    def test_fresh_integration_with_empty_params_is_still_a_noop(self, mocker):
        """
        Given: A graph-hydrated integration with empty ``params``, whose
               on-disk YML re-parse ALSO yields an integration with
               empty ``params`` (a legitimate zero-param integration).
        When: The helper runs.
        Then: ``integration.params`` is not reassigned — the guard
              ``if fresh_params:`` protects against an otherwise
              indistinguishable overwrite that would still preserve the
              symptom (``params == []``) but obscure whether hydration
              actually ran, and would defeat any later "already
              populated" short-circuit if the caller re-runs the helper.
        """
        integration = self._fake_integration(
            params=[],
            path=Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml"),
            object_id="Foo",
        )
        original_list = integration.params

        fresh = SimpleNamespace(params=[])
        mocker.patch(
            "demisto_sdk.commands.content_graph.objects.integration."
            "Integration.from_path",
            return_value=fresh,
        )

        ConnectorAwareInitializer._hydrate_integration_params(integration)

        assert integration.params is original_list  # untouched


class TestDedupByObjectId:
    """Tests for ConnectorAwareInitializer._dedup_by_object_id."""

    class _FakeObj:
        """Minimal stand-in for BaseContent with object identity fields.

        Real BaseContent objects that differ only by ``git_status`` are unequal
        under Pydantic field-based equality, so both survive a ``set``. This fake
        reproduces that behavior deterministically for the dedup test.
        """

        def __init__(self, content_type, object_id, git_status):
            self.content_type = content_type
            self.object_id = object_id
            self.git_status = git_status

    def test_dedup_prefers_modified_over_added(self):
        """
        Given: Two objects with the same content_type and object_id, one ADDED
            and one MODIFIED (as produced when a connector's files carry
            different git statuses).
        When: _dedup_by_object_id collapses them.
        Then: Exactly one object remains, with status MODIFIED.
        """
        added = self._FakeObj("connector", "zoom", GitStatuses.ADDED)
        modified = self._FakeObj("connector", "zoom", GitStatuses.MODIFIED)

        result = ConnectorAwareInitializer._dedup_by_object_id({added, modified})

        assert len(result) == 1
        assert next(iter(result)).git_status == GitStatuses.MODIFIED

    def test_dedup_keeps_distinct_object_ids(self):
        """
        Given: Objects with different object_ids.
        When: _dedup_by_object_id runs.
        Then: All objects are preserved (nothing is collapsed).
        """
        a = self._FakeObj("connector", "zoom", GitStatuses.MODIFIED)
        b = self._FakeObj("connector", "okta", GitStatuses.ADDED)

        result = ConnectorAwareInitializer._dedup_by_object_id({a, b})

        assert len(result) == 2
        assert {o.object_id for o in result} == {"zoom", "okta"}

    def test_dedup_distinguishes_by_content_type(self):
        """
        Given: Two objects sharing an object_id but with different content types
            (e.g. an Integration and a Connector both named "zoom").
        When: _dedup_by_object_id runs.
        Then: Both are kept because they are different content items.
        """
        integration = self._FakeObj("integration", "zoom", GitStatuses.MODIFIED)
        connector = self._FakeObj("connector", "zoom", GitStatuses.ADDED)

        result = ConnectorAwareInitializer._dedup_by_object_id({integration, connector})

        assert len(result) == 2


# ============================================================
# ConnectorAwareInitializer - filter / gather behavior
# ============================================================


class TestConnectorAwareInitializerFilter:
    """Tests for the post-collection filter inside
    :py:meth:`ConnectorAwareInitializer.gather_objects_to_run_on`.
    """

    @staticmethod
    def _run_filter(objects):
        """Replay the inline post-filter block from gather_objects_to_run_on.

        We mirror the logic rather than calling the full method so the test
        is independent of file-collection / git-diff plumbing.
        """
        from demisto_sdk.commands.content_graph.objects.connector import Connector

        filtered_connectors = set()
        for obj in objects:
            if isinstance(obj, Connector):
                if obj.xsoar_handlers:
                    filtered_connectors.add(obj)
        return filtered_connectors

    def test_connector_with_xsoar_handler_is_kept(self):
        """
        Given: A connector with at least one XSOAR handler.
        When: The post-collection filter runs.
        Then: The connector is kept (original happy-path behavior).
        """
        connector = create_connector_object()
        assert connector.xsoar_handlers, "fixture must have an XSOAR handler"

        kept = self._run_filter({connector})

        assert kept == {connector}

    def test_connector_with_no_xsoar_handlers_is_dropped(
        self,
    ):
        """
        Given: A connector with NO XSOAR handlers.
        When: The post-collection filter runs.
        Then: The connector is dropped (non-XSOAR connectors are out of
              scope for cross-matching).
        """
        connector = create_connector_object()
        connector.handlers = []

        kept = self._run_filter({connector})

        assert kept == set()


class TestConnectorHandlerIgnoreFiltering:
    """Tests for filtering ignored connector handler/serializer results.

    Covers:
    * ``ConnectorsValidator.resolve_ignore_key_from_path`` path -> key mapping.
    * ``ConnectorsValidator.is_error_ignored`` honoring ALWAYS_RUN_ON_ERROR_CODE.
    * ``ValidateManager.filter_validation_results`` per-handler / per-serializer
      filtering, including keeping non-ignored handlers and honoring the
      content object's main ``ignored_errors`` list.
    """

    @staticmethod
    def _make_result(
        error_code: str,
        path: Optional[Path],
        ignored_map: Dict[str, List[str]],
        main_ignored: Optional[List[str]] = None,
        related_file_type: Optional[list] = None,
    ):
        """Build a lightweight stand-in for a ValidationResult.

        ``filter_validation_results`` only reads
        ``result.validator.error_code``, ``result.validator.related_file_type``,
        ``result.path``, ``result.content_object.ignored_errors`` and
        ``result.content_object.is_handler_error_ignored(error_code, path)``, so
        a SimpleNamespace fake avoids the cost of constructing a full connector
        fixture. The fake reuses the real ``Connector.resolve_handler_ignore_key``
        logic to map paths to ``.connector-ignore`` keys.
        """
        from types import SimpleNamespace

        from demisto_sdk.commands.content_graph.objects.connector import Connector

        def is_handler_error_ignored(code: str, file_path: Optional[Path]) -> bool:
            key = Connector.resolve_handler_ignore_key(file_path)
            if key is None:
                return False
            return code in ignored_map.get(key, [])

        return SimpleNamespace(
            validator=SimpleNamespace(
                error_code=error_code,
                related_file_type=related_file_type,
            ),
            path=path,
            content_object=SimpleNamespace(
                ignored_errors=main_ignored or [],
                is_handler_error_ignored=is_handler_error_ignored,
            ),
        )

    @pytest.mark.parametrize(
        "path, expected_key",
        [
            (
                Path(
                    "/repo/connectors/foo/components/handlers/my_handler/handler.yaml"
                ),
                "my_handler/handler.yaml",
            ),
            (
                Path(
                    "/repo/connectors/foo/components/handlers/my_handler/serializer.yaml"
                ),
                "my_handler/serializer.yaml",
            ),
            (Path("/repo/connectors/foo/connector.yaml"), None),
            (Path("/repo/connectors/foo/components/handlers/my_handler"), None),
            (None, None),
        ],
    )
    def test_resolve_handler_ignore_key(self, path, expected_key):
        """
        Given: A ValidationResult path.
        When: Connector.resolve_handler_ignore_key maps it to a .connector-ignore key.
        Then: Handler/serializer paths yield '<folder>/handler.yaml' /
              '<folder>/serializer.yaml'; anything else yields None.
        """
        from demisto_sdk.commands.content_graph.objects.connector import Connector

        assert Connector.resolve_handler_ignore_key(path) == expected_key

    def test_is_error_ignored_respects_always_run_on_error_code(self, mocker):
        """
        Given: An error code that is in ALWAYS_RUN_ON_ERROR_CODE and is also
               listed in the connector's ignore file for a handler.
        When: ConnectorsValidator.is_error_ignored is called.
        Then: It returns False - the error must always run.
        """
        from demisto_sdk.commands.common.constants import ALWAYS_RUN_ON_ERROR_CODE
        from demisto_sdk.commands.content_graph.parsers.related_files import (
            RelatedFileType,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO155_is_handler_module_xsoar import (
            IsHandlerModuleXsoarValidator,
        )

        validator = IsHandlerModuleXsoarValidator()
        always_run_code = ALWAYS_RUN_ON_ERROR_CODE[0]

        content_item = mocker.Mock()
        content_item.get_ignored_errors.return_value = [always_run_code]

        assert (
            validator.is_error_ignored(
                always_run_code,
                [always_run_code],
                content_item,
                [RelatedFileType.CONNECTOR_HANDLER],
            )
            is False
        )

    def test_should_run_preflight_not_suppressed_when_only_some_handlers_ignore(
        self, mocker
    ):
        """
        Given: A connector with three handlers (a, b, c). Only handler ``c``'s
               ``.connector-ignore`` ignores CO130 (via
               ``[file:c/serializer.yaml]``); handlers ``a`` and ``b`` do NOT.
        When: ``ConnectorsValidator.is_error_ignored`` runs as part of the
              ``should_run`` preflight for a per-handler validator with
              ``related_file_type = [CONNECTOR_HANDLER, CONNECTOR_SERIALIZER]``.
        Then: It returns ``False`` — the validator MUST still run so that
              ``ValidateManager.filter_validation_results`` can drop only the
              individual result for ``c`` while keeping ``a`` and ``b``.

        Regression: the prior "any-match wins" behaviour returned ``True`` as
        soon as any single handler ignored the code, which short-circuited
        ``should_run`` for the whole connector and silenced legitimate CO130
        defects on ``a`` and ``b``. Fix #1 requires universal suppression
        (every handler dir must ignore) before the preflight blocks the run;
        per-handler suppression is the job of ``filter_validation_results``,
        which is exercised separately below.

        This test drives ``is_error_ignored`` directly (the preflight seam)
        rather than the per-result filter — the two chains are independent
        and both must be covered.
        """
        from types import SimpleNamespace

        from demisto_sdk.commands.content_graph.parsers.related_files import (
            RelatedFileType,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        validator = IsValidFetchValidator()

        # Stand-in handler_files: each carries a ``_handler_dir_name`` so
        # ``_resolve_ignore_file_keys`` expands the handler/serializer types
        # into one key per dir — the shape ``obtain_invalid_content_items``
        # would see for a real 3-handler connector.
        handler_files = [
            SimpleNamespace(_handler_dir_name="a"),
            SimpleNamespace(_handler_dir_name="b"),
            SimpleNamespace(_handler_dir_name="c"),
        ]
        ignored_per_key = {
            "c/serializer.yaml": ["CO130"],
        }
        content_item = SimpleNamespace(
            handler_files=handler_files,
            get_ignored_errors=lambda key: ignored_per_key.get(key, []),
        )

        assert (
            validator.is_error_ignored(
                "CO130",
                ["CO130"],
                content_item,
                [
                    RelatedFileType.CONNECTOR_HANDLER,
                    RelatedFileType.CONNECTOR_SERIALIZER,
                ],
            )
            is False
        )

    def test_should_run_preflight_suppressed_when_every_handler_ignores(self, mocker):
        """
        Given: A connector with three handlers (a, b, c), and EVERY handler's
               ``.connector-ignore`` ignores CO130 via its
               ``<h>/serializer.yaml`` key.
        When: ``ConnectorsValidator.is_error_ignored`` runs as part of the
              ``should_run`` preflight.
        Then: It returns ``True`` — universal suppression IS a legitimate
              reason to short-circuit the validator, because no per-result
              output would survive ``filter_validation_results`` anyway.
        """
        from types import SimpleNamespace

        from demisto_sdk.commands.content_graph.parsers.related_files import (
            RelatedFileType,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        validator = IsValidFetchValidator()

        handler_files = [
            SimpleNamespace(_handler_dir_name="a"),
            SimpleNamespace(_handler_dir_name="b"),
            SimpleNamespace(_handler_dir_name="c"),
        ]
        ignored_per_key = {
            "a/serializer.yaml": ["CO130"],
            "b/serializer.yaml": ["CO130"],
            "c/serializer.yaml": ["CO130"],
            # handler.yaml keys not needed — CONNECTOR_SERIALIZER alone
            # already delivers a fully-covered expansion; the loop returns
            # True on the first type whose expansion is fully covered.
        }
        content_item = SimpleNamespace(
            handler_files=handler_files,
            get_ignored_errors=lambda key: ignored_per_key.get(key, []),
        )

        assert (
            validator.is_error_ignored(
                "CO130",
                ["CO130"],
                content_item,
                [RelatedFileType.CONNECTOR_SERIALIZER],
            )
            is True
        )

    def test_should_run_preflight_single_file_type_unchanged(self, mocker):
        """
        Given: A per-configurations-file validator (``related_file_type``
               contains ``CONNECTOR_CONFIGURATIONS``) whose code is ignored
               under ``[file:configurations.yaml]``.
        When: ``is_error_ignored`` runs.
        Then: It returns ``True`` — single-file types (which resolve to
              exactly one key) keep the pre-existing single-match semantics.
              This proves the per-handler AND-semantics fix did not
              regress single-file types.
        """
        from types import SimpleNamespace

        from demisto_sdk.commands.content_graph.parsers.related_files import (
            RelatedFileType,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        validator = IsValidFetchValidator()

        ignored_per_key = {"configurations.yaml": ["CO130"]}
        content_item = SimpleNamespace(
            handler_files=[],
            get_ignored_errors=lambda key: ignored_per_key.get(key, []),
        )

        assert (
            validator.is_error_ignored(
                "CO130",
                ["CO130"],
                content_item,
                [RelatedFileType.CONNECTOR_CONFIGURATIONS],
            )
            is True
        )

    def test_filter_keeps_non_ignored_handler_and_drops_ignored_one(self, mocker):
        """
        Given: Two per-handler results (handler_a and handler_b) for the same
               error code, where only handler_a is ignored in .connector-ignore.
        When: filter_validation_results runs.
        Then: handler_a's result is dropped and handler_b's result is kept.
        """
        manager = get_validate_manager(mocker)

        ignored_map = {"handler_a/handler.yaml": ["CO155"]}
        result_a = self._make_result(
            "CO155",
            Path("/repo/connectors/foo/components/handlers/handler_a/handler.yaml"),
            ignored_map,
            related_file_type=[RelatedFileType.CONNECTOR_HANDLER],
        )
        result_b = self._make_result(
            "CO155",
            Path("/repo/connectors/foo/components/handlers/handler_b/handler.yaml"),
            ignored_map,
            related_file_type=[RelatedFileType.CONNECTOR_HANDLER],
        )

        filtered = manager.filter_validation_results([result_a, result_b])

        assert result_a not in filtered
        assert result_b in filtered

    def test_filter_drops_ignored_serializer(self, mocker):
        """
        Given: A per-serializer result whose error code is ignored via the
               '<folder>/serializer.yaml' key.
        When: filter_validation_results runs.
        Then: The serializer result is dropped.
        """
        manager = get_validate_manager(mocker)

        ignored_map = {"handler_a/serializer.yaml": ["CO155"]}
        result = self._make_result(
            "CO155",
            Path("/repo/connectors/foo/components/handlers/handler_a/serializer.yaml"),
            ignored_map,
            related_file_type=[RelatedFileType.CONNECTOR_SERIALIZER],
        )

        filtered = manager.filter_validation_results([result])

        assert filtered == []

    def test_filter_drops_result_ignored_via_main_ignored_errors(self, mocker):
        """
        Given: A result whose error code is in the content object's main
               ``ignored_errors`` list (the pre-existing filter behavior).
        When: filter_validation_results runs.
        Then: The result is dropped.
        """
        manager = get_validate_manager(mocker)

        result = self._make_result(
            "GR107",
            Path("/repo/connectors/foo/connector.yaml"),
            {},
            main_ignored=["GR107"],
        )

        filtered = manager.filter_validation_results([result])

        assert filtered == []

    def test_filter_keeps_result_when_no_ignore_file(self, mocker):
        """
        Given: A per-handler result but the connector has no matching ignore
               entry (empty ignore map, mimicking a missing .connector-ignore).
        When: filter_validation_results runs.
        Then: The result is kept.
        """
        manager = get_validate_manager(mocker)

        result = self._make_result(
            "CO155",
            Path("/repo/connectors/foo/components/handlers/handler_a/handler.yaml"),
            {},
            related_file_type=[RelatedFileType.CONNECTOR_HANDLER],
        )

        filtered = manager.filter_validation_results([result])

        assert result in filtered

    def test_filter_keeps_non_handler_result_not_in_main_ignored(self, mocker):
        """
        Given: A result whose path is not a handler/serializer file and whose
               error code is not in the main ``ignored_errors`` list.
        When: filter_validation_results runs.
        Then: The result is left untouched (kept) - the handler/serializer key
              lookup does not apply to non-handler paths.
        """
        manager = get_validate_manager(mocker)

        result = self._make_result(
            "CO155",
            Path("/repo/connectors/foo/connector.yaml"),
            {"connector.yaml": ["CO155"]},
        )

        filtered = manager.filter_validation_results([result])

        assert result in filtered

    def test_filter_drops_result_ignored_via_pack_level_ignore(self, mocker):
        """
        Given: A ContentItem result whose error code (e.g. GR109) is listed
               under the pack's ``[pack]`` section of ``.pack-ignore`` (exposed
               as ``in_pack.pack_level_ignored_errors``), and NOT in the item's
               own per-file ``ignored_errors``.
        When: filter_validation_results runs (the post-hoc path taken for
              ``ALWAYS_RUN_ON_ERROR_CODE`` codes such as GR107/GR109).
        Then: The result is dropped - the pack-level ignore is honored.
        """
        from types import SimpleNamespace

        manager = get_validate_manager(mocker)

        pack = SimpleNamespace(pack_level_ignored_errors=["GR109"])
        result = SimpleNamespace(
            validator=SimpleNamespace(error_code="GR109", related_file_type=None),
            path=Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml"),
            content_object=SimpleNamespace(ignored_errors=[], in_pack=pack),
        )

        filtered = manager.filter_validation_results([result])

        assert filtered == []

    def test_filter_drops_result_when_content_object_is_pack_with_pack_level_ignore(
        self, mocker
    ):
        """
        Given: A result whose content_object IS the ``Pack`` itself (as with
               PA-validators), and the code is listed in the pack's
               ``pack_level_ignored_errors``.
        When: filter_validation_results runs.
        Then: The result is dropped - the duck-typed pack lookup uses
              ``pack_level_ignored_errors`` directly on the content_object.
        """
        from types import SimpleNamespace

        manager = get_validate_manager(mocker)

        pack = SimpleNamespace(
            ignored_errors=[],
            pack_level_ignored_errors=["GR107"],
        )
        result = SimpleNamespace(
            validator=SimpleNamespace(error_code="GR107", related_file_type=None),
            path=Path("/repo/Packs/Foo/pack_metadata.json"),
            content_object=pack,
        )

        filtered = manager.filter_validation_results([result])

        assert filtered == []

    def test_filter_keeps_result_when_neither_file_nor_pack_ignore_match(self, mocker):
        """
        Given: A result whose error code is neither in the content item's
               per-file ``ignored_errors`` nor in the pack's
               ``pack_level_ignored_errors``.
        When: filter_validation_results runs.
        Then: The result is kept.
        """
        from types import SimpleNamespace

        manager = get_validate_manager(mocker)

        pack = SimpleNamespace(pack_level_ignored_errors=["PB100"])
        result = SimpleNamespace(
            validator=SimpleNamespace(error_code="GR109", related_file_type=None),
            path=Path("/repo/Packs/Foo/Integrations/Foo/Foo.yml"),
            content_object=SimpleNamespace(ignored_errors=["BA101"], in_pack=pack),
        )

        filtered = manager.filter_validation_results([result])

        assert result in filtered


class TestImplicitGraphInitialization:
    """Tests for the connectors-flow graph initialization.

    The connectors flow resolves handler<->integration links through the
    content graph *during object collection*, before any validator runs, so it
    cannot rely on the lazy ``BaseValidator.graph`` property. These tests pin:

    * ``ConnectorAwareInitializer`` building the graph before cross-matching.
    * Graph initialization staying scoped to the connectors flow - the plain
      ``Initializer`` must not trigger it.
    * ``BaseValidator.ensure_graph_initialized`` being idempotent - it never
      rebuilds when the graph interface is already wired (the connect-only
      ``--graph`` CI path).
    """

    def teardown_method(self):
        # Never leak a wired graph interface between tests.
        BaseValidator.graph_interface = None

    def test_connectors_initializer_builds_graph_before_cross_matching(self, mocker):
        """The graph must be initialized *before* _cross_match_and_expand runs,
        since the expand phases query it to resolve handler links."""
        call_order = []

        ensure_spy = mocker.patch.object(
            BaseValidator,
            "ensure_graph_initialized",
            side_effect=lambda: call_order.append("ensure_graph"),
        )
        cross_match_spy = mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=lambda *a, **kw: call_order.append("cross_match") or set(),
        )
        mocker.patch.object(
            Initializer, "gather_objects_to_run_on", return_value=(set(), set())
        )

        initializer = ConnectorAwareInitializer(execution_mode=ExecutionMode.ALL_FILES)
        initializer.gather_objects_to_run_on()

        ensure_spy.assert_called_once()
        cross_match_spy.assert_called_once()
        assert call_order == ["ensure_graph", "cross_match"]

    def test_graph_is_closed_when_cross_matching_fails(self, mocker):
        """ValidateManager closes the graph in run_validations(), which never
        runs if collection raises. The connectors initializer must close it
        itself so a mid-collection failure does not leak the Neo4j driver."""
        fake_graph = mocker.Mock()
        mocker.patch.object(
            BaseValidator,
            "ensure_graph_initialized",
            side_effect=lambda: setattr(BaseValidator, "graph_interface", fake_graph),
        )
        mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=RuntimeError("boom"),
        )
        mocker.patch.object(
            Initializer, "gather_objects_to_run_on", return_value=(set(), set())
        )

        initializer = ConnectorAwareInitializer(execution_mode=ExecutionMode.ALL_FILES)

        with pytest.raises(RuntimeError, match="boom"):
            initializer.gather_objects_to_run_on()

        fake_graph.close.assert_called_once()
        assert BaseValidator.graph_interface is None

    def test_caller_owned_graph_is_not_closed_when_cross_matching_fails(self, mocker):
        """When the graph interface was already wired by the caller (e.g.
        connect-only via --graph in CI), the initializer must not close it on
        failure - ValidateManager owns it and closes it in run_validations()."""
        caller_graph = mocker.Mock()
        BaseValidator.graph_interface = caller_graph
        mocker.patch.object(
            ConnectorAwareInitializer,
            "_cross_match_and_expand",
            side_effect=RuntimeError("boom"),
        )
        mocker.patch.object(
            Initializer, "gather_objects_to_run_on", return_value=(set(), set())
        )

        initializer = ConnectorAwareInitializer(execution_mode=ExecutionMode.ALL_FILES)

        with pytest.raises(RuntimeError, match="boom"):
            initializer.gather_objects_to_run_on()

        caller_graph.close.assert_not_called()
        assert BaseValidator.graph_interface is caller_graph

    def test_plain_initializer_does_not_build_graph(self, mocker):
        """Graph initialization is scoped to the connectors flow. The regular
        validate flow keeps building the graph lazily, on first validator
        access - collecting objects must not trigger a build."""
        ensure_spy = mocker.patch.object(BaseValidator, "ensure_graph_initialized")
        mocker.patch.object(
            Initializer, "get_files_using_git", return_value=(set(), set(), set())
        )

        Initializer(execution_mode=ExecutionMode.USE_GIT).gather_objects_to_run_on()

        ensure_spy.assert_not_called()

    def test_ensure_graph_initialized_is_idempotent(self, mocker):
        """When the graph interface is already wired (e.g. connect-only via
        --graph), ensure_graph_initialized must NOT rebuild the graph."""
        sentinel = object()
        BaseValidator.graph_interface = sentinel  # type: ignore[assignment]

        update_spy = mocker.patch(
            "demisto_sdk.commands.validate.validators.base_validator.update_content_graph"
        )
        interface_spy = mocker.patch(
            "demisto_sdk.commands.validate.validators.base_validator.ContentGraphInterface"
        )

        result = BaseValidator.ensure_graph_initialized()

        assert result is sentinel
        update_spy.assert_not_called()
        interface_spy.assert_not_called()

    def test_ensure_graph_initialized_builds_when_missing(self, mocker):
        """When no graph interface is wired, ensure_graph_initialized builds and
        updates it via the shared update_content_graph path (the same one used
        for regular and private content)."""
        BaseValidator.graph_interface = None

        fake_interface = object()
        interface_spy = mocker.patch(
            "demisto_sdk.commands.validate.validators.base_validator.ContentGraphInterface",
            return_value=fake_interface,
        )
        update_spy = mocker.patch(
            "demisto_sdk.commands.validate.validators.base_validator.update_content_graph"
        )

        result = BaseValidator.ensure_graph_initialized()

        assert result is fake_interface
        interface_spy.assert_called_once()
        update_spy.assert_called_once()

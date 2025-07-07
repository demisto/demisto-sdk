import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest
import toml
from more_itertools import map_reduce
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.constants import (
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
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.tests.test_tools import (
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

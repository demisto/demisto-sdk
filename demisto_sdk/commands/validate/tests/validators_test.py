import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, GitStatuses
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.tests.test_tools import create_integration_object
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.commands.validate.validation_results import ResultWriter
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name_all_statuses import (
    IDNameAllStatusesValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC100_breaking_backwards_subtype import (
    BreakingBackwardsSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA108_pack_metadata_name_not_valid import (
    PackMetadataNameValidator,
)
from TestSuite.test_tools import str_in_call_args_list

INTEGRATION = create_integration_object()
INTEGRATION.path = Path(
    f"{CONTENT_PATH}/Packs/pack_0/Integrations/integration_0/integration_0.yml"
)


def get_validate_manager(mocker):
    validation_results = ResultWriter()
    config_reader = ConfigReader(category_to_run="test")
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
def test_filter_validators(mocker, validations_to_run, sub_classes, expected_results):
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
    validate_manager.configured_validations.validations_to_run = validations_to_run
    with patch.object(BaseValidator, "__subclasses__", return_value=sub_classes):
        results = validate_manager.filter_validators()
        assert results == expected_results


@pytest.mark.parametrize(
    "category_to_run, use_git, config_file_content, expected_results, ignore_support_level",
    [
        (
            None,
            True,
            {"use_git": {"select": ["BA101", "BC100", "PA108"]}},
            ConfiguredValidations(["BA101", "BC100", "PA108"], [], [], {}),
            False,
        ),
        (
            "custom_category",
            True,
            {
                "ignorable_errors": ["BA101"],
                "custom_category": {
                    "select": ["BA101", "BC100", "PA108"],
                },
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            ConfiguredValidations(["BA101", "BC100", "PA108"], [], ["BA101"], {}),
            False,
        ),
        (
            None,
            False,
            {"validate_all": {"select": ["BA101", "BC100", "PA108"]}},
            ConfiguredValidations(["BA101", "BC100", "PA108"], [], [], {}),
            False,
        ),
        (
            None,
            True,
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
        ),
        (
            None,
            True,
            {
                "support_level": {"community": {"ignore": ["BA101", "BC100", "PA108"]}},
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            ConfiguredValidations(["TE105", "TE106", "TE107"], [], [], {}),
            True,
        ),
    ],
)
def test_gather_validations_to_run(
    mocker,
    category_to_run,
    use_git,
    config_file_content,
    expected_results,
    ignore_support_level,
):
    """
    Given
    a category_to_run, a use_git flag, a config file content, and a ignore_support_level flag.
        - Case 1: No category to run, use_git flag set to True, config file content with only use_git.select section, and ignore_support_level set to False.
        - Case 2: A custom category to run, use_git flag set to True, config file content with use_git.select, and custom_category with both ignorable_errors and select sections, and ignore_support_level set to False.
        - Case 3: No category to run, use_git flag set to False, config file content with validate_all.select section, and ignore_support_level set to False.
        - Case 4: No category to run, use_git flag set to True, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to False.
        - Case 5: No category to run, use_git flag set to True, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to True.
    When
    - Calling the gather_validations_to_run function.
    Then
        - Case 1: Make sure the retrieved results contains only use_git.select results
        - Case 2: Make sure the retrieved results contains the custom category results and ignored the use_git results.
        - Case 3: Make sure the retrieved results contains the validate_all results.
        - Case 4: Make sure the retrieved results contains both the support level and the use_git sections.
        - Case 5: Make sure the retrieved results contains only the use_git section.
    """
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader(category_to_run=category_to_run)
    results: ConfiguredValidations = config_reader.gather_validations_to_run(
        use_git=use_git, ignore_support_level=ignore_support_level
    )
    assert results.validations_to_run == expected_results.validations_to_run
    assert results.ignorable_errors == expected_results.ignorable_errors
    assert results.only_throw_warnings == expected_results.only_throw_warnings
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
            },
        ),
        (
            [],
            [],
            {
                "validations": [],
                "fixed validations": [],
                "invalid content items": [],
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
            0,
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
            0,
            1,
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
            1,
            1,
            ["BC100"],
            ["BA101"],
        ),
    ],
)
def test_post_results(
    mocker,
    only_throw_warnings,
    results,
    expected_exit_code,
    expected_warnings_call_count,
    expected_error_call_count,
    expected_error_code_in_warnings,
    expected_error_code_in_errors,
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
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    validation_results = ResultWriter()
    validation_results.validation_results = results
    exit_code = validation_results.post_results(only_throw_warning=only_throw_warnings)
    assert exit_code == expected_exit_code
    assert logger_warning.call_count == expected_warnings_call_count
    assert logger_error.call_count == expected_error_call_count
    for expected_error_code_in_warning in expected_error_code_in_warnings:
        assert str_in_call_args_list(
            logger_warning.call_args_list, expected_error_code_in_warning
        )
    for expected_error_code_in_error in expected_error_code_in_errors:
        assert str_in_call_args_list(
            logger_error.call_args_list, expected_error_code_in_error
        )


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
    assert expected_results == validator.should_run(INTEGRATION, [], {})


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
    initializer = Initializer(file_path=pack.path)
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
    loaded_files_set = initializer.load_files([pack.path])
    assert len(loaded_files_set) == 1
    assert loaded_files_set.pop() == Path(pack.path)


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

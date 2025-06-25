import pytest

from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.pack_content_items import (
    PackContentItems,
)
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.tests.test_tools import (
    create_playbook_object,
    create_test_use_case_file_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.PB_validators.PB100_is_no_rolename import (
    IsNoRolenameValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB101_is_playbook_has_unreachable_condition import (
    IsAskConditionHasUnreachableConditionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB103_does_playbook_have_unconnected_tasks import (
    ERROR_MSG,
    DoesPlaybookHaveUnconnectedTasks,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB104_deprecated_description import (
    DeprecatedDescriptionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB105_playbook_delete_context_all import (
    PlaybookDeleteContextAllValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB106_is_playbook_using_an_instance import (
    IsPlayBookUsingAnInstanceValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB108_is_valid_task_id import (
    IsValidTaskIdValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB109_is_taskid_equals_id import (
    IsTaskidDifferentFromidValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB114_playbook_quiet_mode import (
    PlaybookQuietModeValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB115_is_tasks_quiet_mode import (
    IsTasksQuietModeValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB116_is_stopping_on_error import (
    IsStoppingOnErrorValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import (
    IsInputKeyNotInTasksValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB119_check_inputs_used import (
    CheckInputsUsedExist,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB121_is_correct_value_references_interface import (
    IsCorrectValueReferencesInterface,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB122_does_playbook_have_unhandled_conditions import (
    DoesPlaybookHaveUnhandledConditionsValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB123_is_conditional_task_has_unhandled_reply_options import (
    IsAskConditionHasUnhandledReplyOptionsValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB124_is_playbook_contain_unhandled_script_condition_branches import (
    IsPlaybookContainUnhandledScriptConditionBranchesValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB125_playbook_only_default_next import (
    PlaybookOnlyDefaultNextValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB126_is_default_not_only_condition import (
    IsDefaultNotOnlyConditionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB127_marketplace_keys_have_default_value import (
    MarketplaceKeysHaveDefaultValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB130_is_silent_playbook import (
    IsSilentPlaybookValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB131_is_silent_playbook_relationships import (
    IsSilentPlaybookRelationshipsValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB132_no_readme_for_silent_playbook import (
    NoReadmeForSilentPlaybook,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB133_playbook_tests_exist import (
    PlaybookTestsExistValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB134_playbook_test_use_case_config import (
    PlaybookTestUseCaseConfigValidator,
)
from TestSuite.pack import Pack as TestSuitePack
from TestSuite.repo import Repo


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {"first_input": "inputs.input_name1"},
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {
                        "first_input": "inputs.input_name1",
                        "second_input": "inputs.input_name2",
                    },
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name2", "value": "input_value2"}],
                    {"first_input": "inputs.input_name1"},
                ],
            ),
            "The playbook 'Detonate File - JoeSecurity V2' contains the following inputs that are not used in any of its tasks: input_name2",
        ),
    ],
)
def test_obtain_invalid_content_items_all_inputs_in_use(content_item, expected_result):
    """
    Given:
    - A playbook with inputs in some tasks and inputs defined in the inputs section
        Case 1: All inputs defined in the inputs section are in use in the playbook
        Case 2: All inputs defined in the inputs section are in use in the playbook but not all inputs in use are defined in the inputs section
        Case 3: All inputs defined in the inputs section are not in use in the playbook

    When:
    - Validating the playbook

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is valid since all inputs defined in the inputs section are in use in the playbook
        Case 3: The playbook is invalid
    """
    result = IsInputKeyNotInTasksValidator().obtain_invalid_content_items(
        [content_item]
    )

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


def test_using_input_not_provided():
    """
    Given:
        inputs 2 and
    When:
        using input 3
    Then:
        Will fail on input 3 (Comments, File, ReportFileType, Systems, Timeout are from the default test config)

    """
    playbook = create_playbook_object(
        paths=["inputs", "tasks.0.task.key"],
        values=[
            [
                {"key": "input_name1", "value": "input_value1"},
                {"key": "input_name2", "value": "input_value2"},
            ],
            {"first_input": "inputs.input_name1", "another 1 ": "inputs.input_name3"},
        ],
    )
    result = CheckInputsUsedExist().obtain_invalid_content_items([playbook])
    assert len(result) == 1
    assert (
        result[0].message
        == "Inputs [Comments, File, ReportFileType, Systems, Timeout, input_name3] were used but not provided for this playbook."
    )


def test_playbook_quiet_mode_regular_playbook_pass():
    """
    Given:
        A regular pb with quiet mode false
    When:
        Calling Validate
    Then:
        The validation shouldnt fail

    """
    playbook = create_playbook_object(["quiet"], [False])
    assert PlaybookQuietModeValidator().obtain_invalid_content_items([playbook]) == []


def test_indicator_pb_must_be_quiet():
    """
    Given:
        A pb with queryEntity indicators
    When:
        not in quiet mode
    Then:
        The validation should fail

    """
    playbook = create_playbook_object(
        ["inputs", "quiet"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
            False,
        ],
    )
    result = PlaybookQuietModeValidator().obtain_invalid_content_items([playbook])
    assert len(result) == 1
    assert (
        result[0].message
        == "Playbooks with a playbookInputQuery for indicators should be on quiet mode."
    )


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(),
            [],
        ),
        (
            create_playbook_object(
                paths=["rolename"],
                values=[[]],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["rolename"],
                values=[["Administrator"]],
            ),
            "The playbook 'Detonate File - JoeSecurity V2' can not have a rolename, please remove the field.",
        ),
    ],
)
def test_is_no_rolename(content_item, expected_result):
    """
    Given:
    - A playbook with id
        Case 1: The playbook has only id and no rolename.
        Case 2: The playbook has id and an empty rolename.
        Case 3: The playbook has id and rolename.

    When:
    - Validating the playbook

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is invalid
        Case 3: The playbook is invalid
    """
    result = IsNoRolenameValidator().obtain_invalid_content_items([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Deprecated. Use PLAYBOOK_NAME instead."],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Deprecated. REASON No available replacement."],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Not a valid description"],
            ),
            "The deprecated playbook 'Detonate File - JoeSecurity V2' has invalid description.\nThe description of "
            'all deprecated playbooks should follow one of the formats:\n1. "Deprecated. Use PLAYBOOK_NAME '
            'instead."\n2. "Deprecated. REASON No available replacement."',
        ),
    ],
)
def test_is_deprecated_with_invalid_description(content_item, expected_result):
    """
    Given:
    - A playbook with id
        Case 1: The playbook is deprecated and has valid description.
        Case 2: The playbook is deprecated and has valid description.
        Case 3: The playbook is deprecated and has invalid description.

    When:
    - calling DeprecatedDescriptionValidator.obtain_invalid_content_items.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is valid
        Case 3: The playbook is invalid
    """
    result = DeprecatedDescriptionValidator().obtain_invalid_content_items(
        [content_item]
    )

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


def test_does_playbook_have_unhandled_conditions__valid():
    """
    Given: A playbook with condition tasks.
    When:
    - All condition options are handled properly.
    Then:
    - Ensure the validation does not fail.
    """
    playbook = create_playbook_object()
    playbook.tasks = {
        "VALID__NOT_A_CONDITION": TaskConfig(
            id="valid_0",
            type="playbook",
            taskid="",
            task={"id": ""},
        ),
        "VALID__NO_CONDITIONS": TaskConfig(
            id="valid_1",
            type="condition",
            nexttasks={"yes": ["2"]},
            conditions=[],
            taskid="",
            task={"id": ""},
        ),
        "VALID__MULTIPLE_OPTIONS_AND_#DEFAULT#_NEXTTASK": TaskConfig(
            id="valid_2",
            type="condition",
            nexttasks={"#default#": ["3"], "yes": ["4"], "no": ["5"]},
            conditions=[{"label": "yes"}, {"label": "no"}],
            taskid="",
            task={"id": ""},
        ),
    }
    errors = (
        DoesPlaybookHaveUnhandledConditionsValidator().obtain_invalid_content_items(
            [playbook]
        )
    )
    assert len(errors) == 0


def test_does_playbook_have_unhandled_conditions__invalid():
    """
    Given: A playbook with condition tasks.
    When:
    - Some condition option are unhandled.
    Then:
    - Ensure the validation fails on the expected errors.
    """
    playbook = create_playbook_object()
    playbook.tasks = {
        "INVALID__LABEL_WITHOUT_NEXTTASK": TaskConfig(
            id="invalid_0",
            type="condition",
            nexttasks={},
            conditions=[{"label": "oh"}],
            taskid="",
            task={"id": ""},
        ),
        "INVALID__NEXTTASK_WITHOUT_LABEL": TaskConfig(
            id="invalid_1",
            type="condition",
            nexttasks={"yes": ["4"], "oh": ["3"]},
            conditions=[{"label": "yes"}],
            taskid="",
            task={"id": ""},
        ),
        "INVALID__MULTIPLE_HANDLED_AND_UNHANDLED_CONDITIONS": TaskConfig(
            id="invalid_2",
            type="condition",
            nexttasks={"#default#": ["3"], "yes": ["4"], "no": ["5"], "hi": ["6"]},
            conditions=[{"label": "yes"}, {"label": "no"}, {"label": "bye"}],
            taskid="",
            task={"id": ""},
        ),
    }
    errors = (
        DoesPlaybookHaveUnhandledConditionsValidator().obtain_invalid_content_items(
            [playbook]
        )
    )
    assert len(errors) == len(playbook.tasks)
    assert any(
        "ID: invalid_2" in error.message
        and "HI" in error.message
        and "BYE" in error.message
        for error in errors
    )


def test_IsAskConditionHasUnreachableConditionValidator():
    playbook = create_playbook_object()
    assert not IsAskConditionHasUnreachableConditionValidator().obtain_invalid_content_items(
        [playbook]
    )
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"], "yes": ["2"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert (
        IsAskConditionHasUnreachableConditionValidator().obtain_invalid_content_items(
            [playbook]
        )
    )


def test_IsAskConditionHasUnhandledReplyOptionsValidator():
    playbook = create_playbook_object()
    assert not IsAskConditionHasUnhandledReplyOptionsValidator().obtain_invalid_content_items(
        [playbook]
    )
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert (
        IsAskConditionHasUnhandledReplyOptionsValidator().obtain_invalid_content_items(
            [playbook]
        )
    )


def test_indicator_pb_must_stop_on_error():
    """
    Given: A pb with queryEntity indicators
    When: Playbook stops on error
    Then: Validation should pass
    """
    playbook = create_playbook_object(
        ["inputs"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
        ],
    )
    res = IsStoppingOnErrorValidator().obtain_invalid_content_items([playbook])
    assert len(res) == 0


def test_indicator_pb_must_stop_on_error_invalid():
    """
    Given: A pb with queryEntity indicators
    When: Playbook continues on error
    Then: Validation should fail
    """
    error_message = IsStoppingOnErrorValidator.error_message
    playbook = create_playbook_object(
        ["inputs", "tasks.0.continueonerror"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
            True,
        ],
    )
    res = IsStoppingOnErrorValidator().obtain_invalid_content_items([playbook])
    assert len(res) == 1
    bad_task = playbook.tasks
    assert res[0].message == error_message.format([bad_task.get("0")])


def test_IsTasksQuietModeValidator_fail_case():
    """
    Given:
    - A invalid playbook with tasks that "quietmode" field is 2
    - An invalid playbook to fix

    When:
    - calling IsTasksQuietModeValidator.obtain_invalid_content_items.
    - calling IsTasksQuietModeValidator.fix

    Then:
    - The playbook is invalid
    -The playbook becomes valid
    """
    playbook = create_playbook_object(
        ["inputs", "quiet", "tasks"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
            False,
            {
                "0": {
                    "id": "test fail task No1",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "quietmode": 2,
                },
                "1": {
                    "id": "test fail task No2",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "quietmode": 2,
                },
            },
        ],
        pack_info={},
    )
    validator = IsTasksQuietModeValidator()
    validate_res = validator.obtain_invalid_content_items([playbook])
    assert len(validate_res) == 1
    assert (
        (validate_res[0]).message
        == "Playbook 'Detonate File - JoeSecurity V2' contains tasks that are not in quiet mode (quietmode: 2) The tasks names is: 'test fail task No1, test fail task No2'."
    )
    fix_playbook = validator.fix(playbook).content_object
    assert len(validator.obtain_invalid_content_items([fix_playbook])) == 0


def test_IsTasksQuietModeValidator_pass_case():
    """
    Given:
    - A valid playbook with tasks that "quietmode" field is 1

    When:
    - calling IsTasksQuietModeValidator.obtain_invalid_content_items.
    - calling IsTasksQuietModeValidator.fix

    Then:
    - The playbook is valid
    - The playbook doesn't changed
    """
    playbook = create_playbook_object(
        ["inputs", "quiet", "tasks"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
            False,
            {
                "0": {
                    "id": "test task",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "quietmode": 1,
                }
            },
        ],
    )
    validator = IsTasksQuietModeValidator()
    assert len(validator.obtain_invalid_content_items([playbook])) == 0
    fix_playbook = validator.fix(playbook).content_object
    assert fix_playbook == playbook


def test_PB125_playbook_only_default_next_valid():
    """
    Given:
    - A default standard playbook.

    When:
    - calling PlaybookOnlyDefaultNextValidator.obtain_invalid_content_items.

    Then:
    - The results should be empty as expected without validation error results.
    """
    playbook = create_playbook_object()
    assert not PlaybookOnlyDefaultNextValidator().obtain_invalid_content_items(
        [playbook]
    )


def test_PB125_playbook_only_default_next_not_valid():
    """
    Given:
    - A playbook with a condition task with only a default nexttask.

    When:
    - calling PlaybookOnlyDefaultNextValidator.obtain_invalid_content_items.

    Then:
    - The results should contain a validation error object.
    """
    playbook = create_playbook_object(
        paths=["tasks"],
        values=[
            {
                "0": {
                    "id": "test task",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"#default#": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                }
            }
        ],
    )
    result = PlaybookOnlyDefaultNextValidator().obtain_invalid_content_items([playbook])
    assert result[0].message == (
        "Playbook has conditional tasks with an only default condition. Tasks IDs: ['0'].\n"
        "Please remove these tasks or add another non-default condition to these conditional tasks."
    )


def create_invalid_playbook(field: str):
    """Create an invalid playbook that has an invalid taskid or the 'id' under the 'task' field is invalid
    Args:
        - field str: which field to update taskid or task.id.
    Return:
        - a playbook object
    """
    playbook = create_playbook_object()
    tasks = playbook.tasks
    for task_id in tasks:
        task_obj = tasks[task_id]
        if field == "taskid":
            task_obj.taskid = task_obj.taskid + "1234"
        else:
            task_obj.task.id = task_obj.task.id + "1234"
        break
    return playbook


def test_IsValidTaskIdValidator(playbook):
    """
    Given:
    - A playbook
        Case 1: The playbook is valid.
        Case 2: The playbook isn't valid, it has invalid taskid.
        Case 3: The playbook isn't valid, the 'id' under the 'task' field is invalid.

    When:
    - calling IsValidTaskIdValidator.obtain_invalid_content_items.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is invalid
        Case 3: The playbook is invalid
    """
    # Case 1
    playbook_valid = create_playbook_object()
    results_valid = IsValidTaskIdValidator().obtain_invalid_content_items(
        [playbook_valid]
    )

    # Case 2
    playbook_invalid_taskid = create_invalid_playbook("taskid")
    results_invalid_taskid = IsValidTaskIdValidator().obtain_invalid_content_items(
        [playbook_invalid_taskid]
    )

    # Case 3
    playbook_invalid_id = create_invalid_playbook("id")
    results_invalid_id = IsValidTaskIdValidator().obtain_invalid_content_items(
        [playbook_invalid_id]
    )

    assert not results_valid
    assert results_invalid_taskid
    assert results_invalid_id


def test_PlaybookDeleteContextAllValidator():
    """
    Given:
    - A playbook with tasks.
    Case 1: The playbook is valid - test with the default playbook object.
    Case 2: The playbook is invalid, with DeleteContext with all set to 'Yes'
    -

    When:
    - calling PlaybookDeleteContextAllValidator.obtain_invalid_content_items.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid.
        Case 2: The playbook is invalid.
    """
    playbook = create_playbook_object()
    assert not PlaybookDeleteContextAllValidator().obtain_invalid_content_items(
        [playbook]
    )
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"], "yes": ["2"]},
                "task": {
                    "id": "task-id",
                    "name": "DeleteContext",
                    "scriptName": "DeleteContext",
                },
                "scriptarguments": {"all": {"simple": "yes"}},
            }
        )
    }
    expected_result = (
        "The playbook includes DeleteContext tasks with all set to 'yes', which is not permitted."
        " Please correct the following tasks: ['task-id']"
        " For more info, see:"
        " https://xsoar.pan.dev/docs/playbooks/playbooks-overview#inputs-and-outputs"
    )

    assert (
        PlaybookDeleteContextAllValidator()
        .obtain_invalid_content_items([playbook])[0]
        .message
        == expected_result
    )


def test_does_playbook_have_unconnected_tasks():
    """
    Given: A playbook with tasks that are connected to each other.
    When: Validating the playbook.
    Then: The playbook is valid.
    """
    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"],
        values=[
            "0",
            {
                "0": {
                    "id": "test task",
                    "type": "regular",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"#none#": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                },
                "1": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
            },
        ],
    )
    validation_results = (
        DoesPlaybookHaveUnconnectedTasks().obtain_invalid_content_items([playbook])
    )
    assert len(validation_results) == 0  # No validation results should be returned


def test_does_playbook_have_unconnected_tasks_not_valid():
    """
    Given: A playbook with tasks that are not connected to the root task.
    When: Validating the playbook.
    Then: The playbook is not valid.
    """
    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"],
        values=[
            "0",
            {
                "0": {
                    "id": "test task",
                    "type": "regular",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"#none#": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                },
                "1": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
                "3": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
                "4": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
            },
        ],
    )
    orphan_tasks = ["3", "4"]
    validation_result = DoesPlaybookHaveUnconnectedTasks().obtain_invalid_content_items(
        [playbook]
    )
    assert validation_result
    assert validation_result[0].message == ERROR_MSG.format(orphan_tasks=orphan_tasks)


def test_IsDefaultNotOnlyConditionValidator():
    """
    Given:
        Case a: playbook with no conditional tasks.
        Case b: playbook with conditional tasks that has two reply options - yes/no.
        Case c: playbook with conditional tasks that has one reply options - #default#.
    When: Validating the playbook tasks to have more than a default option (IsDefaultNotOnlyConditionValidator).
    Then:
        Case a: The validation passes (result list of invalid items is empty)
        Case b: The validation passes (result list of invalid items is empty)
        Case c: The validation fails (result list of invalid items contains the invalid playbook)
    """
    playbook = create_playbook_object()
    assert not IsDefaultNotOnlyConditionValidator().obtain_invalid_content_items(
        [playbook]
    )
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "0",
                "type": "condition",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "message": {"replyOptions": ["yes", "no"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert not IsDefaultNotOnlyConditionValidator().obtain_invalid_content_items(
        [playbook]
    )
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "0",
                "type": "condition",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "message": {"replyOptions": ["#default#"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert IsDefaultNotOnlyConditionValidator().obtain_invalid_content_items([playbook])


def test_IsTaskidDifferentFromidValidator():
    """
    Given:
    - A playbook with tasks, taskid and id
        Case 1: id equals taskid
        Case 2: id not equals taskid

    When:
    - Validating the playbook

    Then:
    - The results should be as expected:
        Case 1: an empty list
        Case 2: a list in length 1 because there is one error
    """
    playbook = create_playbook_object()
    results = IsTaskidDifferentFromidValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == 0
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test",
                "taskid": "test1",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"]},
                "task": {"id": "test"},
            }
        )
    }
    results = IsTaskidDifferentFromidValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "On tasks: 0,  the field 'taskid' and the 'id' under the 'task' field must be with equal value."
    )


def test_IsPlayBookUsingAnInstanceValidator_obtain_invalid_content_items():
    """
    Given:
    - A playbook
        Case 1: The playbook is valid.
        Case 2: The playbook isn't valid, it has using field.
    When:
    - calling IsPlayBookUsingAnInstanceValidator.obtain_invalid_content_items.
    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is invalid
    """
    # Case 1
    valid_playbook = create_playbook_object()
    valid_result = IsPlayBookUsingAnInstanceValidator().obtain_invalid_content_items(
        [valid_playbook]
    )

    # Case 2
    invalid_playbook = create_playbook_object()
    for _, task in invalid_playbook.tasks.items():
        task.scriptarguments = {"using": "instance_name"}
    results_invalid = IsPlayBookUsingAnInstanceValidator().obtain_invalid_content_items(
        [invalid_playbook]
    )

    assert valid_result == []
    assert results_invalid != []
    assert results_invalid[0].message == (
        "Playbook should not use specific instance for tasks: {0}.".format(
            ", ".join([task.taskid for task in invalid_playbook.tasks.values()])
        )
    )


def test_IsPlayBookUsingAnInstanceValidator_fix():
    """
    Given:
    - A playbook
        Case 1: The playbook isn't valid, it will be fixed.
    When:
    - calling IsPlayBookUsingAnInstanceValidator.fix.
    Then:
    - The message appears with the invalid tasks.
    """

    # Case 1
    invalid_playbook = create_playbook_object()
    for _, task in invalid_playbook.tasks.items():
        task.scriptarguments = {"using": "instance_name", "some_key": "value"}
    validator_invalid_playbook = IsPlayBookUsingAnInstanceValidator()
    validator_invalid_playbook.invalid_tasks[invalid_playbook.name] = [
        task for task in invalid_playbook.tasks.values()
    ]
    fix_validator = validator_invalid_playbook.fix(invalid_playbook)
    fix_message = fix_validator.message
    fixed_content_item: Playbook = fix_validator.content_object
    expected_message = (
        "Removed The 'using' statement from the following tasks tasks: {0}.".format(
            ", ".join([task.taskid for task in invalid_playbook.tasks.values()])
        )
    )
    assert fix_message == expected_message
    for tasks in fixed_content_item.tasks.values():
        scriptargs = tasks.scriptarguments
        assert scriptargs == {"some_key": "value"}


def test_IsPlaybookContainUnhandledScriptConditionBranchesValidator_obtain_invalid_content_items():
    """
    Given:
    - A playbook
        Case 1: A valid playbook with 2 conditional tasks:
        - One script condition with 2 next task branches.
        - One non script condition with 1 next task branch.
        Case 2: Two script condition tasks with 1 next task branch each.
    When:
    - calling IsPlaybookContainUnhandledScriptConditionBranchesValidator.obtain_invalid_content_items.
    Then:
    - The results should be as expected:
        Case 1: The playbook is valid.
        Case 2: The playbook is invalid and both tasks should be mentioned as invalid.
    """
    validator = IsPlaybookContainUnhandledScriptConditionBranchesValidator()
    # Case 1
    valid_playbook = create_playbook_object(
        ["tasks"],
        [
            {
                "0": {
                    "id": "test fail task No1",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["1"], "yes": ["2"]},
                    "task": {
                        "id": "27b9c747-b883-4878-8b60-7f352098a63c",
                        "scriptName": "test",
                    },
                    "quietmode": 2,
                },
                "1": {
                    "id": "test fail task No2",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"yes": ["3"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "quietmode": 2,
                },
            }
        ],
    )
    valid_result = validator.obtain_invalid_content_items([valid_playbook])

    # Case 2
    invalid_playbook = create_playbook_object(
        ["tasks"],
        [
            {
                "0": {
                    "id": "0",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["1"]},
                    "task": {
                        "id": "27b9c747-b883-4878-8b60-7f352098a63c",
                        "scriptName": "test",
                    },
                    "quietmode": 2,
                },
                "1": {
                    "id": "1",
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"yes": ["3"]},
                    "task": {
                        "id": "27b9c747-b883-4878-8b60-7f352098a63c",
                        "scriptName": "test",
                    },
                    "quietmode": 2,
                },
            }
        ],
    )
    results_invalid = validator.obtain_invalid_content_items([invalid_playbook])

    assert valid_result == []
    assert results_invalid != []
    assert results_invalid[0].message == (
        "The following conditional tasks contains unhandled conditions: 0, 1."
    )


@pytest.mark.parametrize(
    "playbook_paths, playbook_values, expected_bad_keys, expected_fixed_values",
    [
        # Case 1: No marketplace suffixes specified.
        (
            ["description", "inputs", "starttaskid", "tasks"],
            [
                "some_desc",
                [
                    {
                        "key": "some_key",
                        "value": {"simple": "some value"},
                        "required": False,
                        "description": "some_key_desc",
                        "playbookInputQuery": None,
                    }
                ],
                "0",
                {
                    "0": {
                        "id": "test task",
                        "type": "regular",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"#none#": ["1"]},
                        "task": {"id": "some_id"},
                        "taskid": "some_id",
                    },
                    "1": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                },
            ],
            [],
            {},
        ),
        # Case 2: Various suffixes without a default.
        (
            ["starttaskid", "tasks", "inputs"],
            [
                "0",
                {
                    "0": {
                        "id": "test task",
                        "type": "regular",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"#none#": ["1"]},
                        "task": {"id": "some_id"},
                        "taskid": "some_id",
                    },
                    "1:xsoar": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                    "1:marketplacev2": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                },
                [
                    {
                        "key": "some_key",
                        "value:xsoar": {"simple:xsoar_saas": "some saas value"},
                        "value:xsoar_on_prem": {"simple": "some prem value"},
                        "required": False,
                        "description:xpanse": "some_key_desc",
                        "playbookInputQuery": None,
                    }
                ],
            ],
            [
                "root.tasks.1",
                "root.inputs.[0].value:xsoar.simple",
                "root.inputs.[0].value",
                "root.inputs.[0].description",
            ],
            [
                "0",
                {
                    "0": {
                        "id": "test task",
                        "type": "regular",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"#none#": ["1"]},
                        "task": {"id": "some_id"},
                        "taskid": "some_id",
                    },
                    "1": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                    "1:xsoar": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                    "1:marketplacev2": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                },
                [
                    {
                        "key": "some_key",
                        "value": {
                            "simple:xsoar_saas": "some saas value",
                            "simple": "some saas value",
                        },
                        "value:xsoar": {
                            "simple:xsoar_saas": "some saas value",
                            "simple": "some saas value",
                        },
                        "value:xsoar_on_prem": {"simple": "some prem value"},
                        "required": False,
                        "description:xpanse": "some_key_desc",
                        "description": "some_key_desc",
                        "playbookInputQuery": None,
                    }
                ],
            ],
        ),
        # Case 3: All keys with suffixes have default.
        (
            ["starttaskid", "tasks", "inputs"],
            [
                "0",
                {
                    "0": {
                        "id": "test task",
                        "type": "regular",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"#none#": ["1"]},
                        "task": {"id": "some_id"},
                        "taskid": "some_id",
                    },
                    "1": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                    "1:xsoar": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                    "1:marketplacev2": {
                        "id": "test task",
                        "type": "condition",
                        "message": {"replyOptions": ["yes"]},
                        "nexttasks": {"no": ["2"]},
                        "task": {"id": "some_id1"},
                        "taskid": "some_id1",
                    },
                },
                [
                    {
                        "key": "some_key",
                        "value": {"simple": "stuff"},
                        "value:xsoar": {
                            "simple": "some other value",
                            "simple:xsoar_saas": "some value",
                        },
                        "value:xsoar_on_prem": {"simple": "some value"},
                        "required": False,
                        "required:xsoar_on_prem": True,
                        "description": "some key",
                        "description:xpanse": "some_key_desc",
                        "playbookInputQuery": None,
                    }
                ],
            ],
            [],
            [],
        ),
    ],
)
def test_MarketplaceKeysHaveDefaultValidator(
    playbook_paths, playbook_values, expected_bad_keys, expected_fixed_values
):
    """
    Given: A playbook with:
        Case 1) No marketplace suffixes specified.
        Case 2) Various suffixes without a default.
        Case 3) Various suffixes with a default.
    When: Validating the playbook
    Then: Assert all paths without a default key were displayed and valid returned results accordingly.
        Case 1) valid, no paths.
        Case 2) invalid, all paths are returned.
        Case 3) valid, no paths.
    """
    error_message = (
        "The following playbook yml keys only do not have a default option: {}. Please remove these keys or add "
        "another default option to each key."
    )
    playbook_obj = create_playbook_object(paths=playbook_paths, values=playbook_values)
    marketplace_suffix_validator = MarketplaceKeysHaveDefaultValidator()
    results = marketplace_suffix_validator.obtain_invalid_content_items([playbook_obj])
    assert len(results) == (1 if expected_bad_keys else 0)
    if results:
        assert results[0].message == error_message.format(expected_bad_keys)

        fix_validator = marketplace_suffix_validator.fix(playbook_obj)
        fix_message = fix_validator.message
        fixed_content_item: Playbook = fix_validator.content_object

        expected_playbook_obj = create_playbook_object(
            paths=playbook_paths, values=expected_fixed_values
        )

        for expected_bad_key in expected_bad_keys:
            assert expected_bad_key in fix_message

        assert fixed_content_item.data == expected_playbook_obj.data


@pytest.mark.parametrize(
    "name, id, is_silent, result_len, file_name",
    [
        ("test", "test", False, 0, "test"),
        (
            "silent-test",
            "silent-test",
            True,
            0,
            "silent-test",
        ),
        (
            "test",
            "silent-test",
            True,
            1,
            "silent-test",
        ),
        (
            "silent-test",
            "test",
            True,
            1,
            "silent-test",
        ),
        (
            "silent-test",
            "silent-test",
            False,
            1,
            "silent-test",
        ),
        (
            "test",
            "silent-test",
            False,
            1,
            "test",
        ),
        (
            "silent-test",
            "test",
            False,
            1,
            "test",
        ),
        (
            "test",
            "test",
            True,
            1,
            "test",
        ),
        (
            "test",
            "test",
            False,
            1,
            "silent-test",
        ),
    ],
)
def test_IsSilentPlaybookValidator(name, id, is_silent, result_len, file_name):
    """
    Given:
        case 1: is_silent = False, and name/id/file_name do not contain silent prefix.
        case 2: is_silent = True, and name/id/file_name contain silent prefix.
        case 3: is_silent = True, name contain and id/file_name do not contain silent prefix.
        case 4: is_silent = True, id contain and name/file_name do not contain silent prefix.
        case 5: is_silent = False, and name/id/file_name contain silent prefix.
        case 6: is_silent = False, name contain and id/file_name do not contain silent prefix.
        case 7: is_silent = False, id contain and name/file_name do not contain silent prefix.
        case 8: is_silent = True, and name/id/file_name do not contain silent prefix.
        case 9: is_silent = False, and file_name contains silent prefix but name/id do not.

    When:
    - calling IsSilentPlaybookValidator.obtain_invalid_content_items.

    Then:
    - case 1: Passes. Non-silent playbook with no "silent-" prefix.
    - case 2: Passes. Silent playbook correctly configured with "silent-" in all fields.
    - case 3: Fails. Silent playbook must have "silent-" in id and file_name if it appears in name.
    - case 4: Fails. Silent playbook must have "silent-" in name and file_name if it appears in id.
    - case 5: Fails. Non-silent playbook should not have "silent-" in any field.
    - case 6: Fails. Non-silent playbook should not have "silent-" in name without matching id and file_name.
    - case 7: Fails. Non-silent playbook should not have "silent-" in id without matching name and file_name.
    - case 8: Fails. Silent playbook must have "silent-" in name, id, and file_name.
    - case 9: Fails. Non-silent playbook should not have "silent-" in file_name without matching name and id.
    """
    playbook = create_playbook_object(file_name=file_name)
    playbook.data["id"] = id
    playbook.data["name"] = name
    playbook.is_silent = is_silent

    invalid_content_items = IsSilentPlaybookValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert result_len == len(invalid_content_items)


def test_IsCorrectValueReferencesInterface_correct_pb():
    """
    Given:
    - A playbook has valid references to the context.
    When:
    - Running validate on the playbook.
    Then:
    - Validate that playbook passes.
    """
    pb_content = [
        {
            "0": {
                "continueonerrortype": "",
                "id": "0",
                "isoversize": False,
                "nexttasks": {"#none#": ["1"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "id": "08c98bec-e1c3-4fc3-8112-bf69676573f0",
                    "iscommand": False,
                    "name": "",
                    "version": -1,
                },
                "taskid": "08c98bec-e1c3-4fc3-8112-bf69676573f0",
                "timertriggers": [],
                "type": "start",
            },
            "1": {
                "conditions": [
                    {
                        "condition": [
                            [
                                {
                                    "left": {
                                        "iscontext": True,
                                        "value": {"simple": "incident.as_value"},
                                    },
                                    "operator": "isExists",
                                }
                            ],
                            [
                                {
                                    "left": {
                                        "iscontext": True,
                                        "value": {"simple": "incident.from_context"},
                                    },
                                    "operator": "AnyMatch",
                                    "right": {
                                        "value": {"simple": "${incident.as_value}"}
                                    },
                                }
                            ],
                        ],
                        "label": "yes",
                    },
                    {
                        "condition": [
                            [
                                {
                                    "left": {
                                        "iscontext": True,
                                        "value": {"simple": "incident.from_context"},
                                    },
                                    "operator": "isTrue",
                                }
                            ],
                            [
                                {
                                    "left": {
                                        "value": {
                                            "complex": {
                                                "root": "inputs.File",
                                                "accessor": "EntryID",
                                            }
                                        },
                                        "iscontext": True,
                                    },
                                    "operator": "isExists",
                                    "right": {"value": {}},
                                }
                            ],
                        ],
                        "label": "no",
                    },
                ],
                "continueonerrortype": "",
                "id": "1",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"yes": ["2"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.desc}",
                    "id": "1ed95b8a-fcdd-4aa5-858a-85b4d79c7c34",
                    "iscommand": False,
                    "name": "Conditional Built-in",
                    "tags": ["a", "b"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "1ed95b8a-fcdd-4aa5-858a-85b4d79c7c34",
                "timertriggers": [],
                "type": "condition",
            },
            "2": {
                "continueonerrortype": "",
                "defaultassigneecomplex": {"simple": "${incident.accountid}"},
                "id": "2",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"#default#": ["3"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.accountid}",
                    "id": "5bc96b47-4044-4c44-8f80-bf4b15fe6233",
                    "iscommand": False,
                    "name": "Conditional Manual",
                    "tags": ["a"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "5bc96b47-4044-4c44-8f80-bf4b15fe6233",
                "timertriggers": [],
                "type": "condition",
            },
            "3": {
                "continueonerrortype": "",
                "id": "3",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "${incident.alerttags}"},
                    "cc": {"simple": "Read-Only"},
                    "format": "",
                    "methods": ["email"],
                    "replyOptions": ["Yes", "No"],
                    "subject": {"simple": "${incident.accountname}"},
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": {"simple": "${incident.asn}"},
                },
                "nexttasks": {"Yes": ["4"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {"using": {"simple": "${incident.approver}"}},
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.additionaldata}",
                    "id": "9d366fdc-da13-4d7d-8c04-88f6c403bc6e",
                    "iscommand": False,
                    "name": "Conditional Ask",
                    "tags": ["b"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "9d366fdc-da13-4d7d-8c04-88f6c403bc6e",
                "timertriggers": [],
                "type": "condition",
            },
            "4": {
                "continueonerrortype": "",
                "fieldMapping": [
                    {"output": {"simple": "${DBotPredictURLPhishing.URL}"}}
                ],
                "id": "4",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"#default#": ["5"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {
                    "extend-context": {"simple": "${incident.not_from_context}"},
                    "urls": {"simple": "${incident.additionaldata}"},
                    "using": {"simple": "${incident.accountname}"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.}",
                    "id": "91c388dd-6bdb-4a27-84bc-82770b7ae6ff",
                    "iscommand": False,
                    "name": "Conditional Run Command",
                    "scriptName": "DBotPredictURLPhishingCandidate",
                    "tags": ["a"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "91c388dd-6bdb-4a27-84bc-82770b7ae6ff",
                "timertriggers": [],
                "type": "condition",
            },
            "5": {
                "continueonerrortype": "",
                "id": "5",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"#none#": ["6"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {
                    "action": {
                        "complex": {
                            "filters": [
                                [
                                    {
                                        "left": {
                                            "iscontext": True,
                                            "value": {"simple": "${incident.}"},
                                        },
                                        "operator": "isEqualString",
                                        "right": {"value": {"simple": "${incident.}"}},
                                    }
                                ]
                            ],
                            "root": "incident",
                            "transformers": [
                                {
                                    "args": {
                                        "conditions": {
                                            "iscontext": True,
                                            "value": {
                                                "simple": "incident.from_context"
                                            },
                                        },
                                        "flags": {
                                            "iscontext": True,
                                            "value": {"simple": "incident.as_value"},
                                        },
                                    },
                                    "operator": "If-Elif",
                                }
                            ],
                        }
                    },
                    "associatedDomains": {"simple": "${incident.simple}"},
                    "using": {"simple": "${incident.asn}"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.affectedhosts}",
                    "id": "a6215bdd-8d94-46df-807a-991d9209f0e2",
                    "iscommand": False,
                    "name": "Regular",
                    "scriptName": "DBotUpdateLogoURLPhishing",
                    "type": "regular",
                    "version": -1,
                },
                "taskid": "a6215bdd-8d94-46df-807a-991d9209f0e2",
                "timertriggers": [],
                "type": "regular",
            },
            "6": {
                "continueonerrortype": "",
                "form": {
                    "description": "desc",
                    "expired": False,
                    "questions": [
                        {
                            "defaultrows": [],
                            "fieldassociated": "",
                            "gridcolumns": [],
                            "id": "0",
                            "label": "",
                            "labelarg": {"simple": "${incident.city}"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        },
                        {
                            "defaultrows": [],
                            "fieldassociated": "attackmode",
                            "gridcolumns": [],
                            "id": "1",
                            "label": "",
                            "labelarg": {"simple": "why?"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        },
                    ],
                    "sender": "",
                    "title": "Title",
                    "totalanswers": 0,
                },
                "id": "6",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "${incident.email}"},
                    "cc": None,
                    "format": "",
                    "methods": [],
                    "subject": None,
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": None,
                },
                "nexttasks": {"#none#": ["7"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {
                    "extend-context": {"simple": "${incident.no_context}"},
                    "using": {"simple": "${incident.using},${incident.thing}"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.acquisitionhire}",
                    "id": "1df1fc5c-ec39-40ee-867a-52a677bb8699",
                    "iscommand": False,
                    "name": "Collection Task Only",
                    "type": "collection",
                    "version": -1,
                },
                "taskid": "1df1fc5c-ec39-40ee-867a-52a677bb8699",
                "timertriggers": [],
                "type": "collection",
            },
            "7": {
                "continueonerrortype": "",
                "form": {
                    "description": "",
                    "expired": False,
                    "questions": [
                        {
                            "defaultrows": [],
                            "fieldassociated": "",
                            "gridcolumns": [],
                            "id": "0",
                            "label": "",
                            "labelarg": {"simple": "${incident.why}"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        }
                    ],
                    "sender": "",
                    "title": "incident",
                    "totalanswers": 0,
                },
                "id": "7",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "${incident.body}"},
                    "cc": {"simple": "${incident.from_context}"},
                    "format": "",
                    "methods": ["email"],
                    "subject": {"simple": "incident"},
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": {"simple": "${incident.acquisitionhire}"},
                },
                "nexttasks": {"#none#": ["8"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "id": "f25d3769-3903-470a-898c-e6561a716253",
                    "iscommand": False,
                    "name": "Collection Email",
                    "type": "collection",
                    "version": -1,
                },
                "taskid": "f25d3769-3903-470a-898c-e6561a716253",
                "timertriggers": [],
                "type": "collection",
            },
            "8": {
                "continueonerrortype": "",
                "id": "8",
                "task": {
                    "brand": "",
                    "id": "4a775481-62cc-405c-8f5f-b01437eac66c",
                    "iscommand": False,
                    "name": "${incident.asn}",
                    "type": "title",
                    "version": -1,
                },
                "taskid": "4a775481-62cc-405c-8f5f-b01437eac66c",
                "timertriggers": [],
                "type": "title",
            },
        },
    ]

    pb_object = create_playbook_object(paths=["tasks"], values=pb_content)

    results = IsCorrectValueReferencesInterface().obtain_invalid_content_items(
        [pb_object]
    )

    assert (
        results == []
    ), f"Playbook has valid value references, but the validator got: {results}"


def test_IsCorrectValueReferencesInterface_incorrect_pb():
    """
    Given:
    - A playbook has invalid references to the context.
    When:
    - Running validate on the playbook.
    Then:
    - Validate that the incorrect references are caught.
    """
    pb_content = [
        {
            "0": {
                "continueonerrortype": "",
                "id": "0",
                "isoversize": False,
                "nexttasks": {"#none#": ["1"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "id": "08c98bec-e1c3-4fc3-8112-bf69676573f0",
                    "iscommand": False,
                    "name": "",
                    "version": -1,
                },
                "taskid": "08c98bec-e1c3-4fc3-8112-bf69676573f0",
                "timertriggers": [],
                "type": "start",
            },
            "1": {
                "conditions": [
                    {
                        "condition": [
                            [
                                {
                                    "left": {
                                        "iscontext": False,
                                        "value": {"simple": "incident.1"},
                                    },
                                    "operator": "isExists",
                                }
                            ],
                            [
                                {
                                    "left": {"value": {"simple": "incident.2"}},
                                    "operator": "AnyMatch",
                                    "right": {"value": {"simple": "inputs.3"}},
                                }
                            ],
                        ],
                        "label": "yes",
                    },
                    {
                        "condition": [
                            [
                                {
                                    "left": {"value": {"simple": "incident.4"}},
                                    "operator": "isTrue",
                                }
                            ],
                            [
                                {
                                    "left": {
                                        "value": {
                                            "complex": {
                                                "root": "inputs.5",
                                                "accessor": "EntryID",
                                            }
                                        },
                                        "iscontext": True,
                                    },
                                    "operator": "isExists",
                                    "right": {"value": {}},
                                }
                            ],
                        ],
                        "label": "no",
                    },
                ],
                "continueonerrortype": "",
                "id": "1",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"yes": ["2"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "${incident.desc}",
                    "id": "1ed95b8a-fcdd-4aa5-858a-85b4d79c7c34",
                    "iscommand": False,
                    "name": "Conditional Built-in",
                    "tags": ["a", "b"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "1ed95b8a-fcdd-4aa5-858a-85b4d79c7c34",
                "timertriggers": [],
                "type": "condition",
            },
            "2": {
                "continueonerrortype": "",
                "defaultassigneecomplex": {"simple": "incident.6"},
                "id": "2",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"#default#": ["3"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "incident.7",
                    "id": "5bc96b47-4044-4c44-8f80-bf4b15fe6233",
                    "iscommand": False,
                    "name": "Conditional Manual",
                    "tags": ["a"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "5bc96b47-4044-4c44-8f80-bf4b15fe6233",
                "timertriggers": [],
                "type": "condition",
            },
            "3": {
                "continueonerrortype": "",
                "id": "3",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "incident.8"},
                    "cc": {"simple": "Read-Only"},
                    "format": "",
                    "methods": ["email"],
                    "replyOptions": ["Yes", "No"],
                    "subject": {"simple": "incident.9"},
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": {"simple": "incident.10"},
                },
                "nexttasks": {"Yes": ["4"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {"using": {"simple": "incident.11"}},
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "incident.12",
                    "id": "9d366fdc-da13-4d7d-8c04-88f6c403bc6e",
                    "iscommand": False,
                    "name": "Conditional Ask",
                    "tags": ["b"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "9d366fdc-da13-4d7d-8c04-88f6c403bc6e",
                "timertriggers": [],
                "type": "condition",
            },
            "4": {
                "continueonerrortype": "",
                "fieldMapping": [
                    {"output": {"simple": "${DBotPredictURLPhishing.URL}"}}
                ],
                "id": "4",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "nexttasks": {"#default#": ["5"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {
                    "extend-context": {"simple": "incident.13"},
                    "urls": {"simple": "incident.14"},
                    "using": {"simple": "incident.15"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "incident.16",
                    "id": "91c388dd-6bdb-4a27-84bc-82770b7ae6ff",
                    "iscommand": False,
                    "name": "Conditional Run Command",
                    "scriptName": "DBotPredictURLPhishingCandidate",
                    "tags": ["a"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "91c388dd-6bdb-4a27-84bc-82770b7ae6ff",
                "type": "condition",
            },
            "5": {
                "continueonerrortype": "",
                "id": "5",
                "nexttasks": {"#none#": ["6"]},
                "scriptarguments": {
                    "action": {
                        "complex": {
                            "filters": [
                                [
                                    {
                                        "operator": "isEqualString",
                                        "left": {
                                            "value": {"simple": "incident.17"},
                                            "iscontext": False,
                                        },
                                        "right": {"value": {"simple": "incident.18"}},
                                    }
                                ]
                            ],
                            "root": "incident",
                            "transformers": [
                                {
                                    "args": {
                                        "conditions": {
                                            "value": {"simple": "incident.19"}
                                        },
                                        "flags": {
                                            "iscontext": False,
                                            "value": {"simple": "incident.20"},
                                        },
                                    },
                                    "operator": "If-Elif",
                                }
                            ],
                        }
                    },
                    "associatedDomains": {"simple": "incident.21"},
                    "using": {"simple": "incident.22"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "incident.23",
                    "id": "a6215bdd-8d94-46df-807a-991d9209f0e2",
                    "iscommand": False,
                    "name": "Regular",
                    "scriptName": "DBotUpdateLogoURLPhishing",
                    "type": "regular",
                    "version": -1,
                },
                "taskid": "a6215bdd-8d94-46df-807a-991d9209f0e2",
                "timertriggers": [],
                "type": "regular",
            },
            "6": {
                "continueonerrortype": "",
                "form": {
                    "description": "desc",
                    "expired": False,
                    "questions": [
                        {
                            "defaultrows": [],
                            "fieldassociated": "",
                            "gridcolumns": [],
                            "id": "0",
                            "label": "",
                            "labelarg": {"simple": "incident.24"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        },
                        {
                            "defaultrows": [],
                            "fieldassociated": "attackmode",
                            "gridcolumns": [],
                            "id": "1",
                            "label": "",
                            "labelarg": {"simple": "why?"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        },
                    ],
                    "sender": "",
                    "title": "Title",
                    "totalanswers": 0,
                },
                "id": "6",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "incident.25"},
                    "cc": None,
                    "format": "",
                    "methods": [],
                    "subject": None,
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": None,
                },
                "nexttasks": {"#none#": ["7"]},
                "note": False,
                "quietmode": 0,
                "scriptarguments": {
                    "extend-context": {"simple": "incident.26"},
                    "using": {"simple": "incident.27,incident.28"},
                },
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "description": "incident.29",
                    "id": "1df1fc5c-ec39-40ee-867a-52a677bb8699",
                    "iscommand": False,
                    "name": "Collection Task Only",
                    "type": "collection",
                    "version": -1,
                },
                "taskid": "1df1fc5c-ec39-40ee-867a-52a677bb8699",
                "timertriggers": [],
                "type": "collection",
            },
            "7": {
                "continueonerrortype": "",
                "form": {
                    "description": "",
                    "expired": False,
                    "questions": [
                        {
                            "defaultrows": [],
                            "fieldassociated": "",
                            "gridcolumns": [],
                            "id": "0",
                            "label": "",
                            "labelarg": {"simple": "incident.30"},
                            "options": [],
                            "optionsarg": [],
                            "placeholder": "",
                            "readonly": False,
                            "required": False,
                            "tooltip": "",
                            "type": "shortText",
                        }
                    ],
                    "sender": "",
                    "title": "incident",
                    "totalanswers": 0,
                },
                "id": "7",
                "ignoreworker": False,
                "isautoswitchedtoquietmode": False,
                "isoversize": False,
                "message": {
                    "bcc": None,
                    "body": {"simple": "incident.31"},
                    "cc": {"simple": "incident.32"},
                    "format": "",
                    "methods": ["email"],
                    "subject": {"simple": "incident"},
                    "timings": {
                        "completeafterreplies": 1,
                        "completeaftersla": False,
                        "completeafterv2": True,
                        "retriescount": 2,
                        "retriesinterval": 360,
                    },
                    "to": {"simple": "incident.33"},
                },
                "nexttasks": {"#none#": ["8"]},
                "note": False,
                "quietmode": 0,
                "separatecontext": False,
                "skipunavailable": False,
                "task": {
                    "brand": "",
                    "id": "f25d3769-3903-470a-898c-e6561a716253",
                    "iscommand": False,
                    "name": "Collection Email",
                    "type": "collection",
                    "version": -1,
                },
                "taskid": "f25d3769-3903-470a-898c-e6561a716253",
                "timertriggers": [],
                "type": "collection",
            },
            "8": {
                "continueonerrortype": "",
                "id": "8",
                "task": {
                    "brand": "",
                    "id": "4a775481-62cc-405c-8f5f-b01437eac66c",
                    "iscommand": False,
                    "name": "incident.34",
                    "type": "title",
                    "version": -1,
                },
                "taskid": "4a775481-62cc-405c-8f5f-b01437eac66c",
                "type": "title",
            },
        },
    ]

    pb_object = create_playbook_object(paths=["tasks"], values=pb_content)

    results = IsCorrectValueReferencesInterface().obtain_invalid_content_items(
        [pb_object]
    )
    messages = "".join(res.message for res in results)
    missing_alerts = [i for i in range(1, 35) if str(i) not in messages]
    assert not missing_alerts, f"Playbook has invalid value references, but the validator missed: {missing_alerts}"


def test_IsCorrectValueReferencesInterface_fix():
    """
    Given:
    - A playbook has invalid references to the context.
    When:
    - Running validate on a playbook with the fix flag.
    Then:
    - Validate that the references are fixed.
    """
    incorrect_pb_content = [
        {
            "0": {
                "id": "0",
                "task": {
                    "brand": "",
                    "description": "incident.item1,${incident.item2},incident.item3",
                    "id": "12345",
                    "iscommand": False,
                    "name": "Task Name",
                    "tags": ["a"],
                    "type": "condition",
                    "version": -1,
                },
                "taskid": "12345",
                "type": "condition",
                "scriptarguments": {"arg": {"simple": "incident.item4"}},
            },
        },
    ]

    incorrect_pb_object = create_playbook_object(
        paths=["tasks"], values=incorrect_pb_content
    )

    results = IsCorrectValueReferencesInterface().fix(incorrect_pb_object)

    assert (
        results.message
        == "Fixed the following inputs:\n'incident.item4' in task: 'Task Name'\n'incident.item1' in task: 'Task Name'\n'incident.item3' in task: 'Task Name'"
    )
    assert (
        results.content_object.tasks["0"].task.description
        == "${incident.item1},${incident.item2},${incident.item3}"
    )
    assert (
        results.content_object.tasks["0"].scriptarguments["arg"]["simple"]
        == "${incident.item4}"
    )


class Pack:
    content_items = PackContentItems()


@pytest.mark.parametrize(
    "playbook_id, playbook_is_silent, trigger_playbook_id, trigger_is_silent, result_len",
    [
        (
            "test",
            True,
            "test",
            False,
            1,
        ),
        (
            "test",
            True,
            "test",
            True,
            0,
        ),
        (
            "test1",
            True,
            "test2",
            False,
            1,
        ),
        (
            "test1",
            True,
            "test2",
            True,
            1,
        ),
        (
            "test1",
            False,
            "test1",
            True,
            0,
        ),
    ],
)
def test_IsSilentPlaybookRelationshipsValidator(
    playbook_id,
    playbook_is_silent,
    trigger_playbook_id,
    trigger_is_silent,
    result_len,
    mocker,
    graph_repo: Repo,
):
    """
    Given:
    - case 1: A silent trigger that points on a non-silent playbook.
    - case 2: A silent trigger that points on a silent playbook.
    - case 3: A silent trigger that points on a non-silent playbook that is not found.
    - case 4: A silent trigger that points on a silent playbook that is not found.
    - case 5: A non-silent trigger that points on a silent playbook.
    When:
    - Calling IsSilentPlaybookRelationshipsValidator for playbooks.
    Then:
    - Validate that only invalid items are returned.
    """
    pack = graph_repo.create_pack("Pack-silent")

    pack.create_playbook(
        name="silent-test1",
        yml={"id": playbook_id, "issilent": playbook_is_silent, "name": playbook_id},
    )

    pack.create_trigger(
        "silent-trigger",
        content={
            "trigger_id": "silent-trigger",
            "playbook_id": trigger_playbook_id,
            "issilent": trigger_is_silent,
            "trigger_name": "silent-trigger",
        },
    )
    graph_path = graph_repo.path

    BaseValidator.graph_interface = graph_repo.create_graph()
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_content_path", return_value=graph_path
    )
    results = IsSilentPlaybookRelationshipsValidator().obtain_invalid_content_items(
        [graph_repo.packs[0].playbooks[0].object]
    )
    assert result_len == len(results)


@pytest.mark.parametrize(
    "trigger_playbook_id, trigger_is_silent, playbook_id, playbook_is_silent, result_len",
    [
        (
            "silent-test1",
            True,
            "silent-test1",
            False,
            1,
        ),
        (
            "silent-test1",
            True,
            "silent-test1",
            True,
            0,
        ),
        (
            "silent-test3",
            True,
            "silent-test33",
            False,
            1,
        ),
        (
            "silent-test4",
            True,
            "silent-test44",
            True,
            1,
        ),
        (
            "silent-test5",
            False,
            "silent-test5",
            True,
            0,
        ),
    ],
)
def test_IsSilentTriggerRelationshipsValidator(
    trigger_playbook_id,
    trigger_is_silent,
    playbook_id,
    playbook_is_silent,
    result_len,
    mocker,
    graph_repo: Repo,
):
    """
    Given:
    - case 1: A silent playbook that corresponds to a non-silent trigger.
    - case 2: A silent playbook that corresponds to a silent trigger.
    - case 3: A silent playbook that corresponds to a non-silent trigger that is not found.
    - case 4: A silent playbook that corresponds to a silent trigger that is not found.
    - case 5: A non-silent playbook that corresponds to a silent trigger.
    When:
    - Calling IsSilentPlaybookRelationshipsValidator for playbooks.
    Then:
    - Validate that only invalid items are returned.
    """

    pack = graph_repo.create_pack("Pack-silent")

    pack.create_trigger(
        "silent-trigger",
        content={
            "trigger_id": "silent-trigger",
            "playbook_id": trigger_playbook_id,
            "issilent": trigger_is_silent,
            "trigger_name": "silent-trigger",
        },
    )

    pack.create_playbook(
        name="silent-test1",
        yml={"id": playbook_id, "issilent": playbook_is_silent, "name": playbook_id},
    )

    BaseValidator.graph_interface = graph_repo.create_graph()
    graph_path = graph_repo.path
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_content_path", return_value=graph_path
    )
    results = IsSilentPlaybookRelationshipsValidator().obtain_invalid_content_items(
        [graph_repo.packs[0].triggers[0].object]
    )
    assert result_len == len(results)


def test_NoReadmeForSilentPlaybook():
    """
    Given:
    a silent playbook with/without a readme file.

    When:
    - calling NoReadmeForSilentPlaybook.obtain_invalid_content_items.

    Then:
    - Checks that it fails only when there is a readme.
    """
    playbook = create_playbook_object()
    playbook.is_silent = True
    playbook.readme.exist = True
    invalid_content_items = NoReadmeForSilentPlaybook().obtain_invalid_content_items(
        [playbook]
    )
    assert len(invalid_content_items) == 1

    playbook.readme.exist = False
    invalid_content_items = NoReadmeForSilentPlaybook().obtain_invalid_content_items(
        [playbook]
    )
    assert len(invalid_content_items) == 0


def test_PlaybookTestsExistValidator_valid(graph_repo: Repo):
    """
    Given:
    - A playbook that correctly refrences a test playbook and test use case that exist.

    When:
    - Calling PlaybookTestsExistValidator.obtain_invalid_content_items_using_graph.

    Then:
    - Ensure no validation errors.
    """
    playbook_id = "Generic Remediation"
    test_playbook_id = "Remediation Test"
    test_use_case_name = "Remediation_use_case_test"

    pack: TestSuitePack = graph_repo.create_pack("Incident Remediation Pack")
    pack.create_playbook(
        "playbook-GenericRemediation",
        yml={
            "id": playbook_id,
            "name": playbook_id,
            # Referenced PB tests are valid and defined below
            "tests": [test_playbook_id, test_use_case_name],
        },
    )
    pack.create_test_playbook(
        "playbook-RemediationTest",
        yml={
            "id": test_playbook_id,
            "name": test_playbook_id,
        },
    )
    pack.create_test_use_case(
        test_use_case_name,
        content="import pytest\n...",
    )

    BaseValidator.graph_interface = graph_repo.create_graph()
    validation_results = (
        PlaybookTestsExistValidator().obtain_invalid_content_items_using_graph(
            content_items=[], validate_all_files=True
        )
    )

    assert len(validation_results) == 0


def test_PlaybookTestsExistValidator_invalid(graph_repo: Repo):
    """
    Given:
    - A playbook that refrences a test playbook that does not exist.

    When:
    - Calling PlaybookTestsExistValidator.obtain_invalid_content_items_using_graph.

    Then:
    - Ensure a validation error is returned with the expected message (missing test playbook).
    """
    playbook_id = "Extract Indicators"
    test_playbook_id = "Extraction & Enrichment Test"

    pack: TestSuitePack = graph_repo.create_pack("Indcator Extraction Pack")
    pack.create_playbook(
        "playbook-ExtractIndicators",
        yml={
            "id": playbook_id,
            "name": playbook_id,
            # Referenced PB tests do not exist!
            "tests": [test_playbook_id],
        },
    )

    BaseValidator.graph_interface = graph_repo.create_graph()
    validation_results = (
        PlaybookTestsExistValidator().obtain_invalid_content_items_using_graph(
            content_items=[], validate_all_files=True
        )
    )

    expected_message = f"Playbook '{playbook_id}' references the following missing test playbooks: {test_playbook_id}."
    assert validation_results[0].message == expected_message


def test_PlaybookTestUseCaseConfigValidator_valid():
    """
    Given:
    - A pack that contains a test use case with a valid configuration docstring.

    When:
    - Calling PlaybookTestUseCaseConfigValidator.obtain_invalid_content_items.

    Then:
    - Ensure no validation errors.
    """
    config = '{"additional_needed_packs": {"TestPack": "pack_instance_1"}}'
    test_use_case_name = "CloudInfra_use_case_test"
    playbook = create_playbook_object(
        paths=["tests"],
        values=[[test_use_case_name]],
    )
    create_test_use_case_file_object(
        playbook_path=playbook.path,
        test_use_case_name=test_use_case_name,
        test_use_case_content=f"'''\n{config}\n'''\nimport pytest",
    )

    validation_results = (
        PlaybookTestUseCaseConfigValidator().obtain_invalid_content_items(
            content_items=[playbook]
        )
    )
    assert validation_results == []


@pytest.mark.parametrize(
    "config, expected_invalid_reason",
    [
        pytest.param(
            '{"additional"_"needed_packs": /dkfg.})',
            "Invalid JSON object",
            id="Invalid JSON",
        ),
        pytest.param(
            '{"additional_needed_packs": 123}',
            "Invalid object schema",
            id="Invalid Schema",
        ),
        pytest.param(
            '{"additional_needed_packs": {"BlahBlah": "hello_instance"}}',
            "Unknown packs: BlahBlah",
            id="Invalid Pack",
        ),
    ],
)
def test_PlaybookTestUseCaseConfigValidator_invalid(
    config: str,
    expected_invalid_reason: str,
):
    """
    Given:
    - A pack that contains a test use case with an invalid configuration docstring.

    When:
    - Calling PlaybookTestUseCaseConfigValidator.obtain_invalid_content_items.

    Then:
    - Ensure a validation error is returned with the expected message.
    """
    test_use_case_name = "Generic_use_case_test"
    playbook = create_playbook_object(
        paths=["tests"],
        values=[[test_use_case_name]],
    )
    create_test_use_case_file_object(
        playbook_path=playbook.path,
        test_use_case_name=test_use_case_name,
        test_use_case_content=f"'''\n{config}\n'''\nimport pytest",
    )

    validation_results = (
        PlaybookTestUseCaseConfigValidator().obtain_invalid_content_items(
            content_items=[playbook]
        )
    )
    expected_message = f"Invalid configuration in test use case: {test_use_case_name}. {expected_invalid_reason}."
    assert validation_results[0].message == expected_message

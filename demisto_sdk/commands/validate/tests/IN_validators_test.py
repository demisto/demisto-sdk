from typing import List

import pytest

from demisto_sdk.commands.common.constants import (
    COMMON_PARAMS_DISPLAY_NAME,
    DEFAULT_MAX_FETCH,
    FIRST_FETCH,
    FIRST_FETCH_PARAM,
    GET_MAPPING_FIELDS_COMMAND,
    GET_MAPPING_FIELDS_COMMAND_NAME,
    MAX_FETCH,
    MAX_FETCH_PARAM,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN100_is_valid_proxy_and_insecure import (
    IsValidProxyAndInsecureValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN102_is_valid_checkbox_param import (
    IsValidCheckboxParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN104_is_valid_category import (
    IsValidCategoryValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN108_is_valid_subtype import (
    ValidSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN109_is_id_contain_beta import (
    IsIdContainBetaValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN110_is_name_contain_beta import (
    IsNameContainBetaValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN112_is_display_contain_beta import (
    IsDisplayContainBetaValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN113_is_command_args_contain_duplications import (
    IsCommandArgsContainDuplicationsValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN114_is_params_contain_duplications import (
    IsParamsContainDuplicationsValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN115_is_valid_context_path import (
    IsValidContextPathValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN117_should_have_display_field import (
    ShouldHaveDisplayFieldValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN118_is_missing_display_field import (
    IsMissingDisplayFieldValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN125_is_valid_max_fetch_param import (
    IsValidMaxFetchParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN126_is_valid_fetch_integration import (
    IsValidFetchIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN130_is_integration_runable import (
    IsIntegrationRunnableValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN131_is_valid_as_mappable_integration import (
    IsValidAsMappableIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN134_is_containing_multiple_default_args import (
    IsContainingMultipleDefaultArgsValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(paths=["script.subtype"], values=["test"]),
                create_integration_object(),
            ],
            1,
            ["The subtype test is invalid, please change to python2 or python3."],
        ),
        (
            [
                create_script_object(paths=["subtype"], values=["test"]),
                create_script_object(),
            ],
            1,
            ["The subtype test is invalid, please change to python2 or python3."],
        ),
        (
            [
                create_script_object(),
                create_integration_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_script_object(paths=["subtype"], values=["test"]),
                create_integration_object(paths=["script.subtype"], values=["test"]),
            ],
            2,
            [
                "The subtype test is invalid, please change to python2 or python3.",
                "The subtype test is invalid, please change to python2 or python3.",
            ],
        ),
    ],
)
def test_ValidSubtypeValidator_is_valid(
    content_items, expected_number_of_failures: int, expected_msgs: List[str]
):
    """
    Given
    content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has subtype different from python2/3 and the second one does.
        - Case 2: content_items with 2 script where the first one has subtype different from python2/3 and the second one does.
        - Case 3: content_items with one script and one integration where both have python3 as subtype.
        - Case 4: content_items with one script and one integration where both dont have python2/python3 as subtype.
    When
    - Calling the ValidSubtypeValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 script.
        - Case 3: Should'nt fail at all.
        - Case 4: Should fail all content items.
    """
    results = ValidSubtypeValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        (
            [
                create_integration_object(
                    paths=[
                        "script.isfetch",
                        "script.feed",
                        "script.longRunning",
                        "script.commands",
                    ],
                    values=[False, False, False, []],
                ),
            ],
            1,
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.isfetch",
                        "script.feed",
                        "script.longRunning",
                        "script.commands",
                    ],
                    values=[True, False, False, []],
                ),
            ],
            0,
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.isfetch",
                        "script.feed",
                        "script.longRunning",
                        "script.commands",
                    ],
                    values=[False, True, False, []],
                ),
            ],
            0,
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.isfetch",
                        "script.feed",
                        "script.longRunning",
                        "script.commands",
                    ],
                    values=[False, False, True, []],
                ),
            ],
            0,
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.isfetch",
                        "script.feed",
                        "script.longRunning",
                        "script.commands",
                    ],
                    values=[False, False, False, [{"name": "test"}]],
                ),
            ],
            0,
        ),
    ],
)
def test_IsIntegrationRunnableValidator_is_valid(
    content_items: List[Integration], expected_number_of_failures: int
):
    """
    Given
    content_items iterables.
        - Case 1: An integration without any commands, and isfetch, feed, and longRunnings keys are set to false.
        - Case 2: An integration without any commands, and feed, and longRunnings keys are set to false, and isfetch is set to True.
        - Case 3: An integration without any commands, and isfetch, feed, and longRunnings keys are set to false, and feed is set to True.
        - Case 4: An integration without any commands, and isfetch, and feed keys are set to false, and longRunnings is set to True.
        - Case 5: An integration with one command, and isfetch, feed, and longRunnings keys are set to false.
    When
    - Calling the IsIntegrationRunnableValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Should pass.
        - Case 3: Should pass.
        - Case 4: Should pass.
        - Case 5: Should pass.
    """
    results = IsIntegrationRunnableValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert (
        not results
        or results[0].message
        == "Could not find any runnable command in the integration.\nMust have at least one of: a command under the `commands` section, `isFetch: true`, `feed: true`, or `longRunning: true`."
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "insecure",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "unscure",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "proxy",
                                "type": 8,
                                "required": False,
                                "display": "Use system proxy settings",
                            }
                        ]
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[[{"name": "proxy", "display": "a", "type": 1}]],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "proxy",
                                "display": "Use system proxy settingss",
                                "type": 1,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "proxy",
                                "display": "Use system proxy settings",
                                "type": 1,
                                "required": False,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "proxy",
                                "display": "Use system proxy settings",
                                "type": 8,
                                "required": True,
                            }
                        ]
                    ],
                ),
            ],
            4,
            [
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8.",
            ],
        ),
    ],
)
def test_IsValidProxyAndInsecureValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One integration without proxy / insecure params.
            - One integration with valid insecure param.
            - One integration with valid unsecure param.
            - One integration with valid proxy param.
        - Case 2: Four invalid integrations:
            - One integration with proxy param with a wrong display name.
            - One integration with proxy param without required field and a wrong type field.
            - One integration with proxy param with a wrong type.
            - One integration with proxy param with a required field set to true.
    When
    - Calling the IsValidProxyAndInsecureValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsValidProxyAndInsecureValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidProxyAndInsecureValidator_fix():
    """
    Given
        An integration with invalid proxy & insecure params.
    When
    - Calling the IsValidProxyAndInsecureValidator fix function.
    Then
        - Make sure that all the relevant fields were added/fixed and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {"name": "proxy", "display": "a", "type": 1},
                {
                    "name": "insecure",
                    "type": 1,
                    "required": True,
                    "display": "Trust any certificate (not secure)",
                },
            ]
        ],
    )
    validator = IsValidProxyAndInsecureValidator()
    validator.fixed_params[content_item.name] = {
        "insecure": {
            "name": "insecure",
            "type": 8,
            "required": False,
            "display": "Trust any certificate (not secure)",
        },
        "proxy": {
            "name": "proxy",
            "type": 8,
            "required": False,
            "display": "Use system proxy settings",
        },
    }
    assert (
        validator.fix(content_item).message
        == "Corrected the following params: insecure, proxy."
    )
    for param in content_item.params:
        assert param.type == 8
        assert not param.required
        assert param.display == COMMON_PARAMS_DISPLAY_NAME[param.name]


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [{"name": "test_param_1", "type": 8, "display": "test param 1"}]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [{"name": "test_param_2", "type": 0, "display": "test param 2"}]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_param_3",
                                "type": 8,
                                "display": "test param 3",
                                "required": False,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_param_4",
                                "type": 8,
                                "display": "test param 4",
                                "required": True,
                            },
                            {
                                "name": "test_param_5",
                                "type": 8,
                                "display": "test param 5",
                                "required": False,
                            },
                            {
                                "name": "test_param_6",
                                "type": 8,
                                "display": "test param 6",
                                "required": False,
                            },
                        ]
                    ],
                ),
            ],
            3,
            [
                "The following checkbox params required field is not set to True: test_param_1.\nMake sure to set it to True.",
                "The following checkbox params required field is not set to True: test_param_3.\nMake sure to set it to True.",
                "The following checkbox params required field is not set to True: test_param_5, test_param_6.\nMake sure to set it to True.",
            ],
        ),
    ],
)
def test_IsValidCheckboxParamValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Four integrations:
            - One integration with a param of type 8 but no required field.
            - One integration with a param of type 0 and no required field.
            - One integration with a param of type 8 but required field set to False.
            - One integration with 3 param of type 8, one's required field is set to True and the other two are set to False.
    When
    - Calling the IsValidCheckboxParamValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should fail all except test_param 2 & 4.
    """
    results = IsValidCheckboxParamValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidCheckboxParamValidator_fix():
    """
    Given
        An integration with invalid proxy & insecure params.
    When
    - Calling the IsValidCheckboxParamValidator fix function.
    Then
        - Make sure that all the relevant fields were added/fixed and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_param_4",
                    "type": 8,
                    "display": "test param 4",
                    "required": True,
                },
                {
                    "name": "test_param_5",
                    "type": 8,
                    "display": "test param 5",
                    "required": False,
                },
                {
                    "name": "test_param_6",
                    "type": 8,
                    "display": "test param 6",
                    "required": False,
                },
            ]
        ],
    )
    validator = IsValidCheckboxParamValidator()
    validator.misconfigured_checkbox_params_by_integration[content_item.name] = [
        "test_param_5",
        "test_param_6",
    ]
    assert (
        validator.fix(content_item).message
        == "Set required field of the following params was set to True: test_param_5, test_param_6."
    )
    assert all([param.required for param in content_item.params])


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_integration_object()], 0, []),
        (
            [create_integration_object(["category"], [""])],
            1,
            [
                "The Integration's category (empty category section) doesn't match the standard,\nplease make sure that the field is a category from the following options: Network Security, Utilities, Forensics & Malware Analysis."
            ],
        ),
        (
            [
                create_integration_object(["category"], ["Utilities"]),
                create_integration_object(["category"], ["Random Category..."]),
                create_integration_object(),
            ],
            1,
            [
                "The Integration's category (Random Category...) doesn't match the standard,\nplease make sure that the field is a category from the following options: Network Security, Utilities, Forensics & Malware Analysis."
            ],
        ),
    ],
)
def test_IsValidCategoryValidator_is_valid(
    mocker,
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items.
        - Case 1: One integration with n valid category.
        - Case 2: One integration with an empty category field.
        - Case 3: Three integrations:
            - Two integrations with a valid category.
            - One integration with an invalid category.
    When
    - Calling the IsValidCategoryValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Should fail only the pack_metadata with the "Random Category..."
    """

    mocker.patch(
        "demisto_sdk.commands.validate.validators.IN_validators.IN104_is_valid_category.get_current_categories",
        return_value=["Network Security", "Utilities", "Forensics & Malware Analysis"],
    )
    results = IsValidCategoryValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["commonfields.id", "script.beta"],
                    values=["contain_beta", False],
                ),
                create_integration_object(
                    paths=["commonfields.id", "script.beta"], values=["test", True]
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["commonfields.id", "script.beta"], values=["beta_test", True]
                ),
                create_integration_object(
                    paths=["commonfields.id", "script.beta"], values=["test beta", True]
                ),
            ],
            2,
            [
                "The ID field (beta_test) contains the word 'beta', make sure to remove it.",
                "The ID field (test beta) contains the word 'beta', make sure to remove it.",
            ],
        ),
    ],
)
def test_IsIdContainBetaValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two integration:
            - One non-beta integration with beta in id.
            - One beta integration without beta in id.
        - Case 2: Two integration:
            - One beta integration with id starting with beta.
            - One beta integration with beta in id.
    When
    - Calling the IsIdContainBetaValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail both.
    """
    results = IsIdContainBetaValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsIdContainBetaValidator_fix():
    """
    Given
        - Case 1: A beta integration with an ID containing the word beta in it.
    When
    - Calling the IsIdContainBetaValidator fix function.
    Then
        - Make sure the right ID was fixed correctly and that the right ID was returned.
    """
    content_item = create_integration_object(
        paths=["commonfields.id", "script.beta"], values=["test beta", True]
    )
    assert content_item.object_id == "test beta"
    assert (
        IsIdContainBetaValidator().fix(content_item).message
        == "Removed the word 'beta' from the ID, the new ID is: test."
    )
    assert content_item.object_id == "test"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["name", "script.beta"], values=["contain_beta", False]
                ),
                create_integration_object(
                    paths=["name", "script.beta"], values=["test", True]
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["name", "script.beta"], values=["beta_test", True]
                ),
                create_integration_object(
                    paths=["name", "script.beta"], values=["test beta", True]
                ),
            ],
            2,
            [
                "The name field (beta_test) contains the word 'beta', make sure to remove it.",
                "The name field (test beta) contains the word 'beta', make sure to remove it.",
            ],
        ),
    ],
)
def test_IsNameContainBetaValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two integration:
            - One non-beta integration with beta in the name.
            - One beta integration without beta in the name.
        - Case 2: Two integration:
            - One beta integration with name starting with beta.
            - One beta integration with beta in the name.
    When
    - Calling the IsNameContainBetaValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail both.
    """
    results = IsNameContainBetaValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsNameContainBetaValidator_fix():
    """
    Given
        - Case 1: A beta integration with a name containing the word beta in it.
    When
    - Calling the IsNameContainBetaValidator fix function.
    Then
        - Make sure the right ID was fixed correctly and that the right name was returned.
    """
    content_item = create_integration_object(
        paths=["name", "script.beta"], values=["test beta", True]
    )
    assert content_item.name == "test beta"
    assert (
        IsNameContainBetaValidator().fix(content_item).message
        == "Removed the word 'beta' from the name field, the new name is: test."
    )
    assert content_item.name == "test"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["display", "script.beta"], values=["contain beta", True]
                ),
                create_integration_object(
                    paths=["display", "script.beta"], values=["test", False]
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["display", "script.beta"], values=["should fail", True]
                ),
            ],
            1,
            [
                "The display name (should fail) doesn't contain the word 'beta', make sure to add it.",
            ],
        ),
    ],
)
def test_IsDisplayContainBetaValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two integration:
            - One beta integration with beta in the display name.
            - One non-beta integration without beta in the display name.
        - Case 2: Two integration:
            - One beta integration without beta in the display name.
    When
    - Calling the IsDisplayContainBetaValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail.
    """
    results = IsDisplayContainBetaValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["script.commands"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_1_description",
                                    },
                                    {
                                        "name": "ip_2",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_2_description",
                                    },
                                ],
                                "outputs": [],
                            },
                        ]
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip_1",
                                "description": "ip command 1",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_1_description",
                                    },
                                    {
                                        "name": "ip_2",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_2_description",
                                    },
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_1_description",
                                    },
                                ],
                                "outputs": [],
                            }
                        ]
                    ],
                )
            ],
            1,
            [
                "The following commands contain duplicated arguments:\nCommand ip_1, contains multiple appearances of the following arguments ip_1.\nPlease make sure to remove the duplications."
            ],
        ),
    ],
)
def test_IsCommandArgsContainDuplicationsValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One integration without commands.
            - One integration with one command without duplicated args.
        - Case 2: One invalid integration with a command with 3 arguments Two of the same name and one different..
    When
    - Calling the IsCommandArgsContainDuplicationsValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail.
    """
    results = IsCommandArgsContainDuplicationsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[[]],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {"name": "test_1", "display": "a", "type": 1},
                            {"name": "test_1", "display": "a", "type": 1},
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following params are duplicated: test_1.\nPlease make sure your file doesn't contain duplications.",
            ],
        ),
    ],
)
def test_IsParamsContainDuplicationsValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One integration with params but without duplications.
            - One integration with empty params list.
        - Case 2: One invalid integration with a param with a name that return multiple name.
    When
    - Calling the IsParamsContainDuplicationsValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsParamsContainDuplicationsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["script.commands"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_1_description",
                                    },
                                    {
                                        "name": "ip_2",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_2_description",
                                    },
                                ],
                                "outputs": [],
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "path_1",
                                        "description": "description_1",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextPath": "path_2",
                                        "description": "description_2",
                                    },
                                ],
                            },
                        ]
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "path_1",
                                        "description": "description_1",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextpath": "path_2",
                                        "description": "description_2",
                                    },
                                    {
                                        "name": "output_3",
                                        "description": "description_3",
                                    },
                                    {
                                        "name": "output_4",
                                        "contextPath": "path_4",
                                        "description": "description_4",
                                    },
                                ],
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip_1",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextpath": "path_1",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "ip_2",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [],
                                "outputs": [
                                    {"name": "output_1", "description": "description_1"}
                                ],
                            },
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following commands include outputs with context path different from missing contextPath, please make sure to add: ip.",
                "The following commands include outputs with context path different from missing contextPath, please make sure to add: ip_1, ip_2.",
            ],
        ),
    ],
)
def test_IsValidContextPathValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without commands.
            - One integration with a command with empty outputs.
            - One integration with one command with valid outputs.
        - Case 2: Two invalid integrations:
            - One integration with one command with multiple malformed outputs.
            - One integration with two commands with malformed outputs.
    When
    - Calling the IsValidContextPathValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail all.
    """
    results = IsValidContextPathValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                        ]
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                                "display": "test",
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                                "display": "test",
                            },
                            {
                                "name": "test_2",
                                "type": 17,
                                "required": False,
                                "display": "display",
                            },
                            {
                                "name": "test_3",
                                "type": 17,
                                "required": False,
                            },
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following params are expiration fields and therefore can't have a 'display' field. Make sure to remove the field for the following: test_1.",
                "The following params are expiration fields and therefore can't have a 'display' field. Make sure to remove the field for the following: test_1, test_2.",
            ],
        ),
    ],
)
def test_ShouldHaveDisplayFieldValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without type 17 param.
            - One integration without params.
            - One integration with two params: one type 17 without display name and one type 8.
        - Case 2: Two invalid integrations:
            - One integration with two params: one type 17 with display name and one type 8.
            - One integration with three params: one type 17 without display name, and two type 17 with display name.
    When
    - Calling the ShouldHaveDisplayFieldValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all the type 17 with display names.
    """
    results = ShouldHaveDisplayFieldValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_ShouldHaveDisplayFieldValidator_fix():
    """
    Given
        - An integration with three params: one type 17 without display name, and two type 17 with display name.
    When
    - Calling the ShouldHaveDisplayFieldValidator fix function.
    Then
        - Make sure the display name was removed for all params and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_1",
                    "type": 17,
                    "required": False,
                    "display": "test",
                },
                {
                    "name": "test_2",
                    "type": 17,
                    "required": False,
                    "display": "display",
                },
                {
                    "name": "test_3",
                    "type": 17,
                    "required": False,
                },
            ]
        ],
    )
    validator = ShouldHaveDisplayFieldValidator()
    validator.invalid_params[content_item.name] = ["test_1", "test_2"]
    assert (
        validator.fix(content_item).message
        == "Removed display field for the following params: test_1, test_2."
    )
    assert not any(
        [(param.type == 17 and param.display) for param in content_item.params]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "test 2",
                            },
                        ]
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 10,
                                "required": False,
                            },
                            {
                                "name": "test_2",
                                "type": 10,
                                "required": False,
                                "display": "display",
                            },
                            {
                                "name": "test_3",
                                "type": 10,
                                "required": False,
                            },
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following params doesn't have a display field, please make sure to add one: test_2.",
                "The following params doesn't have a display field, please make sure to add one: test_1, test_3.",
            ],
        ),
    ],
)
def test_IsMissingDisplayFieldValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without type 17 param, all other params with display name.
            - One integration without params.
            - One integration with two params: one type 17 without display name and one type 8 with display name.
        - Case 2: Two invalid integrations:
            - One integration with two params: one type 17 and type params both without display name.
            - One integration with three params: Two type 10 without display name, and one type 10 with display name.
    When
    - Calling the IsMissingDisplayFieldValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all the type 8 / 10 without display names.
    """
    results = IsMissingDisplayFieldValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["configuration", "script.isfetch"],
                    values=[
                        [
                            {
                                "name": "max_fetch",
                                "type": 0,
                                "required": False,
                                "defaultvalue": 200,
                                "display": "Maximum incidents to fetch.",
                                "additionalinfo": "Maximum number of incidents per fetch. The default value is 200.",
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "test 2",
                            },
                        ],
                        True,
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["configuration", "script.isfetch"],
                    values=[
                        [
                            {
                                "name": "max_fetch",
                                "type": 0,
                                "required": False,
                                "display": "Maximum incidents to fetch.",
                                "additionalinfo": "Maximum number of incidents per fetch. The default value is 200.",
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                            },
                        ],
                        True,
                    ],
                ),
            ],
            1,
            [
                "The integration is a fetch integration with max_fetch param, please make sure the max_fetch param has a default value.",
            ],
        ),
    ],
)
def test_IsValidMaxFetchParamValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without max_fetch param.
            - One integration without params.
            - One fetch integration with max_fetch param with a default value.
        - Case 2: One invalid integration with max_fetch param without default value and another param that isn't max_fetch.
    When
    - Calling the IsValidMaxFetchParamValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all the type 8 / 10 without display names.
    """
    results = IsValidMaxFetchParamValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidMaxFetchParamValidator_fix():
    """
    Given
        - A fetching integration with two params: one is a max_fetch without default value and one isn't a max_fetch
    When
        - Calling the IsValidMaxFetchParamValidator fix function.
    Then
        - Make sure the defaultvalue was updated to the max_fetch param and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration", "script.isfetch"],
        values=[
            [
                {
                    "name": "max_fetch",
                    "type": 0,
                    "required": False,
                    "display": "Maximum incidents to fetch.",
                    "additionalinfo": "Maximum number of incidents per fetch. The default value is 200.",
                },
                {
                    "name": "test_2",
                    "type": 8,
                    "required": False,
                },
            ],
            True,
        ],
    )
    assert (
        IsValidMaxFetchParamValidator().fix(content_item).message
        == f"Added a 'defaultvalue = {DEFAULT_MAX_FETCH}' to the max_fetch param."
    )
    assert any(
        [
            (param.name == "max_fetch" and param.defaultvalue is not None)
            for param in content_item.params
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["configuration"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["configuration", "script.isfetch"],
                    values=[
                        [MAX_FETCH_PARAM, FIRST_FETCH_PARAM],
                        True,
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.isfetch"],
                    values=[True],
                ),
                create_integration_object(
                    paths=["configuration", "script.isfetch"],
                    values=[
                        [MAX_FETCH_PARAM],
                        True,
                    ],
                ),
                create_integration_object(
                    paths=["configuration", "script.isfetch"],
                    values=[
                        [FIRST_FETCH_PARAM],
                        True,
                    ],
                ),
            ],
            3,
            [
                "The integration is a fetch integration and missing the following params: max_fetch, first_fetch.",
                "The integration is a fetch integration and missing the following params: first_fetch.",
                "The integration is a fetch integration and missing the following params: max_fetch.",
            ],
        ),
    ],
)
def test_IsValidFetchIntegrationValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One none fetching integration without max_fetch or first_fetch params.
            - One none fetching integration without params.
            - One fetch integration with both first_fetch and max_fetch params.
         - Case 2: Three invalid integrations:
            - One integration without max_fetch & first_fetch params.
            - One integration without first_fetch param.
            - One integration without max_fetch param.

    When
    - Calling the IsValidFetchIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all:
            - First integration should fail due to both first_fetch & max_fetch missing.
            - Second integration should fail due to missing first_fetch.
            - Third integration should fail due to missing max_fetch.
    """
    results = IsValidFetchIntegrationValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidFetchIntegrationValidator_fix():
    """
    Given
        - A fetching integration without max_fetch & first_fetch params.
    When
        - Calling the IsValidFetchIntegrationValidator fix function.
    Then
        - Make sure that the params were added to the params list and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["script.isfetch"],
        values=[True],
    )
    validator = IsValidFetchIntegrationValidator()
    validator.missing_fetch_params[content_item.name] = {
        MAX_FETCH: MAX_FETCH_PARAM,
        FIRST_FETCH: FIRST_FETCH_PARAM,
    }
    assert (
        validator.fix(content_item).message
        == f"Added the following params to the integration: {MAX_FETCH}, {FIRST_FETCH}."
    )
    assert all(
        [param in content_item.params for param in [MAX_FETCH_PARAM, FIRST_FETCH_PARAM]]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["script.commands"],
                    values=[[]],
                ),
                create_integration_object(
                    paths=["script.commands", "script.ismappable"],
                    values=[
                        [GET_MAPPING_FIELDS_COMMAND],
                        True,
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.ismappable"],
                    values=[
                        True,
                    ],
                ),
            ],
            1,
            [
                f"The integration is a mappable integration and is missing the {GET_MAPPING_FIELDS_COMMAND_NAME} command. Please add the command."
            ],
        ),
    ],
)
def test_IsValidAsMappableIntegrationValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One none mappable integration with commands but no get-mapping-fields command.
            - One none mappable integration without commands.
            - One mappable integration with get-mapping-fields command.
         - Case 2: One invalid mappable integration without get-mapping-fields command.

    When
    - Calling the IsValidAsMappableIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidAsMappableIntegrationValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidAsMappableIntegrationValidator_fix():
    """
    Given
        - A mappable integration without get-mapping-fields command.
    When
        - Calling the IsValidAsMappableIntegrationValidator fix function.
    Then
        - Make sure that the command was added to the integration and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["script.ismappable"],
        values=[
            True,
        ],
    )
    assert (
        IsValidAsMappableIntegrationValidator().fix(content_item).message
        == f"Added the {GET_MAPPING_FIELDS_COMMAND_NAME} command to the integration."
    )
    assert [
        GET_MAPPING_FIELDS_COMMAND_NAME in command.name
        for command in content_item.commands
    ]


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["script.commands"],
                    values=[[]],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "arguments": [
                                    {
                                        "name": "test_1_arg_1",
                                        "default": True,
                                        "description": "test_1_arg_1_description",
                                    },
                                    {
                                        "name": "test_1_arg_2",
                                        "default": True,
                                        "description": "test_1_arg_2_description",
                                    },
                                    {
                                        "name": "test_1_arg_3",
                                        "description": "test_1_arg_3_description",
                                    },
                                ],
                            }
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following commands have more than 1 default arg, please make sure they have at most one: test_1."
            ],
        ),
    ],
)
def test_IsContainingMultipleDefaultArgsValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One integration with commands with multiple default args.
            - One integration without commands.
         - Case 2: One invalid integration with a command with multiple default args.

    When
    - Calling the IsContainingMultipleDefaultArgsValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsContainingMultipleDefaultArgsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )

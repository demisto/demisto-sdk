from typing import List

import pytest

from demisto_sdk.commands.common.constants import (
    COMMON_PARAMS_DISPLAY_NAME,
    COMMUNITY_SUPPORT,
    DEFAULT_MAX_FETCH,
    DEVELOPER_SUPPORT,
    ENDPOINT_FLEXIBLE_REQUIRED_ARGS,
    FEED_RELIABILITY,
    FIRST_FETCH_PARAM,
    GET_MAPPING_FIELDS_COMMAND,
    GET_MAPPING_FIELDS_COMMAND_NAME,
    MAX_FETCH_PARAM,
    PARTNER_SUPPORT,
    RELIABILITY_PARAM,
    SUPPORT_LEVEL_HEADER,
    XSOAR_SUPPORT,
    MarketplaceVersions,
    ParameterType,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN100_is_valid_proxy_and_insecure import (
    IsValidProxyAndInsecureValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN102_is_valid_checkbox_default_field import (
    IsValidCheckboxDefaultFieldValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN104_is_valid_category import (
    IsValidCategoryValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN106_is_valid_rep_command import (
    IsValidRepCommandValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN107_is_missing_reputation_output import (
    IsMissingReputationOutputValidator,
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
from demisto_sdk.commands.validate.validators.IN_validators.IN121_is_valid_fetch import (
    IsValidFetchValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN122_is_valid_feed_integration import (
    IsValidFeedIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN123_display_name_has_invalid_version import (
    IntegrationDisplayNameVersionedCorrectlyValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN124_is_hiddenable_param import (
    IsHiddenableParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN125_is_valid_max_fetch_param import (
    IsValidMaxFetchParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN126_is_valid_fetch_integration import (
    IsValidFetchIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN127_is_valid_deprecated_integration_display_name import (
    IsValidDeprecatedIntegrationDisplayNameValidator,
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
from demisto_sdk.commands.validate.validators.IN_validators.IN135_is_valid_param_display import (
    IsValidParamDisplayValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN139_is_name_contain_incident_in_core_pack import (
    IsNameContainIncidentInCorePackValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN141_is_valid_endpoint_command import (
    IsValidEndpointCommandValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN142_is_containing_default_additional_info import (
    IsContainingDefaultAdditionalInfoValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN144_is_rep_command_contain_is_array_argument import (
    IsRepCommandContainIsArrayArgumentValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN145_is_api_token_in_credential_type import (
    IsAPITokenInCredentialTypeValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN146_is_containing_from_license_in_params import (
    IsContainingFromLicenseInParamsValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN149_does_common_outputs_have_description import (
    DoesCommonOutputsHaveDescriptionValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN150_is_valid_display_for_siem_integration import (
    IsValidDisplayForSiemIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN151_is_none_command_args import (
    IsNoneCommandArgsValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN152_is_valid_default_value_for_checkbox_param import (
    IsValidDefaultValueForCheckboxParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN153_is_valid_url_default_value import (
    IsValidUrlDefaultValueValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN154_is_missing_reliability_param import (
    IsMissingReliabilityParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN156_is_valid_hidden_value import (
    IsValidHiddenValueValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN158_is_valid_description_for_non_deprecated_integration import (
    IsValidDescriptionForNonDeprecatedIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN159_is_valid_reputation_command_context_path_capitalization import (
    IsValidReputationCommandContextPathCapitalizationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN160_is_valid_display_name_for_non_deprecated_integration import (
    IsValidDisplayNameForNonDeprecatedIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN161_is_siem_integration_valid_marketplace import (
    IsSiemIntegrationValidMarketplaceValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN162_is_partner_collector_has_xsoar_support_level import (
    IsPartnerCollectorHasXsoarSupportLevelValidator,
)
from TestSuite.repo import ChangeCWD


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
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'false', the 'required' field should be 'False', and the 'type' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'false', the 'required' field should be 'False', and the 'type' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'false', the 'required' field should be 'False', and the 'type' field should be 8.",
                "The following params are invalid:\nThe proxy param display name should be 'Use system proxy settings', the 'defaultvalue' field should be 'false', the 'required' field should be 'False', and the 'type' field should be 8.",
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
        assert param.type == ParameterType.BOOLEAN.value
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
                                "name": "insecure",
                                "type": 8,
                                "display": "test param 5",
                                "required": True,
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
            1,
            [
                "The following checkbox params required field is set to True: test_param_4.\nMake sure to change it to False/remove the field."
            ],
        ),
    ],
)
def test_IsValidCheckboxDefaultFieldValidator_is_valid(
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
            - One integration with 3 param of type 8, one's required field is set to True, one's required field is set to True and the name is part of the required allowed params, and the other two are set to False.
    When
    - Calling the IsValidCheckboxDefaultFieldValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should fail only the first param of the last integration.
    """
    results = IsValidCheckboxDefaultFieldValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidCheckboxDefaultFieldValidator_fix():
    """
    Given
        An integration with invalid proxy & insecure params.
    When
    - Calling the IsValidCheckboxDefaultFieldValidator fix function.
    Then
        - Make sure that all the relevant fields were added/fixed and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_param",
                    "type": 8,
                    "display": "test param",
                    "required": True,
                },
            ]
        ],
    )
    assert content_item.params[0].required
    validator = IsValidCheckboxDefaultFieldValidator()
    validator.misconfigured_checkbox_params_by_integration[content_item.name] = [
        "test_param",
    ]
    assert (
        validator.fix(content_item).message
        == "Set required field of the following params was set to False: test_param."
    )
    assert not content_item.params[0].required


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
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "description": "test command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "test",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "test argument",
                                    },
                                ],
                                "outputs": [],
                            },
                            {
                                "name": "test_2",
                                "description": "test command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "test",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "test argument",
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
        - Case 1: Three valid integrations:
            - One integration without commands.
            - One integration with one command without duplicated args.
            - One integration with two commands, both have the same argument.
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
                                        "contextPath": "path_2",
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
                                        "contextPath": "path_1",
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
                "The following commands include outputs with missing contextPath, please make sure to add: ip.",
                "The following commands include outputs with missing contextPath, please make sure to add: ip_2.",
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
        [
            (param.type == ParameterType.EXPIRATION_FIELD and param.display)
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
            ["The following commands have multiple default arguments: test_1."],
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
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 17,
                                "required": False,
                                "display": "test 1",
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "Test 2",
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
                                "display": "test_1",
                            },
                            {
                                "name": "test_2",
                                "type": 17,
                                "required": False,
                                "display": "Test_2",
                            },
                            {
                                "name": "test_3",
                                "type": 17,
                                "required": False,
                                "display": "Test 3",
                            },
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following params are invalid. Integration parameters display field must start with capital letters and can't contain underscores ('_'): test 1.",
                "The following params are invalid. Integration parameters display field must start with capital letters and can't contain underscores ('_'): test_1, Test_2.",
            ],
        ),
    ],
)
def test_IsValidParamDisplayValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration with params, all with display name.
            - One integration without params.
            - One integration with one param without display name.
        - Case 2: Two invalid integrations:
            - One integration with two params: one invalid because it's starting with lowercase letter and one valid.
            - One integration with three params: one invalid because it's starting with lowercase letter and has underscore in the display name, one invalid because it has underscore in the display name, and one valid.
    When
    - Calling the IsValidParamDisplayValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail and mention only the invalid params in the message.
    """
    results = IsValidParamDisplayValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidParamDisplayValidator_fix():
    """
    Given
        An integration with 4 params:
        - One param with invalid display because it's starting with lowercase letter and has underscore.
        - One param with invalid display because it has underscore.
        - One param with valid display.
        - one param with invalid display because it's starting with lowercase letter.
    When
    - Calling the IsValidParamDisplayValidator fix function.
    Then
        - Make sure that the display field was modified correctly, and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_1",
                    "type": 17,
                    "required": False,
                    "display": "test_1",
                },
                {
                    "name": "test_2",
                    "type": 17,
                    "required": False,
                    "display": "Test_2",
                },
                {
                    "name": "test_3",
                    "type": 17,
                    "required": False,
                    "display": "Test 3",
                },
                {
                    "name": "test_4",
                    "type": 17,
                    "required": False,
                    "display": "test 4",
                },
            ]
        ],
    )
    validator = IsValidParamDisplayValidator()
    validator.invalid_params[content_item.name] = ["test_1", "Test_2", "test 4"]
    assert (
        validator.fix(content_item).message
        == "The following param displays has been modified: test_1 -> Test 1, Test_2 -> Test 2, test 4 -> Test 4."
    )
    assert not bool(
        validator.get_invalid_params(
            [param.display for param in content_item.params if param.display],
            content_item.name,
        )
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs, marketplaces",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["script.marketplaces", "script.isfetchevents"],
                    values=["marketplacev2", True],
                ),
            ],
            0,
            [],
            [MarketplaceVersions.MarketplaceV2, MarketplaceVersions.XSOAR],
        ),
        (
            [
                create_integration_object(
                    paths=["script.marketplaces", "script.isfetchevents"],
                    values=["marketplace", True],
                )
            ],
            1,
            [
                "The marketplaces field of this XSIAM integration is incorrect.\nThis field should have only the 'marketplacev2' value."
            ],
            [MarketplaceVersions.XSOAR],
        ),
    ],
)
def test_IsSiemIntegrationValidMarketplaceValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs, marketplaces
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One non siem integration.
            - One siem integration with the marketplacev2 tag.
        - Case 2: One invalid siem integration without marketplacev2 tag.
    When
    - Calling the IsSiemIntegrationValidMarketplaceValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    for content_item in content_items:
        content_item.marketplaces = marketplaces
    results = IsSiemIntegrationValidMarketplaceValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsSiemIntegrationValidMarketplaceValidator_fix():
    """
    Given
        A siem integration without marketplacev2 tag.
    When
    - Calling the IsSiemIntegrationValidMarketplaceValidator fix function.
    Then
        - Make sure that the marketplacev2 tag was added to the list of available marketplaces, and that the right message was returned.
    """
    content_item = create_integration_object(
        paths=["script.marketplaces", "script.isfetchevents"],
        values=["marketplace", True],
    )
    content_item.marketplaces = [MarketplaceVersions.MarketplaceV2]
    validator = IsSiemIntegrationValidMarketplaceValidator()
    assert (
        validator.fix(content_item).message
        == "Added the 'marketplacev2' entry to the integration's marketplaces list."
    )
    assert MarketplaceVersions.MarketplaceV2 in content_item.marketplaces


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["deprecated", "display"],
                    values=[True, "test (Deprecated)"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["deprecated", "display"],
                    values=[False, "test (Deprecated)"],
                )
            ],
            1,
            [
                "All integrations whose display_names end with `(Deprecated)` must have `deprecated:true`.\nPlease run demisto-sdk format --deprecate -i "
            ],
        ),
    ],
)
def test_IsValidDisplayNameForNonDeprecatedIntegrationValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One non deprecated integration.
            - One deprecated integration with deprecated display template.
        - Case 2: Two invalid integrations
            - One non deprecated integration with deprecated display template.
    When
    - Calling the IsValidDisplayNameForNonDeprecatedIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidDisplayNameForNonDeprecatedIntegrationValidator().is_valid(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            expected_msg in result.message
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
                    paths=["deprecated", "description"],
                    values=[True, "Deprecated. No available replacement."],
                ),
                create_integration_object(
                    paths=["deprecated", "description"],
                    values=[True, "Deprecated. Use test_2 FTK instead."],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["deprecated", "description"],
                    values=[False, "Deprecated. No available replacement."],
                ),
                create_integration_object(
                    paths=["deprecated", "description"],
                    values=[False, "Deprecated. Use test_2 FTK instead."],
                ),
            ],
            2,
            [
                "All integrations whose description states are deprecated, must have `deprecated:true`.\nPlease run demisto-sdk format --deprecate -i",
                "All integrations whose description states are deprecated, must have `deprecated:true`.\nPlease run demisto-sdk format --deprecate -i",
            ],
        ),
    ],
)
def test_IsValidDescriptionForNonDeprecatedIntegrationValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One non deprecated integration.
            - Two deprecated integrations with deprecated description templates.
        - Case 2: Two invalid integrations
            - Two non deprecated integrations with deprecated description templates.
    When
    - Calling the IsValidDescriptionForNonDeprecatedIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidDescriptionForNonDeprecatedIntegrationValidator().is_valid(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            expected_msg in result.message
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
                    paths=["configuration", "script.feed"],
                    values=[[RELIABILITY_PARAM], True],
                ),
                create_integration_object(
                    paths=["configuration", "script.commands"],
                    values=[
                        [RELIABILITY_PARAM],
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip arg description",
                                    }
                                ],
                                "outputs": [],
                            }
                        ],
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.feed"],
                    values=[True],
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
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip arg description",
                                    }
                                ],
                                "outputs": [],
                            }
                        ]
                    ],
                ),
            ],
            2,
            [
                "Feed integrations and integrations with reputation commands must implement a reliability parameter, make sure to add one.",
                "Feed integrations and integrations with reputation commands must implement a reliability parameter, make sure to add one.",
            ],
        ),
    ],
)
def test_IsMissingReliabilityParamValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without reliability param and with no need for it.
            - One feed integration with reliability param.
            - One integration with reliability param and reputation command.
        - Case 2: Two invalid integrations:
            - One feed integration without reliability param.
            - One integration without reliability param and with reputation command.
    When
    - Calling the IsMissingReliabilityParamValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsMissingReliabilityParamValidator().is_valid(content_items)
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
                                "name": "url",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "defaultvalue": "https://test.com",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "url",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "defaultvalue": "www.test.com",
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
                    values=[
                        [
                            {
                                "name": "url",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "defaultvalue": "http://test.com",
                            }
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following params have an invalid default value. If possible, replace the http prefix with https: url.",
            ],
        ),
    ],
)
def test_IsValidUrlDefaultValueValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One integration without any URL param.
            - One integration without params.
            - One integration with URL param with default value starting with https.
            - One integration with URL param with default value not starting with https nor http.
        - Case 2: One invalid integration with URL starting with http.
    When
    - Calling the IsValidUrlDefaultValueValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsValidUrlDefaultValueValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidUrlDefaultValueValidator_fix():
    """
    Given
        An integration with url param with a default value starting with http.
    When
    - Calling the IsValidUrlDefaultValueValidator fix function.
    Then
        - Make sure that the default value is now starting with https, and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "url",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                    "defaultvalue": "http://test.com",
                }
            ]
        ],
    )
    validator = IsValidUrlDefaultValueValidator()
    validator.invalid_params[content_item.name] = ["url"]
    assert content_item.params[0].defaultvalue.startswith("http:")
    assert (
        validator.fix(content_item).message
        == "Changed the following params default value to include the https prefix: url."
    )
    assert not content_item.params[0].defaultvalue.startswith("http:")


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
                                "name": "test",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                                "defaultvalue": "false",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                                "defaultvalue": "true",
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
                    values=[
                        [
                            {
                                "name": "test",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                                "defaultvalue": False,
                            },
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                                "defaultvalue": "something wrong",
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test",
                                "type": 8,
                                "required": False,
                                "display": "test display",
                                "defaultvalue": True,
                            }
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following checkbox params have invalid defaultvalue: test, test_2.\nUse a boolean represented as a lowercase string, e.g defaultvalue: 'true'",
                "The following checkbox params have invalid defaultvalue: test.\nUse a boolean represented as a lowercase string, e.g defaultvalue: 'true'",
            ],
        ),
    ],
)
def test_IsValidDefaultValueForCheckboxParamValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One integration without any type 8 param.
            - One integration with type 8 param without default value.
            - One integration with type 8 param with default value set to 'false'.
            - One integration with type 8 param with default value set to 'true'.
        - Case 2: Two invalid integrations:
            - One integration with two type 8 params: one with default value set to False, and one to something that isn't true/false .
            - One integration with two type 8 params: one with default value set to True.
    When
    - Calling the IsValidDefaultValueForCheckboxParamValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsValidDefaultValueForCheckboxParamValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidDefaultValueForCheckboxParamValidator_fix():
    """
    Given
        An integration with 3 invalid checkbox params default values.
    When
    - Calling the IsValidDefaultValueForCheckboxParamValidator fix function.
    Then
        - Make sure that the default values are now correct, and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_1",
                    "type": 8,
                    "required": True,
                    "display": "test display",
                    "defaultvalue": False,
                },
                {
                    "name": "test_2",
                    "type": 8,
                    "required": True,
                    "display": "test display",
                    "defaultvalue": "something wrong",
                },
                {
                    "name": "test_3",
                    "type": 8,
                    "required": False,
                    "display": "test display",
                    "defaultvalue": True,
                },
            ]
        ],
    )
    validator = IsValidDefaultValueForCheckboxParamValidator()
    validator.invalid_params[content_item.name] = ["test_1", "test_2", "test_3"]
    assert all(
        [
            param.defaultvalue not in (None, "true", "false")
            for param in content_item.params
        ]
    )
    assert (
        validator.fix(content_item).message
        == "Changed the default values of the following checkbox params: param test_1 default value was changed to false.\nparam test_2 default value was changed to None.\nparam test_3 default value was changed to true."
    )
    assert all(
        [param.defaultvalue in (None, "true", "false") for param in content_item.params]
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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "test",
                                "description": "test command",
                                "deprecated": False,
                                "arguments": [],
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "test",
                                "description": "test command",
                                "deprecated": False,
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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "test",
                                "description": "test command",
                                "deprecated": False,
                                "arguments": None,
                            }
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following commands arguments are None: test.\nIf the command has no arguments, use `arguments: []` or remove the `arguments` field."
            ],
        ),
    ],
)
def test_IsNoneCommandArgsValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One integration with valid commands with non-empty arguments list.
            - One integration with commands.
            - One integration with a command with arguments = empty list.
            - One integration with a command without arguments field.
        - Case 2: An invalid integration with command with arguments field = None.
    When
    - Calling the IsNoneCommandArgsValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsNoneCommandArgsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsNoneCommandArgsValidator_fix():
    """
    Given
        An integration with command with arguments field = None.
    When
    - Calling the IsNoneCommandArgsValidator fix function.
    Then
        - Make sure that the arguments field was set to an empty list and that the right fix message was returned.
    """
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[
            [
                {
                    "name": "test",
                    "description": "test command",
                    "deprecated": False,
                    "arguments": None,
                }
            ]
        ],
    )
    assert (
        content_item.data.get("script", {}).get("commands", [])[0].get("arguments")
        is None
    )
    validator = IsNoneCommandArgsValidator()
    IsNoneCommandArgsValidator.invalid_commands[content_item.name] = ["test"]
    assert (
        validator.fix(content_item).message
        == "Set an empty list value to the following commands arguments: test."
    )
    assert (
        content_item.data.get("script", {}).get("commands", [])[0].get("arguments")
        == []
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["display", "script.isfetchevents"],
                    values=["test Event Collector", True],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["display", "script.isfetchevents"],
                    values=["test", True],
                ),
                create_integration_object(
                    paths=["display", "script.isfetchevents"],
                    values=["Event Collector test", True],
                ),
            ],
            2,
            [
                "The integration is a siem integration with invalid display name (test). Please make sure the display name ends with 'Event Collector'",
                "The integration is a siem integration with invalid display name (Event Collector test). Please make sure the display name ends with 'Event Collector'",
            ],
        ),
    ],
)
def test_IsValidDisplayForSiemIntegrationValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One non siem integration with display name not ending with 'Event Collector'.
            - One siem integration with display name ending with 'Event Collector'.
        - Case 2: Two invalid integrations:
            - One siem integration with display name without 'Event Collector'.
            - One siem integration with display name starting with 'Event Collector'.
    When
    - Calling the IsValidDisplayForSiemIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidDisplayForSiemIntegrationValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidDisplayForSiemIntegrationValidator_fix():
    """
    Given
        A siem integration without Event Collector suffix in the display name.
    When
    - Calling the IsValidDisplayForSiemIntegrationValidator fix function.
    Then
        - Make sure that the Event Collector was added to the display name, and that the right message was returned.
    """
    content_item = create_integration_object(
        paths=["display", "script.isfetchevents"],
        values=["test", True],
    )
    assert content_item.display_name == "test"
    validator = IsValidDisplayForSiemIntegrationValidator()
    assert (
        validator.fix(content_item).message
        == "Added the 'Event Collector' suffix to the display name, the new display name is test Event Collector."
    )
    assert content_item.display_name == "test Event Collector"


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
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "test 1",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextPath": "Test.Test_2",
                                        "description": "This is test 2 output.",
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
                                "arguments": [
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_1_description",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextPath": "Test.Test_2",
                                        "description": "description_2",
                                    },
                                    {
                                        "name": "output_3",
                                        "contextPath": "Test.Test_3",
                                        "description": "",
                                    },
                                ],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "url_description",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "",
                                    },
                                ],
                            },
                        ]
                    ],
                )
            ],
            1,
            [
                "The following commands are missing description for the following contextPath: The command ip is missing a description for the following contextPath: Test.Test_1, Test.Test_3\nThe command url is missing a description for the following contextPath: Test.Test_1"
            ],
        ),
    ],
)
def test_DoesCommonOutputsHaveDescriptionValidator_is_valid(
    mocker, content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without default outputs in any of the command outputs.
            - One integration without commands.
            - One integration with default outputs with/without the same template as in the json file.
        - Case 2: One invalid integration with several commands with several empty outputs for default contextPaths.
    When
    - Calling the DoesCommonOutputsHaveDescriptionValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.IN_validators.IN149_does_common_outputs_have_description.get_default_output_description",
        return_value={
            "Test.Test_1": "This is test 1 output.",
            "Test.Test_2": "This is test 2 output.",
            "Test.Test_3": "This is test 3 output.",
        },
    )
    results = DoesCommonOutputsHaveDescriptionValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_DoesCommonOutputsHaveDescriptionValidator_fix():
    """
    Given
        An invalid integration with several commands with several empty outputs for default contextPaths.
    When
    - Calling the DoesCommonOutputsHaveDescriptionValidator fix function.
    Then
        - Make sure that there're no empty descriptions for default contextPaths, and that the right message was returned.
    """
    content_item = create_integration_object(
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
                    ],
                    "outputs": [
                        {
                            "name": "output_1",
                            "contextPath": "Test.Test_1",
                            "description": "",
                        },
                        {
                            "name": "output_2",
                            "contextPath": "Test.Test_2",
                            "description": "description_2",
                        },
                        {
                            "name": "output_3",
                            "contextPath": "Test.Test_3",
                            "description": "",
                        },
                    ],
                },
                {
                    "name": "url",
                    "description": "url command",
                    "deprecated": False,
                    "arguments": [
                        {
                            "name": "url",
                            "default": True,
                            "isArray": True,
                            "required": True,
                            "description": "url_description",
                        },
                    ],
                    "outputs": [
                        {
                            "name": "output_1",
                            "contextPath": "Test.Test_1",
                            "description": "",
                        },
                    ],
                },
            ]
        ],
    )
    validator = DoesCommonOutputsHaveDescriptionValidator()
    validator.invalid_commands[content_item.name] = {
        "ip": ["Test.Test_1", "Test.Test_3"],
        "url": ["Test.Test_1"],
    }
    validator.default.update(
        {
            "Test.Test_1": "This is test 1 output.",
            "Test.Test_2": "This is test 2 output.",
            "Test.Test_3": "This is test 3 output.",
        }
    )
    assert (
        validator.fix(content_item).message
        == "Added description for the following outputs: \n\tThe command ip: \n\t\tThe contextPath Test.Test_1 description is now: This is test 1 output.\n\t\tThe contextPath Test.Test_3 description is now: This is test 3 output.\n\tThe command url: \n\t\tThe contextPath Test.Test_1 description is now: This is test 1 output."
    )
    # Validate that for all items that appear in the default field there're no empty descriptions.
    assert all(
        [
            all(
                [
                    (output.contextPath in validator.default and output.description)
                    for output in command.outputs
                ]
            )
            for command in content_item.commands
        ]
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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "endpoint",
                                "description": "endpoint command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_description",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "test 1",
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
                                "name": "endpoint",
                                "description": "endpoint command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_description",
                                    },
                                    {
                                        "name": "hostname",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_description",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "test 1",
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
                                "name": "endpoint",
                                "description": "endpoint command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip_1",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip_description",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Test.Test_1",
                                        "description": "",
                                    },
                                ],
                            }
                        ]
                    ],
                )
            ],
            1,
            [
                f"At least one of these {', '.join(ENDPOINT_FLEXIBLE_REQUIRED_ARGS)} arguments is required for endpoint command."
            ],
        ),
    ],
)
def test_IsValidEndpointCommandValidator_is_valid(
    mocker, content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One integration without endpoint commands.
            - One integration without commands.
            - One integration with endpoint command with one argument from the list.
            - One integration with endpoint command with more than one argument from the list.
        - Case 2: One invalid integration with endpoint command without any argument from the list.
    When
    - Calling the IsValidEndpointCommandValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.IN_validators.IN149_does_common_outputs_have_description.get_default_output_description",
        return_value={
            "Test.Test_1": "This is test 1 output.",
            "Test.Test_2": "This is test 2 output.",
            "Test.Test_3": "This is test 3 output.",
        },
    )
    results = IsValidEndpointCommandValidator().is_valid(content_items)
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
                                "name": "API key",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "The API Key to use for the connection.",
                            },
                            {
                                "name": "Source Reliability",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "Reliability of the source providing the intelligence data.",
                            },
                            {
                                "name": "Incident Type",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "The default incident type to create.",
                            },
                            {
                                "name": "Fetch Incidents",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "When set to true, this integration instance will pull incidents.",
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
                                "name": "API key",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "",
                            },
                            {
                                "name": "Source Reliability",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "additional info different from the template.",
                            },
                            {
                                "name": "Incident Type",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "additionalinfo": "The default incident type to create.",
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "API key",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                            {
                                "name": "Source Reliability",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                            {
                                "name": "Incident Type",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                            {
                                "name": "Fetch Incidents",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                        ]
                    ],
                ),
            ],
            2,
            [
                "The integration contains params with missing/malformed additionalinfo fields:\nThe aditionalinfo field of API key should be: The API Key to use for the connection.\nThe aditionalinfo field of Source Reliability should be: Reliability of the source providing the intelligence data.",
                "The integration contains params with missing/malformed additionalinfo fields:\nThe aditionalinfo field of API key should be: The API Key to use for the connection.\nThe aditionalinfo field of Source Reliability should be: Reliability of the source providing the intelligence data.\nThe aditionalinfo field of Incident Type should be: The default incident type to create.\nThe aditionalinfo field of Fetch Incidents should be: When set to true, this integration instance will pull incidents.",
            ],
        ),
    ],
)
def test_IsContainingDefaultAdditionalInfoValidator_is_valid(
    mocker,
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without any of the params.
            - One integration without params.
            - One integration with all the params in the right format.
        - Case 2: Two invalid integrations:
            - One integration with three params:
                - One param with an empty additionalinfo.
                - One param with a malformed additionalinfo.
                - One param with a valid additionalinfo.
            - One integration with all four params, all missing addiotionalinfo field.
    When
    - Calling the IsContainingDefaultAdditionalInfoValidator is valid function.
    Then
        - Make sure the validation fail when it needs to, only the relevant params are being caught ,and that the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.IN_validators.IN142_is_containing_default_additional_info.load_default_additional_info_dict",
        return_value={
            "API key": "The API Key to use for the connection.",
            "Fetch Incidents": "When set to true, this integration instance will pull incidents.",
            "Incident Type": "The default incident type to create.",
            "Source Reliability": "Reliability of the source providing the intelligence data.",
        },
    )
    results = IsContainingDefaultAdditionalInfoValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsContainingDefaultAdditionalInfoValidator_fix():
    """
    Given
        An integration with all four params missing additional info.
    When
    - Calling the IsContainingDefaultAdditionalInfoValidator fix function.
    Then
        - Make sure that all the additionalinfo fields of the mentioned params now match the standards, and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "API key",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                },
                {
                    "name": "Source Reliability",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                },
                {
                    "name": "Incident Type",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                },
                {
                    "name": "Fetch Incidents",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                },
            ]
        ],
    )
    validator = IsContainingDefaultAdditionalInfoValidator()
    validator.invalid_params[content_item.name] = {
        "API key": "The API Key to use for the connection.",
        "Fetch Incidents": "When set to true, this integration instance will pull incidents.",
        "Incident Type": "The default incident type to create.",
        "Source Reliability": "Reliability of the source providing the intelligence data.",
    }
    assert not any([param.additionalinfo for param in content_item.params])
    assert (
        validator.fix(content_item).message
        == "Fixed the following params additionalinfo fields:ֿ\nThe aditionalinfo field of API key is now: The API Key to use for the connection.\nThe aditionalinfo field of Fetch Incidents is now: When set to true, this integration instance will pull incidents.\nThe aditionalinfo field of Incident Type is now: The default incident type to create.\nThe aditionalinfo field of Source Reliability is now: Reliability of the source providing the intelligence data."
    )
    assert all(
        [
            param.additionalinfo
            == validator.invalid_params[content_item.name][param.name]
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
                    paths=["deprecated", "display"],
                    values=[True, "test (Deprecated)"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["deprecated", "display"],
                    values=[True, "test"],
                )
            ],
            1,
            [
                "The integration is deprecated, make sure the display name (test) ends with (Deprecated)."
            ],
        ),
    ],
)
def test_IsValidDeprecatedIntegrationDisplayNameValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One non deprecated integration.
            - One deprecated integration with deprecated display template.
        - Case 2: Two invalid integrations
            - One deprecated integration without deprecated display template.
    When
    - Calling the IsValidDeprecatedIntegrationDisplayNameValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidDeprecatedIntegrationDisplayNameValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            expected_msg in result.message
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidDeprecatedIntegrationDisplayNameValidator_fix():
    """
    Given
        A deprecated integration with display name without the (Deprecated) suffix.
    When
    - Calling the IsValidDeprecatedIntegrationDisplayNameValidator fix function.
    Then
        - Make sure that the (Deprecated) suffix was added to the display name and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["deprecated", "display"],
        values=[True, "test"],
    )
    assert not content_item.display_name.endswith("(Deprecated)")
    validator = IsValidDeprecatedIntegrationDisplayNameValidator()
    assert (
        validator.fix(content_item).message
        == "Added the (Deprecated) suffix to the integration display name: test (Deprecated)."
    )
    assert content_item.display_name.endswith("(Deprecated)")


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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [],
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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "nothing",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "nothing description.",
                                    }
                                ],
                                "outputs": [],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "url description.",
                                    }
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
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": False,
                                        "required": True,
                                        "description": "nothing description.",
                                    }
                                ],
                                "outputs": [],
                            }
                        ]
                    ],
                ),
            ],
            2,
            [
                "The following reputation commands are invalid:\n- The ip command arguments are invalid, it should include the following argument with the following configuration: name should be 'ip', the 'isArray' field should be True, and the default field should not be set to False.\nMake sure to fix the issue both in the yml and the code.",
                "The following reputation commands are invalid:\n- The ip command arguments are invalid, it should include the following argument with the following configuration: name should be 'ip', the 'isArray' field should be True, and the default field should not be set to False.\nMake sure to fix the issue both in the yml and the code.",
            ],
        ),
    ],
)
def test_IsValidRepCommandValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without reputation commands.
            - One integration without commands.
            - One integration with valid reputation command.
        - Case 2: Two invalid integrations:
            - One integration with one invalid ip command due to missing required default argument, and a valid url command.
            - One integration with one invalid ip command due to default set to False.
    When
    - Calling the IsValidRepCommandValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail only the ip commands for for both integrations.
    """
    results = IsValidRepCommandValidator().is_valid(content_items)
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
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "IP.Address",
                                        "contextPath": "IP.Address",
                                        "description": "IP.Address description",
                                    }
                                ],
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "file",
                                "description": "file command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "file",
                                        "default": True,
                                        "required": True,
                                        "description": "file description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "File.MD5",
                                        "contextPath": "File.MD5",
                                        "description": "File.MD5 description",
                                    },
                                    {
                                        "name": "File.SHA1",
                                        "contextPath": "File.SHA1",
                                        "description": "File.SHA1 description",
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
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "IP.Address",
                                        "contextPath": "IP.Address",
                                        "description": "IP.Address description",
                                    }
                                ],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "url description.",
                                    }
                                ],
                                "outputs": [],
                            },
                        ]
                    ],
                ),
            ],
            1,
            [
                "The integration contains invalid reputation command(s):\n\tThe command 'url' should include at least one of the output contextPaths: URL.Data.",
            ],
        ),
    ],
)
def test_IsMissingReputationOutputValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without reputation commands.
            - One integration without commands.
            - One integration with valid reputation command.
            - One integration with valid file command due to having one of the required outputs.
        - Case 2: One invalid integration with one valid ip command, and an invalid url command due to missing outputs.
    When
    - Calling the IsMissingReputationOutputValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsMissingReputationOutputValidator().is_valid(content_items)
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
                    paths=["script.feed"],
                    values=[True],
                ),
                create_integration_object(
                    paths=["script.feed", "configuration"],
                    values=[
                        True,
                        [
                            {
                                "name": "feed",
                                "defaultvalue": "true",
                                "display": "Fetch indicators",
                                "type": 8,
                            },
                            {
                                "name": "feedReputation",
                                "display": "Indicator Reputation",
                                "type": 18,
                                "options": ["None", "Good", "Suspicious", "Bad"],
                                "additionalinfo": "Indicators from this integration instance will be marked with this reputation",
                            },
                            {
                                "name": FEED_RELIABILITY,
                                "display": "Source Reliability",
                                "type": 15,
                                "required": True,
                                "options": [
                                    "A - Completely reliable",
                                    "B - Usually reliable",
                                    "C - Fairly reliable",
                                    "D - Not usually reliable",
                                    "E - Unreliable",
                                    "F - Reliability cannot be judged",
                                ],
                                "additionalinfo": "Reliability of the source providing the intelligence data",
                                "defaultvalue": "C - Fairly reliable",
                            },
                            {
                                "name": "feedExpirationPolicy",
                                "display": "",
                                "type": 17,
                                "options": [
                                    "never",
                                    "interval",
                                    "indicatorType",
                                    "suddenDeath",
                                ],
                            },
                            {
                                "name": "feedExpirationInterval",
                                "display": "",
                                "type": 1,
                            },
                            {
                                "name": "feedFetchInterval",
                                "display": "Feed Fetch Interval",
                                "type": 19,
                            },
                            {
                                "name": "feedBypassExclusionList",
                                "display": "Bypass exclusion list",
                                "type": 8,
                                "additionalinfo": "When selected, the exclusion list is ignored for indicators from this feed. This means that if an indicator from this feed is on the exclusion list, the indicator might still be added to the system.",
                            },
                            {
                                "name": "feedTags",
                                "display": "Tags",
                                "type": 0,
                                "additionalinfo": "Supports CSV values.",
                            },
                            {
                                "name": "tlp_color",
                                "display": "Traffic Light Protocol Color",
                                "type": 15,
                                "additionalinfo": "The Traffic Light Protocol (TLP) designation to apply to indicators fetched from the feed",
                                "options": ["RED", "AMBER", "GREEN", "WHITE"],
                            },
                        ],
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["script.feed", "configuration"],
                    values=[
                        True,
                        [
                            {
                                "name": FEED_RELIABILITY,
                                "display": "Source Reliability",
                                "type": 15,
                                "required": True,
                                "additionalinfo": "Reliability of the source providing the intelligence data",
                                "defaultvalue": "C - Fairly reliable",
                            },
                            {
                                "name": "feedExpirationPolicy",
                                "display": "",
                                "type": 17,
                            },
                            {
                                "name": "feedExpirationInterval",
                                "display": "",
                                "type": 1,
                            },
                        ],
                    ],
                ),
                create_integration_object(
                    paths=["script.feed", "configuration"],
                    values=[
                        True,
                        [
                            {
                                "name": "feed",
                                "defaultvalue": "false",
                                "display": "Fetch indicators",
                                "type": 8,
                            },
                            {
                                "name": "feedReputation",
                                "display": "Indicator Reputation test failure",
                                "type": 18,
                                "options": ["None", "Good", "Suspicious", "Bad"],
                                "additionalinfo": "Indicators from this integration instance will be marked with this reputation",
                            },
                            {
                                "name": FEED_RELIABILITY,
                                "display": "Source Reliability",
                                "type": 16,
                                "required": True,
                                "options": [
                                    "A - Completely reliable",
                                    "B - Usually reliable",
                                    "C - Fairly reliable",
                                    "D - Not usually reliable",
                                    "E - Unreliable",
                                    "F - Reliability cannot be judged",
                                ],
                                "additionalinfo": "Reliability of the source providing the intelligence data",
                                "defaultvalue": "C - Fairly reliable",
                            },
                        ],
                    ],
                ),
            ],
            2,
            [
                "The integration is a feed integration with malformed params: The param 'feedReliability' should be in the following structure: \n\tThe field 'display' must be equal 'Source Reliability'.\n\tThe field 'type' must be equal '15'.\n\tThe field 'required' must be equal 'True'.\n\tThe field 'options' must be equal '['A - Completely reliable', 'B - Usually reliable', 'C - Fairly reliable', 'D - Not usually reliable', 'E - Unreliable', 'F - Reliability cannot be judged']'.\n\tThe field 'additionalinfo' must appear and contain 'Reliability of the source providing the intelligence data'.\nThe param 'feedExpirationPolicy' should be in the following structure: \n\tThe field 'display' must be equal ''.\n\tThe field 'type' must be equal '17'.\n\tThe field 'options' must be equal '['never', 'interval', 'indicatorType', 'suddenDeath']'.",
                "The integration is a feed integration with malformed params: The param 'feed' should be in the following structure: \n\tThe field 'defaultvalue' must be equal 'true'.\n\tThe field 'display' must be equal 'Fetch indicators'.\n\tThe field 'type' must be equal '8'.\nThe param 'feedReputation' should be in the following structure: \n\tThe field 'display' must be equal 'Indicator Reputation'.\n\tThe field 'type' must be equal '18'.\n\tThe field 'options' must be equal '['None', 'Good', 'Suspicious', 'Bad']'.\n\tThe field 'additionalinfo' must appear and contain 'Indicators from this integration instance will be marked with this reputation'.\nThe param 'feedReliability' should be in the following structure: \n\tThe field 'display' must be equal 'Source Reliability'.\n\tThe field 'type' must be equal '15'.\n\tThe field 'required' must be equal 'True'.\n\tThe field 'options' must be equal '['A - Completely reliable', 'B - Usually reliable', 'C - Fairly reliable', 'D - Not usually reliable', 'E - Unreliable', 'F - Reliability cannot be judged']'.\n\tThe field 'additionalinfo' must appear and contain 'Reliability of the source providing the intelligence data'.",
            ],
        ),
    ],
)
def test_IsValidFeedIntegrationValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One none feed integration.
            - One feed integration without feed params at all.
            - One feed integration with all feed params in the right standards..
        - Case 2: Two invalid integrations:
            - One feed integration with feedReliability and feedExpirationPolicy without options field and valid feedExpirationInterval param.
            - One feed integration with feed param with malformed defaultvalue, feedReputation parma with malformed display, and feedReliability param with malformed type.
    When
    - Calling the IsValidFeedIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail and mention only the format of feedReliability and feedExpirationPolicy in the first msg and feed, feedReputation, and feedReliability in the second msg.
    """
    results = IsValidFeedIntegrationValidator().is_valid(content_items)
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
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "longRunning",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": True,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "non_hiddenable_param",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": False,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "longRunning",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "true",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "non_hiddenable_param",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": ["xsoar"],
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "type": 4,
                                "display": "API key",
                                "hidden": True,
                                "name": "test_old",
                            },
                            {
                                "type": 9,
                                "displaypassword": "API key",
                                "name": "test_new",
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
                                "name": "non_hiddenable_param",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": True,
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "type": 1,
                                "display": "API key",
                                "hidden": True,
                                "name": "test_old",
                            },
                            {
                                "type": 9,
                                "displaypassword": "API key",
                                "name": "test_new",
                            },
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "non_hiddenable_param",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "true",
                            }
                        ]
                    ],
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "non_hiddenable_param",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": [
                                    "xsoar",
                                    "marketplacev2",
                                    "xpanse",
                                    "xsoar_saas",
                                    "xsoar_on_prem",
                                ],
                            },
                            {
                                "type": 4,
                                "display": "API key",
                                "hidden": True,
                                "name": "test_old",
                            },
                        ]
                    ],
                ),
            ],
            4,
            [
                "The following fields are hidden and cannot be hidden, please unhide them: non_hiddenable_param.",
                "The following fields are hidden and cannot be hidden, please unhide them: test_old.",
                "The following fields are hidden and cannot be hidden, please unhide them: non_hiddenable_param.",
                "The following fields are hidden and cannot be hidden, please unhide them: non_hiddenable_param, test_old.",
            ],
        ),
    ],
)
def test_IsHiddenableParamValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Five valid integrations:
            - One integration with a hiddenable param with hidden value = True.
            - One integration with a non-hiddenable param with hidden value = False.
            - One integration with a hiddenable param with hidden value = 'true'.
            - One integration with a non-hiddenable param with hidden value = [xsoar].
            - One integration with a non-hiddenable param with hidden value = True and type = 4, with a type 9 replacement.
        - Case 1: Four invalid integrations:
            - One integration with a non-hiddenable param with hidden value = True.
            - One integration with a non-hiddenable param with hidden value = True and type not in 0,4,12,14, with a type 9 replacement.
            - One integration with a non-hiddenable param with hidden value = 'true'.
            - One integration with a non-hiddenable param with hidden value = all market places and another hidden type 4 param without type 9 replacement.
    When
    - Calling the IsHiddenableParamValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsHiddenableParamValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsHiddenableParamValidator_fix():
    """
    Given
        An integration with a non-hiddenable param with hidden value = all market places and another hidden type 4 param without type 9 replacement.
    When
    - Calling the IsHiddenableParamValidator fix function.
    Then
        - Make sure that the hidden params value was set to False, and that the right msg was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "non_hiddenable_param",
                    "type": 8,
                    "display": "test param",
                    "required": False,
                    "hidden": [
                        "xsoar",
                        "marketplacev2",
                        "xpanse",
                        "xsoar_saas",
                        "xsoar_on_prem",
                    ],
                },
                {"type": 4, "display": "API key", "hidden": True, "name": "test_old"},
            ]
        ],
    )
    validator = IsHiddenableParamValidator()
    validator.invalid_params[content_item.name] = ["test_old", "non_hiddenable_param"]
    assert (
        validator.fix(content_item).message
        == "Unhiddened the following params test_old, non_hiddenable_param."
    )
    assert all([not param.hidden for param in content_item.params])


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_param_1",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": True,
                            },
                            {
                                "name": "test_param_2",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": False,
                            },
                            {
                                "name": "test_param_3",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "true",
                            },
                            {
                                "name": "test_param_4",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "false",
                            },
                            {
                                "name": "test_param_5",
                                "type": 8,
                                "display": "test param",
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
                                "name": "test_param_1",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": [
                                    "xsoar",
                                    "marketplacev2",
                                    "xpanse",
                                    "xsoar_saas",
                                    "xsoar_on_prem",
                                ],
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
                    values=[
                        [
                            {
                                "name": "test_param_1",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": [False],
                            },
                            {
                                "name": "test_param_2",
                                "type": 8,
                                "display": "test param",
                                "hidden": ["some comment"],
                            },
                            {
                                "name": "test_param_3",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "flase",
                            },
                            {
                                "name": "test_param_4",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": "yes",
                            },
                            {
                                "name": "test_param_5",
                                "type": 8,
                                "display": "test param",
                                "required": False,
                                "hidden": 1,
                            },
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following params contain invalid hidden field values:\nThe param test_param_1 contains the following invalid hidden value: [False]\nThe param test_param_2 contains the following invalid hidden value: ['some comment']\nThe param test_param_3 contains the following invalid hidden value: flase\nThe param test_param_4 contains the following invalid hidden value: yes\nThe param test_param_5 contains the following invalid hidden value: 1\nThe valid values must be either a boolean, or a list of marketplace values.\n(Possible marketplace values: xsoar, marketplacev2, xpanse, xsoar_saas, xsoar_on_prem). Note that this param is not required, and may be omitted."
            ],
        ),
    ],
)
def test_IsValidHiddenValueValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Two valid integrations:
            - One integration with 5 params:
                - One param with hidden set to True (bool).
                - One param with hidden set to False (bool).
                - One param with hidden set to 'true' (str).
                - One param with hidden set to 'false' (str).
                - One param without hidden param.
            - One integration with 1 param:
                - One param with the list of valid marketplaces.
        - Case 1: One invalid integrations with 5 invalid params:
                - One param with hidden set to [False] (List[bool]).
                - One param with hidden set to "some comment" (str).
                - One param with hidden set to 'flase' (typo str).
                - One param with hidden set to 'yes' (str).
                - One param with hidden set to 1 (int).
    When
        - Calling the IsValidHiddenValueValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsValidHiddenValueValidator().is_valid(content_items)
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
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "IP.Address",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "file",
                                "description": "file command",
                                "arguments": [
                                    {
                                        "name": "file",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "file description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "File.MD5",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "url description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "URL.Address",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "email",
                                "description": "email command",
                                "arguments": [
                                    {
                                        "name": "email",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "email description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Email.Address",
                                        "description": "description_1",
                                    }
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
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "Ip.Address",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "file",
                                "description": "file command",
                                "arguments": [
                                    {
                                        "name": "file",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "file description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "file.MD5",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "url description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "UrL.Address",
                                        "description": "description_1",
                                    }
                                ],
                            },
                            {
                                "name": "email",
                                "description": "email command",
                                "arguments": [
                                    {
                                        "name": "email",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "email description.",
                                    }
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "emaIl.Address",
                                        "description": "description_1",
                                    }
                                ],
                            },
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following reputation commands contains invalid contextPath capitalization: The command 'ip' returns the following invalid reputation outputs:\n\tIp.Address for reputation: IP.\nThe capitalization is incorrect, for further information refer to https://xsoar.pan.dev/docs/integrations/context-and-outputs\nThe command 'file' returns the following invalid reputation outputs:\n\tfile.MD5 for reputation: File.\nThe capitalization is incorrect, for further information refer to https://xsoar.pan.dev/docs/integrations/context-and-outputs\nThe command 'url' returns the following invalid reputation outputs:\n\tUrL.Address for reputation: URL.\nThe capitalization is incorrect, for further information refer to https://xsoar.pan.dev/docs/integrations/context-and-outputs\nThe command 'email' returns the following invalid reputation outputs:\n\temaIl.Address for reputation: Email.\nThe capitalization is incorrect, for further information refer to https://xsoar.pan.dev/docs/integrations/context-and-outputs"
            ],
        ),
    ],
)
def test_IsValidReputationCommandContextPathCapitalizationValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: One valid integration with four valid commands:
            - ip command with valid IP contextPath prefix.
            - file command with valid File contextPath prefix.
            - url command with valid URL contextPath prefix.
            - email command with valid Email contextPath prefix.
        - Case 2: One invalid integration with four invalid commands:
            - ip command with invalid Ip contextPath prefix.
            - file command with invalid file contextPath prefix.
            - url command with invalid UrL contextPath prefix.
            - email command with invalid emaIl contextPath prefix.
    When
    - Calling the IsValidReputationCommandContextPathCapitalizationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsValidReputationCommandContextPathCapitalizationValidator().is_valid(
        content_items
    )
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
                create_integration_object(["marketplaces"], [["marketplacev2"]]),
                create_integration_object(["marketplaces"], [["xsoar"]]),
                create_integration_object(
                    ["marketplaces", "script.isfetch", "configuration"],
                    [
                        ["marketplacev2"],
                        True,
                        [
                            {
                                "display": "Alert type",
                                "name": "incidentType",
                                "type": 13,
                            },
                            {"display": "Fetch alerts", "name": "isFetch", "type": 8},
                        ],
                    ],
                ),
                create_integration_object(
                    ["marketplaces", "script.isfetch", "configuration"],
                    [
                        ["xsoar"],
                        True,
                        [
                            {
                                "display": "Incident type",
                                "name": "incidentType",
                                "type": 13,
                            },
                            {
                                "display": "Fetch incidents",
                                "name": "isFetch",
                                "type": 8,
                            },
                        ],
                    ],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    ["marketplaces", "script.isfetch"],
                    [
                        ["marketplacev2"],
                        True,
                    ],
                ),
                create_integration_object(
                    ["marketplaces", "script.isfetch"],
                    [
                        ["xsoar"],
                        True,
                    ],
                ),
                create_integration_object(
                    ["marketplaces", "script.isfetch", "configuration"],
                    [
                        ["marketplacev2"],
                        True,
                        [
                            {
                                "display": "Alert",
                                "name": "incidentType",
                                "type": 13,
                            },
                            {"display": "Fetch alerts", "name": "isFetch", "type": 1},
                        ],
                    ],
                ),
                create_integration_object(
                    ["marketplaces", "script.isfetch", "configuration"],
                    [
                        ["xsoar"],
                        True,
                        [
                            {
                                "display": "Incident type",
                                "name": "incidentType",
                                "type": 13,
                            },
                            {
                                "name": "isFetch",
                                "type": 8,
                            },
                        ],
                    ],
                ),
            ],
            4,
            [
                "The integration is a fetch integration and is missing/containing malformed required params:\nThe param incidentType is missing/malformed, it should be in the following format: {'display': 'Alert type', 'name': 'incidentType', 'type': 13}\nThe param isFetch is missing/malformed, it should be in the following format: {'display': 'Fetch alerts', 'name': 'isFetch', 'type': 8}",
                "The integration is a fetch integration and is missing/containing malformed required params:\nThe param incidentType is missing/malformed, it should be in the following format: {'display': 'Incident type', 'name': 'incidentType', 'type': 13}\nThe param isFetch is missing/malformed, it should be in the following format: {'display': 'Fetch incidents', 'name': 'isFetch', 'type': 8}",
                "The integration is a fetch integration and is missing/containing malformed required params:\nThe param incidentType is missing/malformed, it should be in the following format: {'display': 'Alert type', 'name': 'incidentType', 'type': 13}\nThe param isFetch is missing/malformed, it should be in the following format: {'display': 'Fetch alerts', 'name': 'isFetch', 'type': 8}",
                "The integration is a fetch integration and is missing/containing malformed required params:\nThe param isFetch is missing/malformed, it should be in the following format: {'display': 'Fetch incidents', 'name': 'isFetch', 'type': 8}",
            ],
        ),
    ],
)
def test_IsValidFetchValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One Xsiam non-fetch integration.
            - One Xsoar non-fetch integration.
            - One Xsiam fetching integration with all required params.
            - One Xsoar fetching integration with all required params.
        - Case 2: Four invalid integrations:
            - One Xsiam fetching integration without all required params.
            - One Xsoar fetching integration without all required params.
            - One Xsiam fetching integration with incidentType with malformed display and isFetch with wrong type.
            - One Xsoar fetching integration with all required with missing display.
    When
    - Calling the IsValidFetchValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all and mention only the missing display (and nothing about isFetch) for the last integration.
    """
    results = IsValidFetchValidator().is_valid(content_items)
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
                create_integration_object(pack_info={"support": XSOAR_SUPPORT}),
                create_integration_object(pack_info={"support": PARTNER_SUPPORT}),
                create_integration_object(pack_info={"support": DEVELOPER_SUPPORT}),
                create_integration_object(pack_info={"support": COMMUNITY_SUPPORT}),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "insecure",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "fromlicense": "encrypted",
                            }
                        ]
                    ],
                    pack_info={"support": XSOAR_SUPPORT},
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
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "fromlicense": "encrypted",
                            }
                        ]
                    ],
                    pack_info={"support": PARTNER_SUPPORT},
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_2",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "fromlicense": "encrypted",
                            }
                        ]
                    ],
                    pack_info={"support": DEVELOPER_SUPPORT},
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_3",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "fromlicense": "encrypted",
                            }
                        ]
                    ],
                    pack_info={"support": COMMUNITY_SUPPORT},
                ),
            ],
            3,
            [
                'The following parameters contain the "fromlicense" field: test_1. The field is not allowed for contributors, please remove it.',
                'The following parameters contain the "fromlicense" field: test_2. The field is not allowed for contributors, please remove it.',
                'The following parameters contain the "fromlicense" field: test_3. The field is not allowed for contributors, please remove it.',
            ],
        ),
    ],
)
def test_IsContainingFromLicenseInParamsValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Five valid integrations:
            - One Xsoar supported integration without fromlicense field in any of the integration params.
            - One Partner supported integration without fromlicense field in any of the integration params.
            - One Developer supported integration without fromlicense field in any of the integration params.
            - One Community supported integration without fromlicense field in any of the integration params.
            - One Xsoar supported integration with fromlicense field in one of the integration params.
        - Case 2: Three invalid integrations:
            - One Partner supported integration with fromlicense field in one of the integration params.
            - One Developer supported integration with fromlicense field in one of the integration params.
            - One Community supported integration with fromlicense field in one of the integration params.
    When
    - Calling the IsContainingFromLicenseInParamsValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    with ChangeCWD(REPO.path):
        results = IsContainingFromLicenseInParamsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsContainingFromLicenseInParamsValidator_fix():
    """
    Given
        An invalid community supported integration with two params: one with fromlicense and one without.
    When
    - Calling the IsContainingFromLicenseInParamsValidator fix function.
    Then
        - Make sure that fromlicense field was set to None, and that the right message was returned.
    """
    content_item = create_integration_object(
        paths=["configuration"],
        values=[
            [
                {
                    "name": "test_1",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                },
                {
                    "name": "test_3",
                    "type": 8,
                    "required": False,
                    "display": "Trust any certificate (not secure)",
                    "fromlicense": "encrypted",
                },
            ]
        ],
        pack_info={"support": COMMUNITY_SUPPORT},
    )
    assert any([param.fromlicense for param in content_item.params])
    validator = IsContainingFromLicenseInParamsValidator()
    validator.invalid_params[content_item.name] = ["test_3"]
    assert (
        validator.fix(content_item).message
        == "Removed the fromlicense field from the following parameters: test_3."
    )
    assert not any([param.fromlicense for param in content_item.params])


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": True,
                            },
                            {
                                "name": "test_2",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": False,
                            },
                        ]
                    ],
                    pack_info={"support": PARTNER_SUPPORT},
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": True,
                            },
                            {
                                "name": "test_2",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": False,
                            },
                        ]
                    ],
                    pack_info={"support": DEVELOPER_SUPPORT},
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": True,
                            },
                            {
                                "name": "test_2",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": False,
                            },
                        ]
                    ],
                    pack_info={"support": COMMUNITY_SUPPORT},
                ),
                create_integration_object(
                    paths=["configuration"],
                    values=[
                        [
                            {
                                "name": "test_1",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": True,
                            },
                            {
                                "name": "test_3",
                                "type": 8,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                            },
                        ]
                    ],
                    pack_info={"support": XSOAR_SUPPORT},
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
                                "name": "test",
                                "type": 4,
                                "required": False,
                                "display": "Trust any certificate (not secure)",
                                "hidden": False,
                            }
                        ]
                    ],
                    pack_info={"support": XSOAR_SUPPORT},
                ),
            ],
            1,
            [
                "In order to allow fetching the following params: test from an external vault, the type of the parameters should be changed from 'Encrypted' (type 4), to 'Credentials' (type 9)'.\nFor more details, check the convention for credentials - https://xsoar.pan.dev/docs/integrations/code-conventions#credentials"
            ],
        ),
    ],
)
def test_IsAPITokenInCredentialTypeValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Five valid integrations:
            - One Partner supported integration with one hidden and one non-hidden type 4 params.
            - One Developer supported integration with one hidden and one non-hidden type 4 params.
            - One Community supported integration with one hidden and one non-hidden type 4 params.
            - One Xsoar supported integration with one hidden type 4 param, and one non-hidden non type 4 param.
        - Case 2: One invalid integration with a non-hidden type 4 param.
    When
    - Calling the IsAPITokenInCredentialTypeValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    with ChangeCWD(REPO.path):
        results = IsAPITokenInCredentialTypeValidator().is_valid(content_items)
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
                    pack_info={"name": "pack_no_1"},
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
                    pack_info={"name": "pack_no_2"},
                ),
                create_integration_object(
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "incident_command",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "incident_arg_no_1",
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
                    pack_info={"name": "pack_no_3"},
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
                                "name": "incident_command",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "incident_arg_no_1",
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
                    pack_info={"name": "pack_no_4"},
                )
            ],
            1,
            [
                "The following commands contain the word 'incident' in one or more of their fields, please remove:\nThe command incident_command contains the word 'incident' in its name and in the following arguments: incident_arg_no_1."
            ],
        ),
    ],
)
def test_IsNameContainIncidentInCorePackValidator_is_valid(
    mocker, content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Four valid integrations:
            - One core integration without commands.
            - One core integration without commands without incident in one of their field.
            - One non-core integration with commands with incident in one of their field.
        - Case 2: One invalid core integration with commands with incident in one of their field.
    When
    - Calling the IsNameContainIncidentInCorePackValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail any.
        - Case 2: Should fail and mention only the fields with 'incident' in their name.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.IN_validators.IN139_is_name_contain_incident_in_core_pack.get_core_pack_list",
        return_value=["pack_no_1", "pack_no_2", "pack_no_4"],
    )
    with ChangeCWD(REPO.path):
        results = IsNameContainIncidentInCorePackValidator().is_valid(content_items)
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
                    pack_info={"support": XSOAR_SUPPORT},
                    paths=["script.isfetchevents"],
                    values=[True],
                ),
                create_integration_object(
                    pack_info={"support": PARTNER_SUPPORT},
                    paths=["supportlevelheader", "script.isfetchevents"],
                    values=[XSOAR_SUPPORT, True],
                ),
                create_integration_object(
                    pack_info={"support": XSOAR_SUPPORT},
                    paths=["script.isfetcheventsandassets"],
                    values=[True],
                ),
                create_integration_object(
                    pack_info={"support": PARTNER_SUPPORT},
                    paths=["supportlevelheader", "script.isfetcheventsandassets"],
                    values=[XSOAR_SUPPORT, True],
                ),
                create_integration_object(pack_info={"support": PARTNER_SUPPORT}),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    pack_info={"support": PARTNER_SUPPORT},
                    paths=["script.isfetchevents"],
                    values=[True],
                ),
                create_integration_object(
                    pack_info={"support": PARTNER_SUPPORT},
                    paths=["script.isfetcheventsandassets"],
                    values=[True],
                ),
            ],
            2,
            [
                "The integration is a fetch events/assets integration in a partner supported pack.\nTherefore, it should have the key supportlevelheader = xsoar in its yml.",
                "The integration is a fetch events/assets integration in a partner supported pack.\nTherefore, it should have the key supportlevelheader = xsoar in its yml.",
            ],
        ),
    ],
)
def test_IsPartnerCollectorHasXsoarSupportLevelValidator_is_valid(
    content_items: List[Integration],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given
    content_items iterables.
        - Case 1: Five valid integrations:
            - One Xsoar supported events fetching integration.
            - One Partner supported events fetching integration with support level header = Xsoar.
            - One Xsoar supported events&assets fetching integration.
            - One Xsoar supported events&assets fetching integration with support level header = Xsoar.
            - One non-fetching Partner supported integration without support level header = Xsoar.
        - Case 2: Two invalid integrations:
            - One Partner supported events fetching integration without support level header = Xsoar.
            - One Xsoar supported events&assets fetching integration without support level header = Xsoar.
    When
    - Calling the IsPartnerCollectorHasXsoarSupportLevelValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """

    with ChangeCWD(REPO.path):
        results = IsPartnerCollectorHasXsoarSupportLevelValidator().is_valid(
            content_items
        )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsPartnerCollectorHasXsoarSupportLevelValidator_fix():
    """
    Given
        A Partner supported events fetching integration with support level header = Xsoar.
    When
    - Calling the IsPartnerCollectorHasXsoarSupportLevelValidator fix function.
    Then
        - Make sure that the support level header was set to xsoar, and that the right message was returned.
    """
    content_item = create_integration_object(
        pack_info={"support": PARTNER_SUPPORT},
        paths=["script.isfetchevents"],
        values=[True],
    )
    assert content_item.data.get(SUPPORT_LEVEL_HEADER) != XSOAR_SUPPORT
    validator = IsPartnerCollectorHasXsoarSupportLevelValidator()
    assert (
        validator.fix(content_item).message
        == f"Changed the integration's should {SUPPORT_LEVEL_HEADER} key to {XSOAR_SUPPORT}."
    )
    assert content_item.data.get(SUPPORT_LEVEL_HEADER) == XSOAR_SUPPORT


def test_IntegrationDisplayNameVersionedCorrectlyValidator_is_valid():
    """
    Given:
     - 1 integration with valid versioned display-name
     - 1 integration with invalid versioned display-name

    When:
     - Running the IntegrationDisplayNameVersionedCorrectlyValidator validator & fix

    Then:
     - make sure the integration with the invalid version fails on the validation
     - make sure the fix updates the display-name of the integration to lower-case versioned name.
    """
    content_items = [
        create_integration_object(paths=["display"], values=["test v2"]),
        create_integration_object(paths=["display"], values=["test V3"]),
    ]

    results = IntegrationDisplayNameVersionedCorrectlyValidator().is_valid(
        content_items
    )
    assert len(results) == 1
    assert results[0].content_object.display_name == "test V3"

    fix_result = IntegrationDisplayNameVersionedCorrectlyValidator().fix(
        results[0].content_object
    )
    assert fix_result.content_object.display_name == "test v3"


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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [],
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
                    paths=["script.commands"],
                    values=[
                        [
                            {
                                "name": "ip",
                                "description": "ip command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "ip",
                                        "default": True,
                                        "required": True,
                                        "description": "ip description.",
                                    }
                                ],
                                "outputs": [],
                            },
                            {
                                "name": "url",
                                "description": "url command",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "url",
                                        "default": True,
                                        "isArray": False,
                                        "required": True,
                                        "description": "url description.",
                                    }
                                ],
                                "outputs": [],
                            },
                        ]
                    ],
                ),
            ],
            1,
            [
                "The following reputation commands contain default arguments without 'isArray: True':\nThe command ip is missing the isArray value on its default argument ip.\nThe command url is missing the isArray value on its default argument url."
            ],
        ),
    ],
)
def test_IsRepCommandContainIsArrayArgumentValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: Three valid integrations:
            - One integration without reputation commands.
            - One integration without commands.
            - One integration with valid reputation command.
        - Case 2: One invalid integration with invalid ip command due to missing required isArray argument, and an invalid url command due to isArray argument set to False.
    When
    - Calling the IsRepCommandContainIsArrayArgumentValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail all.
    """
    results = IsRepCommandContainIsArrayArgumentValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )

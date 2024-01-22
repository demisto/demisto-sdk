import pytest

from demisto_sdk.commands.common.constants import RELIABILITY_PARAM, MarketplaceVersions
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN108_is_valid_subtype import (
    ValidSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN130_is_integration_runable import (
    IsIntegrationRunnableValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN135_is_valid_param_display import (
    IsValidParamDisplayValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN154_is_missing_reliability_param import (
    IsMissingReliabilityParamValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN158_is_valid_description_for_non_deprecated_integration import (
    IsValidDescriptionForNonDeprecatedIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN160_is_valid_display_name_for_non_deprecated_integration import (
    IsValidDisplayNameForNonDeprecatedIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN161_is_siem_integration_valid_marketplace import (
    IsSiemIntegrationValidMarketplaceValidator,
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
    content_items, expected_number_of_failures, expected_msgs
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
    content_items, expected_number_of_failures
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
        - one param with invalid display because it's starting with lowercase letter and has underscore.
        - one param with invalid display because it has underscore.
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


def test_IsMissingReliabilityParamValidator_fix():
    """
    Given
        An integration with reputation command and no reliability param.
    When
    - Calling the IsMissingReliabilityParamValidator fix function.
    Then
        - Make sure that the reliability param was added to the integration, and that the right msg was returned.
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
    )
    validator = IsMissingReliabilityParamValidator()
    assert not validator.is_containing_reliability_param(content_item.params)
    assert (
        validator.fix(content_item).message
        == "Added the reliability param to the integration."
    )
    assert validator.is_containing_reliability_param(content_item.params)

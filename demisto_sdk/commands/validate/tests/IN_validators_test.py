import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_ps_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN108_is_valid_subtype import (
    ValidSubtypeValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN119_feed_integration_from_version import (
    FeedIntegrationFromVersionValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN120_ps_integration_from_version import (
    PSIntegrationFromVersionValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN130_is_integration_runable import (
    IsIntegrationRunnableValidator,
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
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "5.5.0"],
                ),
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[False, "5.0.0"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "6.0.0"],
                ),
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "5.0.0"],
                ),
            ],
            1,
            [
                "The integration is a feed integration and therefore require a fromversion field of at least 5.5.0, current version is: 5.0.0."
            ],
        ),
    ],
)
def test_FeedIntegrationFromVersionValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: 2 integrations - one feed integration with high enough fromversion field and one none feed integration with fromversion lower than 5.5.0.
        - Case 2: 2 integration - one feed integration with fromversion lower than 5.5.0 and one with a high enough fromversion field.
    When
    - Calling the FeedIntegrationFromVersionValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail at all.
        - Case 2: Should fail only one integration.
    """
    results = FeedIntegrationFromVersionValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_FeedIntegrationFromVersionValidator_fix():
    """
    Given
        - an integration
    When
    - Calling the FeedIntegrationFromVersionValidator fix function.
    Then
        - Make sure the the integration fromversion was raised and that the right message was returned.
    """
    content_item = create_integration_object(paths=["fromversion"], values=["5.0.0"])
    assert content_item.fromversion == "5.0.0"
    assert (
        FeedIntegrationFromVersionValidator().fix(content_item).message
        == "Raised the fromversion field to 5.5.0"
    )
    assert content_item.fromversion == "5.5.0"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_ps_integration_object(
                    paths=[
                        "script.type",
                        "fromversion",
                    ],
                    values=["powershell", "5.5.0"],
                ),
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["5.0.0"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["6.0.0"],
                ),
                create_ps_integration_object(
                    paths=[
                        "script.type",
                        "fromversion",
                    ],
                    values=["powershell", "5.0.0"],
                ),
            ],
            1,
            [
                "The integration is a powershell integration and therefore require a fromversion field of at least 5.5.0, current version is: 5.0.0."
            ],
        ),
    ],
)
def test_PSIntegrationFromVersionValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: 2 integrations - one ps integration with high enough fromversion field and one python integration with fromversion lower than 5.5.0.
        - Case 2: 2 integration - one ps integration with fromversion lower than 5.5.0 and one with a high enough fromversion field.
    When
    - Calling the PSIntegrationFromVersionValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail at all.
        - Case 2: Should fail only one integration.
    """
    results = PSIntegrationFromVersionValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_PSIntegrationFromVersionValidator_fix():
    """
    Given
        - a ps integration
    When
    - Calling the PSIntegrationFromVersionValidator fix function.
    Then
        - Make sure the the integration fromversion was raised and that the right message was returned.
    """
    content_item = create_ps_integration_object(paths=["fromversion"], values=["5.0.0"])
    assert content_item.fromversion == "5.0.0"
    assert (
        PSIntegrationFromVersionValidator().fix(content_item).message
        == "Raised the fromversion field to 5.5.0"
    )
    assert content_item.fromversion == "5.5.0"

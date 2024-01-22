import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
from demisto_sdk.commands.validate.validators.IN_validators.IN160_is_valid_display_name_for_non_deprecated_integration import IsValidDisplayNameForNonDeprecatedIntegrationValidator
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


# @pytest.mark.parametrize(
#     "content_items, expected_number_of_failures, expected_msgs",
#     [
#         (
#             [
#                 create_integration_object(),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[[]],
#                 ),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "ip",
#                                 "description": "ip command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "ip",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                                 "outputs": [],
#                             }
#                         ]
#                     ],
#                 ),
#             ],
#             0,
#             [],
#         ),
#         (
#             [
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "endpoint",
#                                 "description": "endpoint command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "ip",
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                             },
#                             {
#                                 "name": "domain",
#                                 "description": "domain command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "domain",
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                                 "outputs": [],
#                             },
#                         ]
#                     ],
#                 ),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "ip",
#                                 "description": "ip command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "ip",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                             },
#                             {
#                                 "name": "url",
#                                 "description": "url command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "url",
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                                 "outputs": [],
#                             },
#                         ]
#                     ],
#                 ),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "email",
#                                 "description": "email command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "email",
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                             },
#                             {
#                                 "name": "cve",
#                                 "description": "cve command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "cve",
#                                         "isArray": True,
#                                         "required": True,
#                                     }
#                                 ],
#                                 "outputs": [],
#                             },
#                         ]
#                     ],
#                 ),
#             ],
#             3,
#             [],
#         ),
#     ],
# )
# def test_IsValidRepCommandValidator_is_valid(
#     content_items, expected_number_of_failures, expected_msgs
# ):
#     """
#     Given
#     content_items iterables.
#         - Case 1: Four integrations:
#             - One integration with a param of type 8 but no required field.
#             - One integration with a param of type 0 and no required field.
#             - One integration with a param of type 8 but required field set to False.
#             - One integration with 3 param of type 8, one's required field is set to True and the other two are set to False.
#     When
#     - Calling the IsValidRepCommandValidator is valid function.
#     Then
#         - Make sure the validation fail when it needs to and the right error message is returned.
#         - Case 1: Should fail all except test_param 2 & 4.
#     """
#     results = IsValidRepCommandValidator().is_valid(content_items)
#     assert len(results) == expected_number_of_failures
#     assert all(
#         [
#             result.message == expected_msg
#             for result, expected_msg in zip(results, expected_msgs)
#         ]
#     )


# def test_IsValidRepCommandValidator_fix():
#     """
#     Given
#         An integration with invalid proxy & insecure params.
#     When
#     - Calling the IsValidRepCommandValidator fix function.
#     Then
#         - Make sure that all the relevant fields were added/fixed and that the right msg was returned.
#     """
#     content_item = create_integration_object(
#         paths=["configuration"],
#         values=[
#             [
#                 {
#                     "name": "test_param_4",
#                     "type": 8,
#                     "display": "test param 4",
#                     "required": True,
#                 },
#                 {
#                     "name": "test_param_5",
#                     "type": 8,
#                     "display": "test param 5",
#                     "required": False,
#                 },
#                 {
#                     "name": "test_param_6",
#                     "type": 8,
#                     "display": "test param 6",
#                     "required": False,
#                 },
#             ]
#         ],
#     )
#     assert content_item.params == [
#         {
#             "name": "test_param_4",
#             "type": 8,
#             "display": "test param 4",
#             "required": True,
#         },
#         {
#             "name": "test_param_5",
#             "type": 8,
#             "display": "test param 5",
#             "required": False,
#         },
#         {
#             "name": "test_param_6",
#             "type": 8,
#             "display": "test param 6",
#             "required": False,
#         },
#     ]
#     validator = IsValidRepCommandValidator()
#     validator.misconfigured_checkbox_params_by_integration[content_item.name] = [
#         "test_param_5",
#         "test_param_6",
#     ]
#     assert (
#         validator.fix(content_item).message
#         == "Set required field of the following params was set to True: test_param_5, test_param_6."
#     )
#     assert content_item.params == [
#         {
#             "name": "test_param_4",
#             "type": 8,
#             "display": "test param 4",
#             "required": True,
#         },
#         {
#             "name": "test_param_5",
#             "type": 8,
#             "display": "test param 5",
#             "required": True,
#         },
#         {
#             "name": "test_param_6",
#             "type": 8,
#             "display": "test param 6",
#             "required": True,
#         },
#     ]


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
        - Case 1: The valid integrations:
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


# @pytest.mark.parametrize(
#     "content_items, expected_number_of_failures, expected_msgs, core_packs_ls",
#     [
#         (
#             [
#                 create_integration_object(),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[[]],
#                 ),
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "ip",
#                                 "description": "ip command",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "ip_1",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                         "description": "ip_1_description",
#                                     },
#                                     {
#                                         "name": "ip_2",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                         "description": "ip_2_description",
#                                     },
#                                 ],
#                                 "outputs": [],
#                             },
#                         ]
#                     ],
#                 ),
#             ],
#             0,
#             [],
#             []
#         ),
#         (
#             [
#                 create_integration_object(
#                     paths=["script.commands"],
#                     values=[
#                         [
#                             {
#                                 "name": "ip_1",
#                                 "description": "ip command 1",
#                                 "deprecated": False,
#                                 "arguments": [
#                                     {
#                                         "name": "ip_1",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                         "description": "ip_1_description",
#                                     },
#                                     {
#                                         "name": "ip_2",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                         "description": "ip_2_description",
#                                     },
#                                     {
#                                         "name": "ip_1",
#                                         "default": True,
#                                         "isArray": True,
#                                         "required": True,
#                                         "description": "ip_1_description",
#                                     },
#                                 ],
#                                 "outputs": [],
#                             }
#                         ]
#                     ],
#                 )
#             ],
#             1,
#             [
#                 "The following commands contain duplicated arguments:\nCommand ip_1, contains multiple appearances of the following arguments ip_1.\nPlease make sure to remove the duplications."
#             ],
#             []
#         ),
#     ],
# )
# def test_IsNameContainIncidentInCorePackValidator_is_valid(
#     mocker, content_items, expected_number_of_failures, expected_msgs, core_packs_ls
# ):
#     """
#     Given
#     content_items iterables.
#         - Case 1: Two valid integrations:
#             - One integration without commands.
#             - One integration with one command without duplicated args.
#         - Case 2: One invalid integration with a command with 3 arguments Two of the same name and one different..
#     When
#     - Calling the IsNameContainIncidentInCorePackValidator is valid function.
#     Then
#         - Make sure the validation fail when it needs to and the right error message is returned.
#         - Case 1: Shouldn't fail any.
#         - Case 2: Should fail.
#     """
#     mocker.patch(
#         "demisto_sdk.commands.validate.validators.IN_validators.IN139_is_name_contain_incident_in_core_pack.get_core_pack_list",
#         return_value = ["pack_1"]
#     )
#     mock = mocker.patch("demisto_sdk.commands.content_graph.objects.content_item.ContentItem.pack_name")
#     mock.side_effect = iter(["pack_1", "pack_2", "pack_3"])
#     results = IsNameContainIncidentInCorePackValidator().is_valid(content_items)
#     assert len(results) == expected_number_of_failures
#     assert all(
#         [
#             result.message == expected_msg
#             for result, expected_msg in zip(results, expected_msgs)
#         ]
#     )


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
    "content_items, expected_number_of_failures, expected_msgs, marketplaces",
    [
        (
            [
                create_integration_object(),
                create_integration_object(
                    paths=["deprecated", "display"],
                    values=[True, "test (Deprecated)"],
                ),
                create_integration_object(
                    paths=["deprecated", "display"],
                    values=[True, "test"],
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
                "The marketplaces field of this XSIAM integration is incorrect.\nThis field should have only the 'marketplacev2' value."
            ],
            [MarketplaceVersions.XSOAR],
        ),
    ],
)
def test_IsValidDisplayNameForNonDeprecatedIntegrationValidator_is_valid(
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
    - Calling the IsValidDisplayNameForNonDeprecatedIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Should pass all.
        - Case 2: Should fail.
    """
    results = IsValidDisplayNameForNonDeprecatedIntegrationValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )

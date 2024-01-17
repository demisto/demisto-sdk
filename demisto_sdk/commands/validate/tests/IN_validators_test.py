import pytest

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
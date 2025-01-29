import pytest

from demisto_sdk.commands.common.constants import BETA_INTEGRATION_DISCLAIMER
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.DS_validators.DS101_is_valid_beta_description import (
    IsValidBetaDescriptionValidator,
)
from demisto_sdk.commands.validate.validators.DS_validators.DS108_description_ends_with_dot import (
    DescriptionEndsWithDotValidator,
)


@pytest.mark.parametrize(
    "is_beta_integration, description_file_exist, result_len",
    [
        (
            False,
            False,
            0,
        ),
        (
            False,
            True,
            0,
        ),
        (
            True,
            False,
            1,
        ),
        (
            True,
            True,
            0,
        ),
    ],
)
def test_DescriptionMissingInBetaIntegrationValidator_obtain_invalid_content_items(
    is_beta_integration,
    description_file_exist,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: Not a beta integration, and no description file.
            - Case 2: Not a beta integration, with a description file.
            - Case 3: A beta integration, and no description file.
            - Case 4: A beta integration, with a description file.
    When
    - Calling the DescriptionMissingInBetaIntegrationValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly for beta integrations.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
        - Case 4: Shouldn't fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS100_description_missing_in_beta_integration import (
        DescriptionMissingInBetaIntegrationValidator,
    )

    integration = create_integration_object()
    integration.is_beta = is_beta_integration
    integration.description_file.exist = description_file_exist

    invalid_content_items = (
        DescriptionMissingInBetaIntegrationValidator().obtain_invalid_content_items(
            [integration]
        )
    )
    assert result_len == len(invalid_content_items)


@pytest.mark.parametrize(
    "is_beta_integration, description_file_content, result_len",
    [
        (
            False,
            "",
            0,
        ),
        (
            True,
            "",
            1,
        ),
        (
            True,
            BETA_INTEGRATION_DISCLAIMER,
            0,
        ),
    ],
)
def test_IsValidBetaDescriptionValidator_obtain_invalid_content_items(
    is_beta_integration,
    description_file_content,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: Not a beta integration, and no beta disclaimer.
            - Case 3: A beta integration, and no beta disclaimer.
            - Case 4: A beta integration, with a beta disclaimer.
    When
    - Calling the IsValidBetaDescriptionValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly for beta integrations.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Shouldn't fail.
    """

    integration = create_integration_object()
    integration.is_beta = is_beta_integration
    integration.description_file.file_content_str = description_file_content

    invalid_content_items = (
        IsValidBetaDescriptionValidator().obtain_invalid_content_items([integration])
    )
    assert result_len == len(invalid_content_items)


@pytest.mark.parametrize(
    "description_file_content, result_len",
    [
        (
            "",
            0,
        ),
        (
            "### This is a partner Contributed Integration",
            1,
        ),
    ],
)
def test_IsDescriptionContainsContribDetailsValidator_obtain_invalid_content_items(
    description_file_content,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: description file without Contrib Details.
            - Case 2: description file with Contrib Details.
    When
    - Calling the IsDescriptionContainsContribDetailsValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS105_is_description_contains_contrib_details import (
        IsDescriptionContainsContribDetailsValidator,
    )

    integration = create_integration_object()
    integration.description_file.file_content_str = description_file_content

    invalid_content_items = (
        IsDescriptionContainsContribDetailsValidator().obtain_invalid_content_items(
            [integration]
        )
    )
    assert result_len == len(invalid_content_items)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_error_msgs",
    [
        (
            [
                create_integration_object(
                    ["description", "script.commands"],
                    [
                        "description without dot",
                        [
                            {
                                "name": "command_number_one",
                                "description": "command_number_one description.",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "arg_one",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "arg_one_desc.",
                                    },
                                    {
                                        "name": "arg_two",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "arg_two_desc",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "path_1",
                                        "description": "description_1",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextPath": "path_2",
                                        "description": "description_2.",
                                    },
                                ],
                            },
                        ],
                    ],
                ),
                create_integration_object(
                    ["description", "script.commands"],
                    [
                        'This description ends with a json list [\n{\n"name": "example json ending on another line"\n}\n]',
                        [
                            {
                                "name": "command_number_two",
                                "description": "command_number_one description.",
                                "deprecated": False,
                                "arguments": [
                                    {
                                        "name": "arg_one",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "an arg description that has a trailing new line.\n",
                                    },
                                    {
                                        "name": "arg_two",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "This description is okay!",
                                    },
                                    {
                                        "name": "arg_three",
                                        "default": True,
                                        "isArray": True,
                                        "required": True,
                                        "description": "a yml with a description that has an 'example without dot at the end of the string.'",
                                    },
                                ],
                                "outputs": [
                                    {
                                        "name": "output_1",
                                        "contextPath": "path_1",
                                        "description": "a contextPath description with a dot in the bracket (like this.)",
                                    },
                                    {
                                        "name": "output_2",
                                        "contextPath": "path_2",
                                        "description": "",
                                    },
                                ],
                            },
                        ],
                    ],
                ),
            ],
            1,
            [
                "The Integration contains description fields without dots at the end:\nThe file's description field is missing a '.' at the end of the sentence.\n- In command 'command_number_one':\n\tThe argument arg_two description should end with a period.\n\tThe context path path_1 description should end with a period.\nPlease make sure to add a dot at the end of all the mentioned fields."
            ],
        ),
        (
            [
                create_script_object(
                    paths=["args", "comment"],
                    values=[
                        [
                            {
                                "name": "arg_no_one",
                                "description": "an arg description that ends with a url www.test.com",
                            },
                            {
                                "name": "arg_no_two",
                                "description": "an arg description that doesn't ends with a dot.",
                            },
                        ],
                        "an arg with a description that has www.test.com in the middle of the sentence and no dot at the end",
                    ],
                )
            ],
            1,
            [
                "The Script contains description fields without dots at the end:\nThe file's comment field is missing a '.' at the end of the sentence.\nPlease make sure to add a dot at the end of all the mentioned fields."
            ],
        ),
    ],
)
def test_DescriptionEndsWithDotValidator_obtain_invalid_content_items(
    content_items,
    expected_number_of_failures,
    expected_error_msgs,
):
    """
    Given
    content_items iterables.
            - Case 1: Two integrations:
                - One integration with a description field without a dot at the end and one command with two arguments and two context paths:
                    - One argument with regular text description and a dot at the end.
                    - One argument with regular text description and no dot at the end.
                    - One contextPath with regular text description and a dot at the end.
                    - One contextPath with regular text description and no dot at the end.
                - One integration with a description field with a json example at the end and no dot with three arguments and two context paths:
                    - One argument with a dot and a trailing new line at the end.
                    - One argument without a dot and an exclamation mark at the end.
                    - One argument with an example string at the end.
                    - One contextPath description ending with a dot inside brackets.
                    - One contextPath with empty description.
            - Case 2: One script with a comment with a url address at the middle and no dot at the end and two arguments:
                - One argument with a description ending with a url address.
                - One argument with a regular text ending a dot.
    When
    - Calling the DescriptionEndsWithDotValidator is valid function.
    Then
        - Make sure that the description file exist.
        - Case 1: One failure, The first integration should fail for it's description, second argument and first context Path.
        - Case 2: The script should fail only for it's comment section.
    """
    results = DescriptionEndsWithDotValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_error_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_fix_msg, lines_without_dots",
    [
        (
            create_integration_object(
                ["description", "script.commands"],
                [
                    "description without dot",
                    [
                        {
                            "name": "command_number_one",
                            "description": "command_number_one description.",
                            "deprecated": False,
                            "arguments": [
                                {
                                    "name": "arg_one",
                                    "default": True,
                                    "isArray": True,
                                    "required": True,
                                    "description": "arg_one_desc.",
                                },
                                {
                                    "name": "arg_two",
                                    "default": True,
                                    "isArray": True,
                                    "required": True,
                                    "description": "arg_two_desc",
                                },
                            ],
                            "outputs": [
                                {
                                    "name": "output_1",
                                    "contextPath": "path_1",
                                    "description": "description_1",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2",
                                    "description": "description_2.",
                                },
                            ],
                        },
                    ],
                ],
            ),
            "Added dots ('.') at the end of the following description fields:\nAdded a '.' at the end of the description field.\n In the command command_number_one:\n\tAdded a '.' at the end of the argument 'arg_two' description field.\n\tAdded a '.' at the end of the output 'path_1' description field.",
            {
                "description": "description without dot.",
                "command_number_one": {"args": ["arg_two"], "contextPath": ["path_1"]},
            },
        ),
        (
            create_script_object(
                paths=["args", "comment"],
                values=[
                    [
                        {
                            "name": "arg_no_one",
                            "description": "an arg description that ends with a url www.test.com",
                        },
                        {
                            "name": "arg_no_two",
                            "description": "an arg description that doesn't ends with a dot.",
                        },
                    ],
                    "an arg with a description that has www.test.com in the middle of the sentence and no dot at the end",
                ],
            ),
            "Added dots ('.') at the end of the following description fields:\nAdded a '.' at the end of the comment field.",
            {
                "description": "an arg with a description that has www.test.com in the middle of the sentence and no dot at the end."
            },
        ),
    ],
)
def test_DescriptionEndsWithDotValidator_fix(
    content_item, expected_fix_msg, lines_without_dots
):
    """
    Given
        content_items iterables.
            - Case 1: One integration with a description field without a dot at the end and one command with two arguments and two context paths:
                    - One argument with regular text description and a dot at the end.
                    - One argument with regular text description and no dot at the end.
                    - One contextPath with regular text description and a dot at the end.
                    - One contextPath with regular text description and no dot at the end.
            - Case 2: One script with a comment with a url address at the middle and no dot at the end and two arguments:
                - One argument with a description ending with a url address.
                - One argument with a regular text ending a dot.
    When
    - Calling the DescriptionEndsWithDotValidator fix function.
    Then
        - Make sure that dots were added to all relevant description fields and that the right fix message was returned.
    """
    validator = DescriptionEndsWithDotValidator()
    validator.lines_without_dots[content_item.name] = lines_without_dots
    assert validator.fix(content_item).message == expected_fix_msg
    assert not validator.obtain_invalid_content_items([content_item])


@pytest.mark.parametrize(
    "description_file_exist, is_unified, expected_len_errors",
    [
        pytest.param(True, False, 0, id="Case 1"),
        pytest.param(False, True, 0, id="Case 2"),
        pytest.param(False, False, 1, id="Case 3"),
    ],
)
def test_NoDescriptionFileValidator_obtain_invalid_content_items(
    description_file_exist, is_unified, expected_len_errors
):
    """
    Given:
        - Case 1: Description file exists in the integration folder, integration is not unified.
        - Case 2: Description file doesn't exist in the integration folder, but is unified.
        - Case 3: Description file doesn't exist in the integration folder, and is not unified.
    When:
        - Calling the DescriptionInFolderAndYmlValidator obtain_invalid_content_items function.
    Then:
        - Case 1: Should pass.
        - Case 2: Should pass.
        - Case 3: Should fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS104_no_description_file import (
        NoDescriptionFileValidator,
    )

    integration = create_integration_object()

    integration.description_file.exist = description_file_exist
    integration.is_unified = is_unified
    invalid_content_items = NoDescriptionFileValidator().obtain_invalid_content_items(
        [integration]
    )
    assert len(invalid_content_items) == expected_len_errors

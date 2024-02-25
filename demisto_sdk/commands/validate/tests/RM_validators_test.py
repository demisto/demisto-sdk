import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_metadata_object
from demisto_sdk.commands.validate.validators.RM_validators.RM113_is_contain_copy_right_section import (
    IsContainCopyRightSectionValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_metadata_object(readme_text="This is a valid readme."),
                create_metadata_object(readme_text=""),
            ],
            0,
            [],
        ),
        (
            [create_metadata_object(readme_text="Invalid readme\nBSD\nCopyright")],
            1,
            [
                "Invalid keywords related to Copyrights (BSD, MIT, Copyright, proprietary) were found in lines: 2, 3. Copyright section cannot be part of pack readme."
            ],
        ),
    ],
)
def test_IsContainCopyRightSectionValidator_is_valid(
    content_items,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given
    content_items.
        - Case 1: Two valid pack_metadatas:
            - 1 pack with valid readme text.
            - 1 pack with an empty readme.
        - Case 2: One invalid pack_metadata with 2 lines contain copyright words
    When
    - Calling the IsContainCopyRightSectionValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should pass all.
        - Case 3: Should fail.
    """
    results = IsContainCopyRightSectionValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )

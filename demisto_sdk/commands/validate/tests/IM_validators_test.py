import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_metadata_object,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM108_author_image_is_empty import (
    AuthorImageIsEmptyValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        (
            [create_metadata_object(image="")],
            1,
            ["The author image should not be empty. Please provide a relevant image."],
        ),
    ],
)
def test_AuthorImageIsEmptyValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: Author image not empty.
        - Case 2: Author image is empty.

    When
    - Calling the AuthorImageIsEmptyValidator is_valid function.
    Then
        - Make sure the right amount of pack author image failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    results = AuthorImageIsEmptyValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )

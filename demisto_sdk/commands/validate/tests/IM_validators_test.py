import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_metadata_object,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM100_image_exists_validation import (
    ImageExistsValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM108_author_image_is_empty import (
    AuthorImageIsEmptyValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM109_author_image_exists_validation import (
    AuthorImageExistsValidator,
)


def test_ImageExistsValidator_is_valid_image_path():
    """
    Given:
    content_items with 2 integrations:
        - One integration without image.
        - One integration with an existing image.

    When:
        - Calling the ImageExistsValidator is_valid function.

    Then:
        - Make sure the right amount of integration image path failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    content_items = [create_integration_object(), create_integration_object()]
    content_items[0].image.exist = False
    results = ImageExistsValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        "You've created/modified a yml or package without providing an image as a .png file. Please make sure to add an image at TestIntegration_image.png."
        in result.message
        for result in results
    )


def test_AuthorImageExistsValidator_is_valid_image_path():
    """
    Given:
    content_items (Pack).
        - Case 1: Author image path exists for community support pack.
        - Case 2: Author image path exists for partner support pack.
        - Case 3: Author image path doesn't exist for partner support pack.
        - Case 4: Author image path doesn't exist for community support pack.

    When:
        - Calling the AuthorImageExistsValidator is_valid function.

    Then:
        - Make sure the right amount of pack author image path failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    content_items = [
        create_metadata_object(paths=["support"], values=["community"]),
        create_metadata_object(paths=["support"], values=["partner"]),
        create_metadata_object(paths=["support"], values=["partner"]),
        create_metadata_object(paths=["support"], values=["community"]),
    ]
    content_items[2].author_image_file.exist = False
    content_items[3].author_image_file.exist = False
    results = AuthorImageExistsValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        "You've created/modified a yml or package in a partner supported pack without providing an author image as a .png file. Please make sure to add an image at"
        in result.message
        for result in results
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

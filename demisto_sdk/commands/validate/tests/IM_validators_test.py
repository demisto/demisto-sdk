import pytest

from demisto_sdk.commands.common.constants import RelatedFileType
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


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_integration_object(),
        "You've created/modified a yml or package without providing an image as a .png file , please add an image in order to proceed."
        ),
    ],
)
def test_ImageExistsValidator_is_valid_no_image_path(content_item, expected_result):
    """
    Given
    content_item with a not valid image path.
    
    When
    - Calling the ImageExistsValidator is_valid function.
    
    Then
        - Make sure the expected result matches the function result.
    """
    content_item.related_content[RelatedFileType.IMAGE]["path"][0] = ""
    result = ImageExistsValidator().is_valid([content_item])
    if isinstance(expected_result, list):
        assert result == expected_result
    else:
        assert result[0].message == expected_result
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_integration_object(), []),
    ],
)
def test_ImageExistsValidator_is_valid_image_path(content_item, expected_result):
    """
    Given
    content_item with a valid image path.
    
    When
    - Calling the ImageExistsValidator is_valid function.
    
    Then
    - Make sure the expected result matches the function result.
    """
    result = ImageExistsValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
        )
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_metadata_object(paths=['support'],values=['community']), []),
        (create_metadata_object(paths=['support'],values=['partner']),
        "Partner, You've created/modified a yml or package without providing an author image as a .png file , please add an image in order to proceed.")
    ],
)

def test_AuthorImageExistsValidator_is_valid_no_image_path(content_item, expected_result):
    """
    Given
    content_item with a not valid author image path.
    
    When
    - Calling the AuthorImageExistsValidator is_valid function.
    
    Then
    - Make sure the expected result matches the function result.
    """
    content_item.related_content[RelatedFileType.AUTHOR_IMAGE]["path"][0] = ''
    result = AuthorImageExistsValidator().is_valid([content_item])
    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
        )
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_metadata_object(paths=['support'],values=['community']), []),
        (create_metadata_object(paths=['support'],values=['partner']), []),
    ],
)
def test_AuthorImageExistsValidator_is_valid_image_path(content_item, expected_result):
    """
    Given
    content_item with a valid author image path.
    
    When
    - Calling the AuthorImageExistsValidator is_valid function.
    
    Then
    - Make sure the expected result matches the function result.
    """
    result = AuthorImageExistsValidator().is_valid([content_item])
    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result)
    
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

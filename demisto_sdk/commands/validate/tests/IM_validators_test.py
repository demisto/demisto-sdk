from typing import List

import pytest

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
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
    "content_items, empty_image_path_flag, expected_number_of_failures, expected_msgs",
    [
        (
            [create_integration_object()],
            True,
            1,
            ["You've created/modified a yml or package without providing an image as a .png file, please add an image in order to proceed."]
        ),
        (
            [create_integration_object()],
            False,
            0,
            []
        ),
    ],
)
def test_ImageExistsValidator_is_valid_image_path(content_items: List[Integration], empty_image_path_flag: bool, expected_number_of_failures: int, expected_msgs: List[str]):
    """
    Given:
    - content_item (Integration) with either a valid or not valid image path.

    When:
    - Calling the ImageExistsValidator is_valid function.

    Then:
    - Make sure the expected result matches the function result.
    """
    for content_item in content_items:
        if empty_image_path_flag:
            content_item.related_content[RelatedFileType.IMAGE]["path"][0] = ""
    result = ImageExistsValidator().is_valid(content_items)
    assert len(result) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(result, expected_msgs)
        ]
    )
 

@pytest.mark.parametrize(
    "content_items, empty_image_path_flag, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object(paths=['support'], values=['community'])], False, 0, []),
        ([create_metadata_object(paths=['support'], values=['partner'])], False, 0, []),
        ([create_metadata_object(paths=['support'], values=['partner'])],
        True,
        1,
        ["Partner, You've created/modified a yml or package without providing an author image as a .png file, please add an image with the following path Author_image.png in order to proceed."]),
        ([create_metadata_object(paths=['support'], values=['partner'])],
        True,
        0,
        [])
    ],
)
def test_AuthorImageExistsValidator_is_valid_image_path(content_items: List[Pack], empty_image_path_flag: bool , expected_number_of_failures: int, expected_msgs: List[str]):
    """
    Given:
    - content_item (Pack) with either a valid or not valid author image path.

    When:
    - Calling the AuthorImageExistsValidator is_valid function.

    Then:
    - Make sure the expected result matches the function result.
    """
    for content_item in content_items:
        if empty_image_path_flag:
            content_item.related_content[RelatedFileType.AUTHOR_IMAGE]["path"][0] = ""
    result = AuthorImageExistsValidator().is_valid(content_items)
    assert len(result) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(result, expected_msgs)
        ]
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

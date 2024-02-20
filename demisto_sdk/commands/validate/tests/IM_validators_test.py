import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_metadata_object,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM100_no_image_validation import (
    ImageNotExistValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM109_no_author_image_validation import (
    AuthorImageNotExistValidator,
)


@pytest.mark.parametrize(


    "content_item, expected_result",
    [
        (create_integration_object(), "no_image_exists"),
    ]
)
def test_is_valid_no_image_path(content_item, expected_result):
    result = ImageNotExistValidator().is_valid([content_item])
    if isinstance(expected_result, list):
        assert result == expected_result
    else:
        assert result[0].message == expected_result
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_integration_object(), []),
    ]
)
def test_is_valid_image_path(content_item, expected_result):
    result = ImageNotExistValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result)
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_metadata_object(), "no_image_exists"),
    ]
)
def test_is_valid_no_author_image_path(content_item, expected_result):
    result = ImageNotExistValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result)
    
@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (create_integration_object, []),
    ]
)
def test_is_valid_author_image_path(content_item, expected_result):
    result = ImageNotExistValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result)

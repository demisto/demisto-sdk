import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_metadata_object
from demisto_sdk.commands.validate.validators.PA_validators.PA108_pack_metadata_name_not_valid import (
    PackMetadataNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA115_is_created_field_in_iso_format import (
    IsCreatedFieldInISOFormatValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA130_is_current_version_correct_format import (
    IsCurrentVersionCorrectFormatValidator,
)


@pytest.mark.parametrize(
    "expected_number_of_failures, packmetadatas_objects_list",
    [
        (1, [create_metadata_object(["name"], [" "])]),
        (1, [create_metadata_object(["name"], [""])]),
        (0, [create_metadata_object(["name"], ["Working pack name"])]),
        (1, [create_metadata_object(["name"], ["fill mandatory field"])]),
        (
            2,
            [
                create_metadata_object(["name"], ["fill mandatory field"]),
                create_metadata_object(["name"], [""]),
            ],
        ),
        (
            2,
            [
                create_metadata_object(["name"], ["fill mandatory field"]),
                create_metadata_object(["name"], [" "]),
                create_metadata_object(["name"], ["Working pack name"]),
            ],
        ),
    ],
)
def test_PackMetadataNameValidator_is_valid(
    expected_number_of_failures, packmetadatas_objects_list
):
    """
    Given
    packmetadatas_objects_list.
        - Case 1: One pack_metadata with name which is just a space.
        - Case 2: One pack_metadata with name which is an empty string.
        - Case 3: One pack_metadata with name which is a valid name.
        - Case 4: One pack_metadata with name which is the default template.
        - Case 5: One pack_metadata with name which is the default template, and one pack_metadata with name which is an empty string.
        - Case 6: One name which is the default template, one name which is just a space, and one name which is a valid name.
    When
    - Calling the PackMetadataNameValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should fail 1 pack meta data.
        - Case 2: Should fail 1 pack meta data.
        - Case 3: Shouldn't fail any pack meta data.
        - Case 4: Should fail 1 pack meta data.
        - Case 5: Should fail 2 pack metadatas.
        - Case 6: Should fail 2 pack metadatas.
    """
    results = PackMetadataNameValidator().is_valid(packmetadatas_objects_list)
    assert len(results) == expected_number_of_failures
    assert (
        not results
        or results[0].message
        == "Pack metadata name field is either missing or invalid. Please fill valid pack name."
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object(["created"], ["2020-04-14T00:00:00Z"])], 0, []),
        (
            [create_metadata_object(["created"], ["2020-04-14T00:00:001Z"])],
            1,
            [
                "The pack_metadata's 'created' field 2020-04-14T00:00:001Z is not in ISO format."
            ],
        ),
        (
            [
                create_metadata_object(["created"], ["2020-04-14T00:00:00Z"]),
                create_metadata_object(["created"], ["2020-04-14T00:00:001Z"]),
            ],
            1,
            [
                "The pack_metadata's 'created' field 2020-04-14T00:00:001Z is not in ISO format."
            ],
        ),
    ],
)
def test_IsCreatedFieldInISOFormatValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with a valid created field.
        - Case 2: One pack_metadata with an invalid created field.
        - Case 3: One pack_metadata with one a valid created field and one pack_metadata with an invalid created field.
    When
    - Calling the IsCreatedFieldInISOFormatValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any pack meta data.
        - Case 2: Should fail 1 pack meta data (all).
        - Case 3: Should fail 1 pack meta data.
    """
    results = IsCreatedFieldInISOFormatValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsCreatedFieldInISOFormatValidator_fix():
    """
    Given
        A pack_metadata with an invalid created field
    When
    - Calling the IsCreatedFieldInISOFormatValidator fix function.
    Then
        - Make sure the the object created field was parsed and changed correctly and that the right msg was returned.
    """
    content_item = create_metadata_object(["created"], ["2020-04-14T00:00:001Z"])
    assert content_item.created == "2020-04-14T00:00:001Z"
    assert (
        IsCreatedFieldInISOFormatValidator().fix(content_item).message  # type: ignore
        == "Changed the pack_metadata's 'created' field value to 2020-04-14T00:00:01+00:00Z."
    )
    assert content_item.created == "2020-04-14T00:00:01+00:00Z"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        (
            [create_metadata_object(["currentVersion"], ["2.0.5a"])],
            1,
        ),
        (
            [
                create_metadata_object(),
                create_metadata_object(["currentVersion"], ["2.0.531"]),
                create_metadata_object(["currentVersion"], ["12.0.53"]),
                create_metadata_object(["currentVersion"], ["112.0.53"]),
                create_metadata_object(["currentVersion"], ["a12.0.53"]),
                create_metadata_object(["currentVersion"], ["12.01.53"]),
                create_metadata_object(["currentVersion"], ["12.011.53"]),
            ],
            4,
        ),
    ],
)
def test_IsCurrentVersionCorrectFormatValidator_is_valid(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with a valid currentVersion field.
        - Case 2: One pack_metadata with an invalid currentVersion field due to a character in the rightmost side of the version string.
        - Case 3: Seven pack_metadatas.
            - One pack_metadata with a valid currentVersion field.
            - One pack_metadata with an invalid currentVersion field due to a triple digits in the rightmost side of the version string.
            - One pack_metadata with a valid currentVersion field.
            - One pack_metadata with an invalid currentVersion field due to a triple digits in the leftmost side of the version string.
            - One pack_metadata with an invalid currentVersion field due to a character in the leftmost side of the version string.
            - One pack_metadata with a valid currentVersion field.
            - One pack_metadata with an invalid currentVersion field due to a triple digits in the middle of the version string.
    When
    - Calling the IsCurrentVersionCorrectFormatValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any pack meta data.
        - Case 2: Should fail 1 pack meta data (all).
        - Case 3: Should fail 4 pack meta datas.
    """
    results = IsCurrentVersionCorrectFormatValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert (
        not results
        or results[0].message
        == "Pack metadata version format is not valid. Please fill in a valid format (example: 0.0.0)"
    )

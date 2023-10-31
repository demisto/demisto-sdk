import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_metadata_object
from demisto_sdk.commands.validate.validators.PA_validators.PA108_pack_metadata_name_not_valid import (
    PackMetadataNameValidator,
)


@pytest.mark.parametrize(
    "expected_number_of_failures, packmetadatas_objects_list",
    [
        (1, [create_metadata_object("name", " ")]),
        (1, [create_metadata_object("name", "")]),
        (0, [create_metadata_object("name", "Working pack name")]),
        (1, [create_metadata_object("name", "fill mandatory field")]),
        (2, [create_metadata_object("name", "fill mandatory field"), create_metadata_object("name", "")]),
        (2, [create_metadata_object("name", "fill mandatory field"), create_metadata_object("name", " "), create_metadata_object("name", "Working pack name")])
    ],
)
def test_pack_metadata_name_validator(expected_number_of_failures, packmetadatas_objects_list):
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
    - Calling the PackMetadataNameValidator is valid function.
    Then
        - Make sure the right amount of pack metadatas failed.
        - Case 1: Should fail 1 pack meta data.
        - Case 2: Should fail 1 pack meta data.
        - Case 3: Shouldn't fail any pack meta data.
        - Case 4: Should fail 1 pack meta data.
        - Case 5: Should fail 2 pack metadatas.
        - Case 6: Should fail 2 pack metadatas.
    """
    assert len(PackMetadataNameValidator().is_valid(packmetadatas_objects_list, None)) == expected_number_of_failures

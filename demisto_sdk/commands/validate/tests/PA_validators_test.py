import pytest

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    MODULES,
    PACK_METADATA_AUTHOR,
    PACK_METADATA_CATEGORIES,
    PACK_METADATA_CURR_VERSION,
    PACK_METADATA_DESC,
    PACK_METADATA_KEYWORDS,
    PACK_METADATA_NAME,
    PACK_METADATA_SUPPORT,
    PACK_METADATA_TAGS,
    PACK_METADATA_USE_CASES,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_metadata_object,
    create_old_file_pointers,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA100_valid_tags_prefixes import (
    ValidTagsPrefixesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA101_is_version_match_rn import (
    IsVersionMatchRnValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA103_is_valid_categories import (
    IsValidCategoriesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA104_is_valid_modules import (
    IsValidModulesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA105_should_include_modules import (
    ShouldIncludeModulesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA107_missing_field_in_pack_metadata import (
    MissingFieldInPackMetadataValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA108_pack_metadata_name_not_valid import (
    PackMetadataNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA109_is_valid_description_field import (
    IsValidDescriptionFieldValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA111_empty_metadata_fields import (
    EmptyMetadataFieldsValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA113_is_url_or_email_exists import (
    IsURLOrEmailExistsValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA115_is_created_field_in_iso_format import (
    IsCreatedFieldInISOFormatValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA117_is_valid_support_type import (
    IsValidSupportTypeValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA118_is_valid_certificate import (
    IsValidCertificateValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA119_is_valid_use_cases import (
    IsValidUseCasesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA120_is_valid_tags import (
    IsValidTagsValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA121_is_price_changed import (
    IsPriceChangedValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA125_is_valid_pack_name import (
    IsValidPackNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA127_is_valid_url_field import (
    IsValidURLFieldValidator,
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
        - Make sure that the created field was parsed and changed correctly and that the right msg was returned.
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


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        (
            [
                create_metadata_object(
                    fields_to_delete=[
                        PACK_METADATA_NAME,
                        PACK_METADATA_DESC,
                        PACK_METADATA_SUPPORT,
                        PACK_METADATA_CURR_VERSION,
                        PACK_METADATA_AUTHOR,
                        PACK_METADATA_CATEGORIES,
                        PACK_METADATA_TAGS,
                        PACK_METADATA_USE_CASES,
                        PACK_METADATA_KEYWORDS,
                    ]
                )
            ],
            1,
            [
                f"The following fields are missing from the file: {', '.join([PACK_METADATA_NAME, PACK_METADATA_DESC, PACK_METADATA_SUPPORT, PACK_METADATA_CURR_VERSION, PACK_METADATA_AUTHOR, PACK_METADATA_CATEGORIES, PACK_METADATA_TAGS, PACK_METADATA_USE_CASES, PACK_METADATA_KEYWORDS])}."
            ],
        ),
    ],
)
def test_MissingFieldInPackMetadataValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without missing fields.
        - Case 2: One pack_metadata with name, desc, support, currentVersion, author, url, categories, tags, use_cases, keywords fields missing.
    When
    - Calling the MissingFieldInPackMetadataValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    results = MissingFieldInPackMetadataValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        (
            [create_metadata_object(paths=["categories"], values=[[]])],
            0,
            [],
        ),
        (
            [
                create_metadata_object(paths=["name", "tags"], values=["", [""]]),
                create_metadata_object(paths=["useCases"], values=[[""]]),
                create_metadata_object(
                    paths=["keywords", "useCases"], values=[[], [""]]
                ),
            ],
            3,
            [
                "The following fields contains empty values: tags.",
                "The following fields contains empty values: useCases.",
                "The following fields contains empty values: useCases.",
            ],
        ),
    ],
)
def test_EmptyMetadataFieldsValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with all fields filled.
        - Case 2: One pack_metadata with an empty categories field.
        - Case 3: Three pack_metadatas:
            - One pack_metadata with empty name and tags field with empty value.
            - One pack_metadata with an empty useCases field value.
            - One pack_metadata with an empty useCases field value, and an empty keywords field.
    When
    - Calling the EmptyMetadataFieldsValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail all 3 pack metadatas.
            - The first pack_metadata should fail due to an empty tags field.
            - The second pack_metadata should fail due to an empty useCases field.
            - The third pack_metadata should fail due to an empty useCases field.
    """
    results = EmptyMetadataFieldsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_sub_msg",
    [
        ([create_metadata_object()], 0, []),
        (
            [
                create_metadata_object(
                    paths=["tags"], values=[["marketplacev2,xpanse:Data Source"]]
                )
            ],
            0,
            [],
        ),
        (
            [
                create_metadata_object(
                    paths=["tags"], values=[["xsoar,NonApprovedTagPrefix:tag"]]
                ),
            ],
            1,
            "xsoar,NonApprovedTagPrefix:tag",
        ),
    ],
)
def test_ValidTagsPrefixesValidator_is_valid(
    content_items, expected_number_of_failures, expected_sub_msg
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any changes.
        - Case 2: One pack_metadata with valid tags
        - Case 3: One pack_metadata with invalid tags
    When
    - Calling the ValidTagsPrefixesValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail the pack_metadata and include the tag in the message.
    """
    results = ValidTagsPrefixesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not len(results) or expected_sub_msg in results[0].message


def test_ValidTagsPrefixesValidator_fix():
    """
    Given
        A pack_metadata with an invalid tag field
    When
    - Calling the ValidTagsPrefixesValidator fix function.
    Then
        - Make sure that the invalid tags were removed and that the right msg was returned.
    """
    content_item = create_metadata_object(
        paths=["tags"], values=[["xsoar,NonApprovedTagPrefix:tag", "some_valid_tag"]]
    )
    assert content_item.tags == ["xsoar,NonApprovedTagPrefix:tag", "some_valid_tag"]
    validator = ValidTagsPrefixesValidator()
    validator.unapproved_tags_dict[content_item.name] = [
        "xsoar,NonApprovedTagPrefix:tag"
    ]
    assert (
        validator.fix(content_item).message
        == "removed the following invalid tags: xsoar,NonApprovedTagPrefix:tag."
    )
    assert content_item.tags == ["some_valid_tag"]


@pytest.mark.parametrize(
    "content_items, rn_versions, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], ["1.2.12"], 0, []),
        ([create_metadata_object(["currentVersion"], ["1.0.0"])], [""], 0, []),
        (
            [
                create_metadata_object(),
                create_metadata_object(),
                create_metadata_object(["currentVersion"], ["1.0.0"]),
            ],
            ["1.2.13", "", "1.2.14"],
            3,
            [
                "The currentVersion in the metadata (1.2.12) doesn't match the latest rn version (1.2.13).",
                "The currentVersion in the metadata (1.2.12) doesn't match the latest rn version (none).",
                "The currentVersion in the metadata (1.0.0) doesn't match the latest rn version (1.2.14).",
            ],
        ),
    ],
)
def test_IsVersionMatchRnValidator_is_valid(
    content_items, rn_versions, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with currentVersion matching latest_rn_version.
        - Case 2: One pack_metadata with currentVersion = 1.0.0 and no latest_rn_version.
        - Case 3: Three pack_metadatas with mismatches between the currentVersion and latest_rn_version.
    When
    - Calling the IsVersionMatchRnValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail all 3.
    """
    for rn_version, content_item in zip(rn_versions, content_items):
        content_item.latest_rn_version = rn_version
    results = IsVersionMatchRnValidator().is_valid(content_items)
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
                create_metadata_object(),
                create_metadata_object(["categories", "name"], [[], API_MODULES_PACK]),
            ],
            0,
        ),
        ([create_metadata_object(["categories"], [[""]])], 1),
        (
            [
                create_metadata_object(["categories"], [["Utilities"]]),
                create_metadata_object(["categories"], [["Random Category..."]]),
                create_metadata_object(
                    ["categories"], [["Network Security", "Utilities"]]
                ),
            ],
            2,
        ),
    ],
)
def test_IsValidCategoriesValidator_is_valid(
    mocker, content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with a valid category and one pack with empty APIModule pack with an empty categories field.
        - Case 2: One pack_metadata with an empty category field.
        - Case 3: Three pack_metadatas:
            - One pack_metadata with a valid category.
            - One pack_metadata with an invalid category.
            - One pack_metadata with 2 valid categories.
    When
    - Calling the IsValidCategoriesValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Should fail only the pack_metadata with 2 and 0 categories.
    """

    mocker.patch(
        "demisto_sdk.commands.validate.validators.PA_validators.PA103_is_valid_categories.get_current_categories",
        return_value=["Network Security", "Utilities"],
    )
    results = IsValidCategoriesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "The pack metadata categories field doesn't match the standard,\nplease make sure the field contain only one category from the following options: Network Security, Utilities."
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        ([create_metadata_object(["modules"], [["compliance"]])], 0),
        (
            [
                create_metadata_object(
                    ["modules"], [["Random module...", "compliance"]]
                ),
                create_metadata_object(["modules"], [["Random module..."]]),
            ],
            2,
        ),
    ],
)
def test_IsValidModulesValidator_is_valid(content_items, expected_number_of_failures):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any modules.
        - Case 2: One pack_metadata with a valid module.
        - Case 3: Two pack_metadatas:
            - One pack_metadata with a valid module and an invalid one.
            - One pack_metadata with an invalid module.
    When
    - Calling the IsValidModulesValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail both.
    """
    results = IsValidModulesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == f"Module field can include only label from the following options: {', '.join(MODULES)}."
            )
            for result in results
        ]
    )


def test_IsValidModulesValidator_fix():
    """
    Given
        A pack_metadata with module field where 1 module is valid and 1 is invalid.
    When
    - Calling the IsValidModulesValidator fix function.
    Then
        - Make sure the right modules were removed and the right message was returned.
    """
    content_item = create_metadata_object(
        paths=["modules"], values=[["Random module...", "compliance"]]
    )
    assert content_item.modules == ["Random module...", "compliance"]
    validator = IsValidModulesValidator()
    validator.non_approved_modules_dict[content_item.name] = ["Random module..."]
    assert (
        validator.fix(content_item).message
        == "Removed the following label from the modules field: Random module...."
    )
    assert content_item.modules == ["compliance"]


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        ([create_metadata_object(["modules"], [["compliance"]])], 0),
        (
            [
                create_metadata_object(
                    ["modules", "marketplaces"], [["compliance"], ["xsoar"]]
                ),
            ],
            1,
        ),
    ],
)
def test_ShouldIncludeModulesValidator_is_valid(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any modules.
        - Case 2: One pack_metadata with a valid module and MPV2 in marketplaces section.
        - Case 3: One pack_metadata with a valid module and without MPV2 in marketplaces section.
    When
    - Calling the ShouldIncludeModulesValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
    """
    results = ShouldIncludeModulesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "Module field can be added only for XSIAM packs (marketplacev2)."
            )
            for result in results
        ]
    )


def test_ShouldIncludeModulesValidator_fix():
    """
    Given
        A pack_metadata with module field with 1 module.
    When
    - Calling the ShouldIncludeModulesValidator fix function.
    Then
        - Make sure the field was emptied and the right message was returned.
    """
    content_item = create_metadata_object(paths=["modules"], values=[["compliance"]])
    assert content_item.modules == ["compliance"]
    assert (
        ShouldIncludeModulesValidator().fix(content_item).message
        == "Emptied the modules field."
    )
    assert content_item.modules == []


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        (
            [
                create_metadata_object(["description"], [""]),
                create_metadata_object(["description"], ["fill mandatory field"]),
            ],
            2,
        ),
    ],
)
def test_IsValidDescriptionFieldValidator_is_valid(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with a description.
        - Case 2: Two pack_metadatas:
            - One pack_metadata with an empty description.
            - One pack_metadata with "fill mandatory field" as description.
    When
    - Calling the IsValidDescriptionFieldValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail both.
    """
    results = IsValidDescriptionFieldValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "Pack metadata description field is invalid. Please fill valid pack description."
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        (
            [
                create_metadata_object(["url", "email"], ["", ""]),
                create_metadata_object(
                    ["url", "email", "support"], ["", "", "partner"]
                ),
                create_metadata_object(
                    ["url", "email", "support"], ["", "", "developer"]
                ),
            ],
            2,
        ),
    ],
)
def test_IsURLOrEmailExistsValidator_is_valid(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata community supported with url and without email fields.
        - Case 2: Three pack_metadatas:
            - One pack_metadata community supported without both url and email fields.
            - One pack_metadata partner supported without both url and email fields.
            - One pack_metadata developer supported without both url and email fields.
    When
    - Calling the IsURLOrEmailExistsValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail the partner & developer supported metadatas.
    """
    results = IsURLOrEmailExistsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "The pack must include either an email or an URL addresses."
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        ([create_metadata_object(["support"], ["xsoar"])], 0, []),
        ([create_metadata_object(["support"], ["partner"])], 0, []),
        ([create_metadata_object(["support"], ["developer"])], 0, []),
        (
            [
                create_metadata_object(["support"], ["Developer"]),
                create_metadata_object(["support"], ["developerr"]),
                create_metadata_object(["support"], ["someone"]),
            ],
            3,
            [
                "The pack's support type (Developer) is invalid.\nThe pack support type can only be one of the following xsoar, partner, developer, community.",
                "The pack's support type (developerr) is invalid.\nThe pack support type can only be one of the following xsoar, partner, developer, community.",
                "The pack's support type (someone) is invalid.\nThe pack support type can only be one of the following xsoar, partner, developer, community.",
            ],
        ),
    ],
)
def test_IsValidSupportTypeValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One community supported pack_metadata.
        - Case 2: One xsoar supported pack_metadata.
        - Case 3: One partner supported pack_metadata.
        - Case 4: One developer supported pack_metadata.
        - Case 5: Three pack_metadatas:
            - One Developer supported pack_metadata (a valid support type starting with a capital letter).
            - One developerr supported pack_metadata. (a valid support type with the laster letter duplicated).
            - One pack_metadata with a non-supported support type (someone).
    When
    - Calling the IsValidSupportTypeValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Shouldn't fail.
        - Case 4: Shouldn't fail.
        - Case 5: Should fail all 3.
    """
    results = IsValidSupportTypeValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        ([create_metadata_object(["certification"], [""])], 0, []),
        (
            [
                create_metadata_object(["certification"], ["certified"]),
                create_metadata_object(["certification"], ["non-certified"]),
            ],
            1,
            [
                "The certification field (non-certified) is invalid. It can be one of the following: certified, verified."
            ],
        ),
    ],
)
def test_IsValidCertificateValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with `verified` as certification.
        - Case 2: One pack_metadata with an empty certification.
        - Case 3: Two pack_metadatas:
            - One pack_metadata with `certified` as certification.
            - One pack_metadata with `non-certified` as certification.
    When
    - Calling the IsValidCertificateValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail only the meta_data with `non-certified` as certification.
    """
    results = IsValidCertificateValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, old_content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], [create_metadata_object()], 0, []),
        (
            [create_metadata_object(["price"], [10])],
            [create_metadata_object(["price"], [10])],
            0,
            [],
        ),
        (
            [
                create_metadata_object(["price"], [10]),
                create_metadata_object(["price"], [10]),
            ],
            [
                create_metadata_object(["price"], [15]),
                create_metadata_object(["price"], [5]),
            ],
            2,
            [
                "The pack price was changed from 15 to 10 - revert the change.",
                "The pack price was changed from 5 to 10 - revert the change.",
            ],
        ),
        (
            [create_metadata_object(["price"], [10]), create_metadata_object()],
            [create_metadata_object(), create_metadata_object(["price"], [10])],
            2,
            [
                "The pack price was changed from not included to 10 - revert the change.",
                "The pack price was changed from 10 to not included - revert the change.",
            ],
        ),
    ],
)
def test_IsPriceChangedValidator_is_valid(
    content_items, old_content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: Old & new pack metadatas without prices.
        - Case 2: Old & new pack metadatas with the same prices.
        - Case 3: Two pack_metadatas:
            - new pack_metadata with price lower than old one.
            - new pack_metadata with price higher than old one.
        - Case 4: Two pack_metadatas:
            - new pack_metadata with price compare to old one that doesn't have price.
            - new pack_metadata without price compare to old one that have price.
    When
    - Calling the IsPriceChangedValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail both.
        - Case 4: Should fail both.
    """
    create_old_file_pointers(content_items, old_content_items)
    results = IsPriceChangedValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, current_price, new_price, expected_msg",
    [
        (create_metadata_object(), 0, 10, "Reverted the price back to 10."),
        (
            create_metadata_object(["price"], [10]),
            10,
            0,
            "Reverted the price back to 0.",
        ),
        (
            create_metadata_object(["price"], [5]),
            5,
            15,
            "Reverted the price back to 15.",
        ),
    ],
)
def test_IsPriceChangedValidator_fix(
    content_item, current_price, new_price, expected_msg
):
    """
    Given
        - Case 1: Pack_metadata without price field and old price = 10.
        - Case 1: Pack_metadata with price = 10 field and old price = 0.
        - Case 1: Pack_metadata with price = 5 field and old price = 15.
    When
    - Calling the IsPriceChangedValidator fix function.
    Then
        - Make sure the the price was updated and that the right msg was returned.
    """
    assert content_item.price == current_price
    validator = IsPriceChangedValidator()
    validator.old_prices_dict[content_item.name] = new_price
    assert validator.fix(content_item).message == expected_msg
    assert content_item.price == new_price


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_metadata_object()], 0),
        ([create_metadata_object(["url"], ["github.com"])], 0),
        ([create_metadata_object(["url", "support"], ["github.com", "developer"])], 1),
        ([create_metadata_object(["url", "support"], ["github.com", "partner"])], 1),
        (
            [
                create_metadata_object(
                    ["url", "support"], ["github.com/issues", "developer"]
                ),
                create_metadata_object(
                    ["url", "support"], ["github.com/issues", "partner"]
                ),
            ],
            0,
        ),
    ],
)
def test_IsValidURLFieldValidator_is_valid(
    mocker, content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One community supported pack_metadata with valid url.
        - Case 2: One community supported pack_metadata with a url that is invalid for developer & partner supported.
        - Case 3: One developer supported pack_metadata with an invalid url.
        - Case 4: One partner supported pack_metadata with an invalid url.
        - Case 5: Two pack_metadatas:
            - One developer supported pack_metadata with a valid url.
            - One partner supported pack_metadata with a valid url.
    When
    - Calling the IsValidURLFieldValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
        - Case 4: Should fail.
        - Case 5: Shouldn't fail.
    """

    mocker.patch(
        "demisto_sdk.commands.validate.validators.PA_validators.PA103_is_valid_categories.get_current_categories",
        return_value=["Network Security", "Utilities"],
    )
    results = IsValidURLFieldValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "The metadata URL leads to a GitHub repo instead of a support page. Please provide a URL for a support page as detailed in:\nhttps://xsoar.pan.dev/docs/packs/packs-format#pack_metadatajson\nNote that GitHub URLs that lead to a /issues page are also acceptable. (e.g. https://github.com/some_monitored_repo/issues)"
            )
            for result in results
        ]
    )


def test_IsValidURLFieldValidator_fix():
    """
    Given
        A pack_metadata with an invalid URL.
    When
    - Calling the IsValidURLFieldValidator fix function.
    Then
        - Make sure that the URL was fixed correctly and that the right msg was returned.
    """
    content_item = create_metadata_object(
        ["url", "support"], ["github.com", "developer"]
    )
    assert content_item.url == "github.com"
    assert (
        IsValidURLFieldValidator().fix(content_item).message  # type: ignore
        == "Fixed the URL to include the issues endpoint. URL is now: github.com/issues."
    )
    assert content_item.url == "github.com/issues"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object()], 0, []),
        (
            [
                create_metadata_object(["name"], ["Valid_name"]),
                create_metadata_object(["name"], ["Va"]),
                create_metadata_object(["name"], ["name_with_lower_letter"]),
                create_metadata_object(["name"], ["Name_with_Pack"]),
                create_metadata_object(["name"], ["Name_with_partner"]),
            ],
            4,
            [
                "Invalid pack name (Va), pack name should be at least 3 characters long, start with a capital letter, must not contain the words: Pack, Playbook, Integration, Script, partner, community.",
                "Invalid pack name (name_with_lower_letter), pack name should be at least 3 characters long, start with a capital letter, must not contain the words: Pack, Playbook, Integration, Script, partner, community.",
                "Invalid pack name (Name_with_Pack), pack name should be at least 3 characters long, start with a capital letter, must not contain the words: Pack, Playbook, Integration, Script, partner, community.",
                "Invalid pack name (Name_with_partner), pack name should be at least 3 characters long, start with a capital letter, must not contain the words: Pack, Playbook, Integration, Script, partner, community.",
            ],
        ),
    ],
)
def test_IsValidPackNameValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with valid name.
        - Case 2: Five pack_metadatas:
            - One pack with a valid name
            - One pack with a name shorter than 3 chars.
            - One pack with a name starting with small letter.
            - One pack with a name with the word pack.
            - One pack with a name with the word partner.
    When
    - Calling the IsValidPackNameValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail all the last 4 packs.
    """
    results = IsValidPackNameValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object(["tags"], [["Spam"]])], 0, []),
        (
            [
                create_metadata_object(["tags"], [[]]),
                create_metadata_object(["tags"], [["Machine Learning", "Spam"]]),
                create_metadata_object(["tags"], [["NonApprovedTag", "GDPR"]]),
                create_metadata_object(["tags"], [["marketplacev2:Data Source"]]),
                create_metadata_object(
                    ["tags"], [["marketplacev2:NonApprovedTag", "Spam"]]
                ),
            ],
            2,
            [
                "The pack metadata contains non approved tags: NonApprovedTag. The list of approved tags for each marketplace can be found on https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories",
                "The pack metadata contains non approved tags: NonApprovedTag. The list of approved tags for each marketplace can be found on https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories",
            ],
        ),
    ],
)
def test_IsValidTagsValidator_is_valid(
    mocker, content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with valid name.
        - Case 2: Four pack_metadatas: Two with approved tags and two with non-approved tags.
    When
    - Calling the IsValidTagsValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail only 2 packs.
    """
    mocker.patch.object(
        tools,
        "get_dict_from_file",
        return_value=(
            {
                "approved_list": {
                    "common": ["Machine Learning", "Spam", "GDPR"],
                    "xsoar": [],
                    "marketplacev2": ["Data Source"],
                    "xpanse": [],
                }
            },
            "json",
        ),
    )
    results = IsValidTagsValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidTagsValidator_fix():
    """
    Given
        A pack_metadata with an invalid tag field
    When
    - Calling the IsValidTagsValidator fix function.
    Then
        - Make sure that the invalid tags were removed and that the right msg was returned.
    """
    content_item = create_metadata_object(paths=["tags"], values=[["tag_1", "tag_2"]])
    assert content_item.tags == ["tag_1", "tag_2"]
    validator = IsValidTagsValidator()
    validator.non_approved_tags_dict[content_item.name] = ["tag_1"]
    assert validator.fix(content_item).message == "Removed the following tags: tag_1."
    assert content_item.tags == ["tag_2"]


@pytest.mark.parametrize(
    "content_items, approved_use_cases, expected_number_of_failures, expected_msgs",
    [
        ([create_metadata_object([], [])], ["Identity and Access Management"], 0, []),
        ([create_metadata_object(["useCases"], [[]])], [], 0, []),
        (
            [
                create_metadata_object(["useCases"], [["Phishing"]]),
                create_metadata_object(["useCases"], [["Malware", "Case Management"]]),
                create_metadata_object(["useCases"], [["invalid_use_Case"]]),
                create_metadata_object(
                    ["useCases"],
                    [
                        [
                            "Malware",
                            "Case Management",
                            "invalid_use_Case_1",
                        ]
                    ],
                ),
            ],
            ["Phishing", "Malware", "Case Management"],
            2,
            [
                "The pack metadata contains non approved usecases: invalid_use_Case.\nThe list of approved use cases can be found in https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories",
                "The pack metadata contains non approved usecases: invalid_use_Case_1.\nThe list of approved use cases can be found in https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories",
            ],
        ),
    ],
)
def test_IsValidUseCasesValidator_is_valid(
    mocker,
    content_items,
    approved_use_cases,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with valid useCases.
        - Case 2: One pack_metadata without useCases and an empty approved list mock.
        - Case 3: For pack_metadatas:
            - One pack_metadata with an empty useCases section.
            - One pack_metadata with valid useCases section.
            - One pack_metadata with an invalid useCases section.
            - One pack_metadata with useCases section containing two valid and one invalid useCases.
    When
    - Calling the IsValidUseCasesValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail only the last 2 packs.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.PA_validators.PA119_is_valid_use_cases.get_current_usecases",
        return_value=approved_use_cases,
    )
    results = IsValidUseCasesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidUseCasesValidator_fix():
    """
    Given
        A pack_metadata with both valid & invalid useCases.
    When
    - Calling the IsValidUseCasesValidator fix function.
    Then
        - Make sure that the invalid useCases were removed and that the right msg was returned.
    """
    content_item = create_metadata_object(
        ["useCases"],
        [["Malware", "Case Management", "invalid_use_Case_1", "invalid_use_Case_2"]],
    )
    assert content_item.use_cases == [
        "Malware",
        "Case Management",
        "Invalid_use_Case_1",
        "Invalid_use_Case_2",
    ]
    validator = IsValidUseCasesValidator()
    validator.non_approved_usecases_dict[content_item.name] = [
        "Invalid_use_Case_1",
        "Invalid_use_Case_2",
    ]
    assert (
        validator.fix(content_item).message
        == "Removed the following use cases: Invalid_use_Case_1, Invalid_use_Case_2."
    )
    assert content_item.use_cases == ["Malware", "Case Management"]

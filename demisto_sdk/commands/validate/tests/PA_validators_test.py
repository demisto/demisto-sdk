import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    API_MODULES_PACK,
    MARKETPLACE_KEY_PACK_METADATA,
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
    GitStatuses,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseNode
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFile
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
    create_modeling_rule_object,
    create_old_file_pointers,
    create_pack_object,
    create_playbook_object,
    create_script_object,
    create_test_playbook_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.PA_validators.PA100_valid_tags_prefixes import (
    ValidTagsPrefixesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA101_is_version_match_rn import (
    IsVersionMatchRnValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA102_should_pack_be_deprecated import (
    ShouldPackBeDeprecatedValidator,
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
from demisto_sdk.commands.validate.validators.PA_validators.PA114_pack_metadata_version_should_be_raised import (
    PackMetadataVersionShouldBeRaisedValidator,
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
from demisto_sdk.commands.validate.validators.PA_validators.PA124_is_core_pack_depend_on_non_core_packs_valid_all_files import (
    IsCorePackDependOnNonCorePacksValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA124_is_core_pack_depend_on_non_core_packs_valid_list_files import (
    IsCorePackDependOnNonCorePacksValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA125_is_valid_pack_name import (
    IsValidPackNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA127_is_valid_url_field import (
    IsValidURLFieldValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA128_validate_pack_files import (
    PackFilesValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA130_is_current_version_correct_format import (
    IsCurrentVersionCorrectFormatValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA131_is_default_data_source_provided import (
    IsDefaultDataSourceProvidedValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA132_is_valid_default_datasource import (
    IsValidDefaultDataSourceNameValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA133_is_base_pack_has_no_new_dependencies_all_files import (
    IsBasePackHasNoNewDependenciesValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA133_is_base_pack_has_no_new_dependencies_list_files import (
    IsBasePackHasNoNewDependenciesValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA134_supported_modules_coverage import (
    PackSupportedModulesCoverageValidator,
)
from demisto_sdk.commands.validate.validators.PA_validators.PA135_pack_level_ignore_added import (
    PackLevelIgnoreAddedValidator,
)
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


@pytest.mark.parametrize(
    "expected_number_of_failures, packmetadatas_objects_list",
    [
        (1, [create_pack_object(["name"], [" "])]),
        (1, [create_pack_object(["name"], [""])]),
        (0, [create_pack_object(["name"], ["Working pack name"])]),
        (1, [create_pack_object(["name"], ["fill mandatory field"])]),
        (
            2,
            [
                create_pack_object(["name"], ["fill mandatory field"]),
                create_pack_object(["name"], [""]),
            ],
        ),
        (
            2,
            [
                create_pack_object(["name"], ["fill mandatory field"]),
                create_pack_object(["name"], [" "]),
                create_pack_object(["name"], ["Working pack name"]),
            ],
        ),
    ],
)
def test_PackMetadataNameValidator_obtain_invalid_content_items(
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
    - Calling the PackMetadataNameValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should fail 1 pack meta data.
        - Case 2: Should fail 1 pack meta data.
        - Case 3: Shouldn't fail any pack meta data.
        - Case 4: Should fail 1 pack meta data.
        - Case 5: Should fail 2 pack metadatas.
        - Case 6: Should fail 2 pack metadatas.
    """
    results = PackMetadataNameValidator().obtain_invalid_content_items(
        packmetadatas_objects_list
    )
    assert len(results) == expected_number_of_failures
    assert (
        not results
        or results[0].message
        == "Pack metadata name field is either missing or invalid. Please fill valid pack name."
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_pack_object(["created"], ["2020-04-14T00:00:00Z"])], 0, []),
        (
            [create_pack_object(["created"], ["2020-04-14T00:00:001Z"])],
            1,
            [
                "The pack_metadata's 'created' field 2020-04-14T00:00:001Z is not in ISO format."
            ],
        ),
        (
            [
                create_pack_object(["created"], ["2020-04-14T00:00:00Z"]),
                create_pack_object(["created"], ["2020-04-14T00:00:001Z"]),
            ],
            1,
            [
                "The pack_metadata's 'created' field 2020-04-14T00:00:001Z is not in ISO format."
            ],
        ),
    ],
)
def test_IsCreatedFieldInISOFormatValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with a valid created field.
        - Case 2: One pack_metadata with an invalid created field.
        - Case 3: One pack_metadata with one a valid created field and one pack_metadata with an invalid created field.
    When
    - Calling the IsCreatedFieldInISOFormatValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any pack meta data.
        - Case 2: Should fail 1 pack meta data (all).
        - Case 3: Should fail 1 pack meta data.
    """
    results = IsCreatedFieldInISOFormatValidator().obtain_invalid_content_items(
        content_items
    )
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
    content_item = create_pack_object(["created"], ["2020-04-14T00:00:001Z"])
    assert content_item.created == "2020-04-14T00:00:001Z"
    assert (
        IsCreatedFieldInISOFormatValidator().fix(content_item).message  # type: ignore
        == "Changed the pack_metadata's 'created' field value to 2020-04-14T00:00:01+00:00Z."
    )
    assert content_item.created == "2020-04-14T00:00:01+00:00Z"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_pack_object()], 0),
        (
            [create_pack_object(["currentVersion"], ["2.0.5a"])],
            1,
        ),
        (
            [
                create_pack_object(),
                create_pack_object(["currentVersion"], ["2.0.531"]),
                create_pack_object(["currentVersion"], ["12.0.53"]),
                create_pack_object(["currentVersion"], ["112.0.53"]),
                create_pack_object(["currentVersion"], ["a12.0.53"]),
                create_pack_object(["currentVersion"], ["12.01.53"]),
                create_pack_object(["currentVersion"], ["12.011.53"]),
            ],
            4,
        ),
    ],
)
def test_IsCurrentVersionCorrectFormatValidator_obtain_invalid_content_items(
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
    - Calling the IsCurrentVersionCorrectFormatValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any pack meta data.
        - Case 2: Should fail 1 pack meta data (all).
        - Case 3: Should fail 4 pack meta datas.
    """
    results = IsCurrentVersionCorrectFormatValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert (
        not results
        or results[0].message
        == "Pack metadata version format is not valid. Please fill in a valid format (example: 0.0.0)"
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_pack_object()], 0, []),
        (
            [
                create_pack_object(
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
                        MARKETPLACE_KEY_PACK_METADATA,
                    ]
                )
            ],
            1,
            [
                f"The following fields are missing from the file: {', '.join([PACK_METADATA_NAME, PACK_METADATA_DESC, PACK_METADATA_SUPPORT, PACK_METADATA_CURR_VERSION, PACK_METADATA_AUTHOR, PACK_METADATA_CATEGORIES, PACK_METADATA_TAGS, PACK_METADATA_USE_CASES, PACK_METADATA_KEYWORDS, MARKETPLACE_KEY_PACK_METADATA])}."
            ],
        ),
    ],
)
def test_MissingFieldInPackMetadataValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without missing fields.
        - Case 2: One pack_metadata with name, desc, support, currentVersion, author, url, categories, tags, use_cases, keywords, marketplaces fields missing.
    When
    - Calling the MissingFieldInPackMetadataValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    results = MissingFieldInPackMetadataValidator().obtain_invalid_content_items(
        content_items
    )
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
        ([create_pack_object()], 0, []),
        (
            [create_pack_object(paths=["categories"], values=[[]])],
            0,
            [],
        ),
        (
            [
                create_pack_object(paths=["name", "tags"], values=["", [""]]),
                create_pack_object(paths=["useCases"], values=[[""]]),
                create_pack_object(paths=["keywords", "useCases"], values=[[], [""]]),
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
def test_EmptyMetadataFieldsValidator_obtain_invalid_content_items(
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
    - Calling the EmptyMetadataFieldsValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail all 3 pack metadatas.
            - The first pack_metadata should fail due to an empty tags field.
            - The second pack_metadata should fail due to an empty useCases field.
            - The third pack_metadata should fail due to an empty useCases field.
    """
    results = EmptyMetadataFieldsValidator().obtain_invalid_content_items(content_items)
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
        ([create_pack_object()], 0, []),
        (
            [
                create_pack_object(
                    paths=["tags"], values=[["marketplacev2,xpanse:Data Source"]]
                )
            ],
            0,
            [],
        ),
        (
            [
                create_pack_object(
                    paths=["tags"], values=[["xsoar,NonApprovedTagPrefix:tag"]]
                ),
            ],
            1,
            "xsoar,NonApprovedTagPrefix:tag",
        ),
    ],
)
def test_ValidTagsPrefixesValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_sub_msg
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any changes.
        - Case 2: One pack_metadata with valid tags
        - Case 3: One pack_metadata with invalid tags
    When
    - Calling the ValidTagsPrefixesValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail the pack_metadata and include the tag in the message.
    """
    results = ValidTagsPrefixesValidator().obtain_invalid_content_items(content_items)
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
    content_item = create_pack_object(
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
        ([create_pack_object()], ["1.2.12"], 0, []),
        ([create_pack_object(["currentVersion"], ["1.0.0"])], [""], 0, []),
        (
            [
                create_pack_object(),
                create_pack_object(),
                create_pack_object(["currentVersion"], ["1.0.0"]),
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
def test_IsVersionMatchRnValidator_obtain_invalid_content_items(
    content_items, rn_versions, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with currentVersion matching latest_rn_version.
        - Case 2: One pack_metadata with currentVersion = 1.0.0 and no latest_rn_version.
        - Case 3: Three pack_metadatas with mismatches between the currentVersion and latest_rn_version.
    When
    - Calling the IsVersionMatchRnValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail all 3.
    """
    for rn_version, content_item in zip(rn_versions, content_items):
        content_item.latest_rn_version = rn_version
    results = IsVersionMatchRnValidator().obtain_invalid_content_items(content_items)
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
                create_pack_object(),
                create_pack_object(["categories", "name"], [[], API_MODULES_PACK]),
            ],
            0,
        ),
        ([create_pack_object(["categories"], [[""]])], 1),
        (
            [
                create_pack_object(["categories"], [["Utilities"]]),
                create_pack_object(["categories"], [["Random Category..."]]),
                create_pack_object(["categories"], [["Network Security", "Utilities"]]),
                create_pack_object(
                    ["categories"], [["Utilities", "Random Category..."]]
                ),
            ],
            2,
        ),
    ],
)
def test_IsValidCategoriesValidator_obtain_invalid_content_items(
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
            - One pack_metadata with 1 valid and 1 invalid categories.
    When
    - Calling the IsValidCategoriesValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Should fail only the pack_metadata with 2 where 1 is a valid and the other isn't and 0 categories.
    """

    mocker.patch(
        "demisto_sdk.commands.validate.validators.PA_validators.PA103_is_valid_categories.get_current_categories",
        return_value=["Network Security", "Utilities"],
    )
    results = IsValidCategoriesValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "The pack metadata categories field doesn't match the standard,\nplease make sure the field contain at least one category from the following options: Network Security, Utilities."
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_pack_object()], 0),
        ([create_pack_object(["modules"], [["compliance"]])], 0),
        (
            [
                create_pack_object(["modules"], [["Random module...", "compliance"]]),
                create_pack_object(["modules"], [["Random module..."]]),
            ],
            2,
        ),
    ],
)
def test_IsValidModulesValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any modules.
        - Case 2: One pack_metadata with a valid module.
        - Case 3: Two pack_metadatas:
            - One pack_metadata with a valid module and an invalid one.
            - One pack_metadata with an invalid module.
    When
    - Calling the IsValidModulesValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail both.
    """
    results = IsValidModulesValidator().obtain_invalid_content_items(content_items)
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
    content_item = create_pack_object(
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
        ([create_pack_object()], 0),
        ([create_pack_object(["modules"], [["compliance"]])], 0),
        (
            [
                create_pack_object(
                    ["modules", "marketplaces"], [["compliance"], ["xsoar"]]
                ),
            ],
            1,
        ),
    ],
)
def test_ShouldIncludeModulesValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata without any modules.
        - Case 2: One pack_metadata with a valid module and MPV2 in marketplaces section.
        - Case 3: One pack_metadata with a valid module and without MPV2 in marketplaces section.
    When
    - Calling the ShouldIncludeModulesValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
    """
    results = ShouldIncludeModulesValidator().obtain_invalid_content_items(
        content_items
    )
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
    content_item = create_pack_object(paths=["modules"], values=[["compliance"]])
    assert content_item.modules == ["compliance"]
    assert (
        ShouldIncludeModulesValidator().fix(content_item).message
        == "Emptied the modules field."
    )
    assert content_item.modules == []


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_pack_object()], 0),
        (
            [
                create_pack_object(["description"], [""]),
                create_pack_object(["description"], ["fill mandatory field"]),
            ],
            2,
        ),
    ],
)
def test_IsValidDescriptionFieldValidator_obtain_invalid_content_items(
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
    - Calling the IsValidDescriptionFieldValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail both.
    """
    results = IsValidDescriptionFieldValidator().obtain_invalid_content_items(
        content_items
    )
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
    "pack, integrations, expected_number_of_failures",
    [
        (
            create_pack_object(),
            [
                create_integration_object(
                    ["script.isfetch", "name"], ["true", "TestIntegration1"]
                ),
                create_integration_object(["script.isfetch"], ["true"]),
            ],
            1,
        ),
        (
            create_pack_object(["defaultDataSource"], ["defaultDataSourceValue"]),
            [
                create_integration_object(
                    ["script.isfetch", "name"], ["true", "defaultDataSourceValue"]
                ),
                create_integration_object(["script.isfetch"], ["true"]),
            ],
            0,
        ),
        (
            create_pack_object(),
            [create_integration_object(["script.isfetch"], ["true"])],
            0,
        ),
        (
            create_pack_object(["marketplaces"], [[MarketplaceVersions.XSOAR]]),
            [
                create_integration_object(
                    ["script.isfetch", "name"], ["true", "TestIntegration1"]
                ),
                create_integration_object(["script.isfetch"], ["true"]),
            ],
            0,
        ),
    ],
)
def test_IsDefaultDataSourceProvidedValidator_obtain_invalid_content_items(
    pack, integrations, expected_number_of_failures
):
    """
    Given
    content_items.
        - Case 1: One XSIAM pack_metadata with 2 integrations and no defaultDataSource.
        - Case 2: One XSIAM pack_metadata with 2 integrations and a defaultDataSource.
        - Case 3: One XSIAM pack_metadata with one integration and no defaultDataSource.
        - Case 4: One non XSIAM pack_metadata with 2 integrations.

    When
        - Calling the IsDefaultDataSourceProvidedValidator obtain_invalid_content_items function.

    Then
        - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
        - Case 3: Shouldn't fail.
        - Case 4: Shouldn't fail.
    """
    pack.content_items.integration.extend(integrations)
    results = IsDefaultDataSourceProvidedValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "The pack metadata does not contain the 'defaultDataSource' field. "
                "Please specify a defaultDataSource from the following options: ['TestIntegration', 'TestIntegration']."
            )
            for result in results
        ]
    )


def test_IsDefaultDataSourceProvidedValidator_fix():
    """
    Given
        - A pack_metadata with no defaultDataSource, for a pack with one event collector

    When
        - Calling the IsDefaultDataSourceProvidedValidator fix function.

    Then
        - Make sure that the defaultDataSource is set to the event collector integration id
    """
    content_item = create_pack_object()
    integrations = [
        create_integration_object(
            ["script.isfetchevents", "commonfields.id"],
            ["true", "defaultDataSourceValue"],
        ),
        create_integration_object(["script.isfetch"], ["true"]),
    ]
    content_item.content_items.integration.extend(integrations)
    assert not content_item.default_data_source_id
    validator = IsDefaultDataSourceProvidedValidator()
    assert validator.fix(content_item).message == (
        "Set the 'defaultDataSource' for 'HelloWorld' pack to the "
        "'defaultDataSourceValue' integration, as it is an event collector."
    )
    assert content_item.default_data_source_id == "defaultDataSourceValue"


@pytest.mark.parametrize(
    "pack, integrations, expected_number_of_failures",
    [
        (
            create_pack_object(
                ["defaultDataSource"], ["InvalidDefaultDataSourceValue"]
            ),
            [
                create_integration_object(
                    ["script.isfetch", "commonfields.id"], ["true", "TestIntegration1"]
                ),
                create_integration_object(["script.isfetch"], ["true"]),
            ],
            1,
        ),
        (
            create_pack_object(["defaultDataSource"], ["defaultDataSourceValue"]),
            [
                create_integration_object(
                    ["script.isfetch", "commonfields.id"],
                    ["true", "defaultDataSourceValue"],
                ),
                create_integration_object(["script.isfetch"], ["true"]),
            ],
            0,
        ),
        (
            create_pack_object(),
            [create_integration_object(["script.isfetch"], ["true"])],
            0,
        ),
    ],
)
def test_IsValidDefaultDataSourceNameValidator_obtain_invalid_content_items(
    pack, integrations, expected_number_of_failures
):
    """
    Given
        - Case 1: One XSIAM pack_metadata with 2 integrations and a defaultDataSource that is not one of the pack integrations.
        - Case 2: One XSIAM pack_metadata with 2 integrations and a defaultDataSource that is one of the pack integrations.
        - Case 3: One XSIAM pack_metadata with one integration and no defaultDataSource.

    When
        - Calling the IsValidDefaultDataSourceNameValidator obtain_invalid_content_items function.

    Then
        - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
        - Case 3: Shouldn't fail.
    """
    pack.content_items.integration.extend(integrations)
    results = IsValidDefaultDataSourceNameValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == expected_number_of_failures
    assert not results or all(
        [
            (
                result.message
                == "Pack metadata contains an invalid 'defaultDataSource': InvalidDefaultDataSourceValue. "
                "Please fill in a valid datasource integration, one of these options: ['TestIntegration1', 'TestIntegration']."
            )
            for result in results
        ]
    )


def test_IsValidDefaultDataSourceNameValidator_fix():
    """
    Given
        - A pack_metadata with a defaultDataSource value that holds the integration display name instead of integration id

    When
        - Calling the IsValidDefaultDataSourceNameValidator fix function.

    Then
        - Make sure that the defaultDataSource is set to the integration id
    """
    content_item = create_pack_object(
        ["defaultDataSource"], ["Default Data Source Value"]
    )
    integrations = [
        create_integration_object(
            ["script.isfetch", "commonfields.id", "display"],
            ["true", "defaultDataSourceValue", "Default Data Source Value"],
        ),
        create_integration_object(["script.isfetch"], ["true"]),
    ]
    content_item.content_items.integration.extend(integrations)
    assert content_item.default_data_source_id == "Default Data Source Value"
    validator = IsValidDefaultDataSourceNameValidator()
    assert validator.fix(content_item).message == (
        "Updated the 'defaultDataSource' for the 'HelloWorld' pack to use the 'defaultDataSourceValue' "
        "integration ID instead of the display name that was previously used."
    )
    assert content_item.default_data_source_id == "defaultDataSourceValue"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_pack_object()], 0),
        (
            [
                create_pack_object(["url", "email"], ["", ""]),
                create_pack_object(["url", "email", "support"], ["", "", "partner"]),
                create_pack_object(["url", "email", "support"], ["", "", "developer"]),
            ],
            2,
        ),
    ],
)
def test_IsURLOrEmailExistsValidator_obtain_invalid_content_items(
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
    - Calling the IsURLOrEmailExistsValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail the partner & developer supported metadatas.
    """
    results = IsURLOrEmailExistsValidator().obtain_invalid_content_items(content_items)
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
        ([create_pack_object()], 0, []),
        ([create_pack_object(["support"], ["xsoar"])], 0, []),
        ([create_pack_object(["support"], ["partner"])], 0, []),
        ([create_pack_object(["support"], ["developer"])], 0, []),
        (
            [
                create_pack_object(["support"], ["Developer"]),
                create_pack_object(["support"], ["developerr"]),
                create_pack_object(["support"], ["someone"]),
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
def test_IsValidSupportTypeValidator_obtain_invalid_content_items(
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
    - Calling the IsValidSupportTypeValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Shouldn't fail.
        - Case 4: Shouldn't fail.
        - Case 5: Should fail all 3.
    """
    results = IsValidSupportTypeValidator().obtain_invalid_content_items(content_items)
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
        ([create_pack_object()], 0, []),
        ([create_pack_object(["certification"], [""])], 0, []),
        (
            [
                create_pack_object(["certification"], ["certified"]),
                create_pack_object(["certification"], ["non-certified"]),
            ],
            1,
            [
                "The certification field (non-certified) is invalid. It can be one of the following: certified, verified."
            ],
        ),
    ],
)
def test_IsValidCertificateValidator_obtain_invalid_content_items(
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
    - Calling the IsValidCertificateValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail only the meta_data with `non-certified` as certification.
    """
    results = IsValidCertificateValidator().obtain_invalid_content_items(content_items)
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
        ([create_pack_object()], [create_pack_object()], 0, []),
        (
            [create_pack_object(["price"], [10])],
            [create_pack_object(["price"], [10])],
            0,
            [],
        ),
        (
            [
                create_pack_object(["price"], [10]),
                create_pack_object(["price"], [10]),
            ],
            [
                create_pack_object(["price"], [15]),
                create_pack_object(["price"], [5]),
            ],
            2,
            [
                "The pack price was changed from 15 to 10 - revert the change.",
                "The pack price was changed from 5 to 10 - revert the change.",
            ],
        ),
        (
            [create_pack_object(["price"], [10]), create_pack_object()],
            [create_pack_object(), create_pack_object(["price"], [10])],
            2,
            [
                "The pack price was changed from not included to 10 - revert the change.",
                "The pack price was changed from 10 to not included - revert the change.",
            ],
        ),
    ],
)
def test_IsPriceChangedValidator_obtain_invalid_content_items(
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
    - Calling the IsPriceChangedValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail both.
        - Case 4: Should fail both.
    """
    create_old_file_pointers(content_items, old_content_items)
    results = IsPriceChangedValidator().obtain_invalid_content_items(content_items)
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
        (create_pack_object(), 0, 10, "Reverted the price back to 10."),
        (
            create_pack_object(["price"], [10]),
            10,
            0,
            "Reverted the price back to 0.",
        ),
        (
            create_pack_object(["price"], [5]),
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
        ([create_pack_object()], 0),
        ([create_pack_object(["url"], ["github.com"])], 0),
        ([create_pack_object(["url", "support"], ["github.com", "developer"])], 1),
        ([create_pack_object(["url", "support"], ["github.com", "partner"])], 1),
        (
            [
                create_pack_object(
                    ["url", "support"], ["github.com/issues", "developer"]
                ),
                create_pack_object(
                    ["url", "support"], ["github.com/issues", "partner"]
                ),
            ],
            0,
        ),
    ],
)
def test_IsValidURLFieldValidator_obtain_invalid_content_items(
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
    - Calling the IsValidURLFieldValidator obtain_invalid_content_items function.
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
    results = IsValidURLFieldValidator().obtain_invalid_content_items(content_items)
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
    content_item = create_pack_object(["url", "support"], ["github.com", "developer"])
    assert content_item.url == "github.com"
    assert (
        IsValidURLFieldValidator().fix(content_item).message  # type: ignore
        == "Fixed the URL to include the issues endpoint. URL is now: github.com/issues."
    )
    assert content_item.url == "github.com/issues"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_pack_object()], 0, []),
        (
            [
                create_pack_object(["name"], ["Valid_name"]),
                create_pack_object(["name"], ["Va"]),
                create_pack_object(["name"], ["name_with_lower_letter"]),
                create_pack_object(["name"], ["Name_with_Pack"]),
                create_pack_object(["name"], ["Name_with_partner"]),
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
def test_IsValidPackNameValidator_obtain_invalid_content_items(
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
    - Calling the IsValidPackNameValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail all the last 4 packs.
    """
    results = IsValidPackNameValidator().obtain_invalid_content_items(content_items)
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
        ([create_pack_object(["tags"], [["Spam"]])], 0, []),
        (
            [
                create_pack_object(["tags"], [[]]),
                create_pack_object(["tags"], [["Machine Learning", "Spam"]]),
                create_pack_object(["tags"], [["NonApprovedTag", "GDPR"]]),
                create_pack_object(["tags"], [["marketplacev2:Data Source"]]),
                create_pack_object(
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
def test_IsValidTagsValidator_obtain_invalid_content_items(
    mocker, content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: One pack_metadata with valid name.
        - Case 2: Four pack_metadatas: Two with approved tags and two with non-approved tags.
    When
    - Calling the IsValidTagsValidator obtain_invalid_content_items function.
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
    results = IsValidTagsValidator().obtain_invalid_content_items(content_items)
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
    content_item = create_pack_object(paths=["tags"], values=[["tag_1", "tag_2"]])
    assert content_item.tags == ["tag_1", "tag_2"]
    validator = IsValidTagsValidator()
    validator.non_approved_tags_dict[content_item.name] = ["tag_1"]
    assert validator.fix(content_item).message == "Removed the following tags: tag_1."
    assert content_item.tags == ["tag_2"]


@pytest.mark.parametrize(
    "content_items, approved_use_cases, expected_number_of_failures, expected_msgs",
    [
        ([create_pack_object([], [])], ["Identity and Access Management"], 0, []),
        ([create_pack_object(["useCases"], [[]])], [], 0, []),
        (
            [
                create_pack_object(["useCases"], [["Phishing"]]),
                create_pack_object(["useCases"], [["Malware", "Case Management"]]),
                create_pack_object(["useCases"], [["invalid_use_Case"]]),
                create_pack_object(
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
def test_IsValidUseCasesValidator_obtain_invalid_content_items(
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
    - Calling the IsValidUseCasesValidator obtain_invalid_content_items function.
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
    results = IsValidUseCasesValidator().obtain_invalid_content_items(content_items)
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
    content_item = create_pack_object(
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


@pytest.mark.parametrize(
    "pack, is_deprecated_pack, integrations, playbooks, scripts, modeling_rules, expected_number_of_failures, "
    "expected_msgs",
    [
        (create_pack_object(), False, [], [], [], [], 0, []),
        (
            create_pack_object(),
            False,
            [create_integration_object(["deprecated"], [True])],
            [],
            [],
            [],
            1,
            [
                "The Pack HelloWorld should be deprecated, as all its content items are deprecated.\nThe name of the pack in the pack_metadata.json should end with (Deprecated).\nThe description of the pack in the pack_metadata.json should be one of the following formats:\n1. 'Deprecated. Use PACK_NAME instead.'\n2. 'Deprecated. REASON No available replacement.'"
            ],
        ),
        (
            create_pack_object(),
            False,
            [],
            [create_playbook_object(["deprecated"], [True])],
            [create_script_object()],
            [],
            0,
            [],
        ),
        (
            create_pack_object(),
            True,
            [create_integration_object(["deprecated"], [True])],
            [],
            [],
            [],
            0,
            [],
        ),
        (
            create_pack_object(),
            False,
            [create_integration_object(["deprecated"], [True])],
            [],
            [],
            [create_modeling_rule_object()],
            0,
            [],
        ),
    ],
)
def test_ShouldPackBeDeprecatedValidator_obtain_invalid_content_items(
    pack,
    is_deprecated_pack,
    integrations,
    playbooks,
    scripts,
    modeling_rules,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given
    A pack objects, and a list of related integrations, playbooks & scripts.
        - Case 1: A non deprecated pack without any integrations, playbooks & scripts.
        - Case 2: A non deprecated pack with a deprecated integration.
        - Case 3: A non deprecated pack with a deprecated integration and a non deprecated script
        - Case 4: A deprecated pack with a deprecated integration.
        - Case 5: A non deprecated pack with a deprecated integration and a non deprecated modeling_rule
    When
    - Calling the ShouldPackBeDeprecatedValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of packs failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Shouldn't fail.
        - Case 4: Shouldn't fail.
        - Case 5: Shouldn't fail.
    """
    pack.deprecated = is_deprecated_pack
    pack.content_items.integration.extend(integrations)
    pack.content_items.playbook.extend(playbooks)
    pack.content_items.script.extend(scripts)
    pack.content_items.modeling_rule.extend(modeling_rules)
    content_items = [pack]
    results = ShouldPackBeDeprecatedValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize("file_attribute", ("readme", "secrets_ignore", "pack_ignore"))
def test_PackFilesValidator(file_attribute: str):
    """
    Given   A pack
    When    Calling PackFilesValidator.obtain_invalid_content_items
    Then    Make sure it only fails when one of the required files has exist=False
    """
    pack = create_pack_object()
    meta_file: RelatedFile = getattr(pack, file_attribute)

    assert meta_file.exist  # sanity check
    assert not PackFilesValidator().obtain_invalid_content_items(
        [pack]
    )  # valid as default

    meta_file.exist = False  # mock deleting the file
    assert PackFilesValidator().obtain_invalid_content_items(
        [pack]
    )  # invalid once deleted


@pytest.mark.parametrize("file_attribute", ("readme", "secrets_ignore", "pack_ignore"))
def test_PackFilesValidator_fix(file_attribute: str):
    """
    Given   A pack
    When    Calling PackFilesValidator.fix
    Then    Make sure the file is created
    """
    pack = create_pack_object()
    meta_file: RelatedFile = getattr(pack, file_attribute)

    meta_file.file_path.unlink()
    meta_file.exist = False

    assert not meta_file.exist  # sanity check
    assert not meta_file.file_path.exists()  # sanity check

    assert PackFilesValidator().obtain_invalid_content_items(
        [pack]
    )  # invalid once deleted
    PackFilesValidator().fix(pack)

    assert meta_file.file_path.exists()
    assert meta_file.exist  # changed in the fix


@pytest.mark.parametrize(
    "old_version, current_version, expected_invalid",
    [("1.0.0", "1.0.1", 0), ("1.0.0", "1.0.0", 1), ("1.1.0", "1.0.1", 1)],
)
def test_PackMetadataVersionShouldBeRaisedValidator(
    mocker, old_version, current_version, expected_invalid
):
    """
    Given: A previous pack version and a current pack version.
    When: Running PackMetadataVersionShouldBeRaisedValidator validator.
    Then: Assure the validation succeeds if the current version <= previous version.
    Cases:
        1) current version > previous version: 0 validation errors.
        2) current version = previous version: 1 validation errors.
        3) current version < previous version: 1 validation errors.
    """
    error_message = (
        "The pack version (currently: {old_version}) needs to be raised - "
        "make sure you are merged from master and "
        "update release notes by running:\n"
        "`demisto-sdk update-release-notes -g` - for automatically generation of release notes and version\n"
        "`demisto-sdk update-release-notes -i Packs/{pack} -u "
        "(major|minor|revision|documentation)` for a specific pack and version."
    )
    with ChangeCWD(REPO.path):
        integration = create_integration_object(
            pack_info={"currentVersion": current_version}
        )
        pack = integration.in_pack
        integration.git_status = GitStatuses.MODIFIED

        old_pack = pack.copy(deep=True)
        old_pack.current_version = old_version

        pack.old_base_content_object = old_pack
        mocker.patch.object(
            BaseNode, "to_dict", return_value={"current_version": old_version}
        )
        version_bump_validator = PackMetadataVersionShouldBeRaisedValidator()
        results = version_bump_validator.obtain_invalid_content_items(
            [pack, integration]
        )
        assert len(results) == expected_invalid
        for result in results:
            assert (
                error_message.format(old_version=old_version, pack=pack.name)
                in result.message
            )


def test_PackMetadataVersionShouldBeRaisedValidator_new_pack():
    """
    Given: A new pack with a script.
    When: Running PackMetadataVersionShouldBeRaisedValidator validator.
    Then: Ensure a validation error is not raised.
    """
    pack = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.0"],
    )
    pack.git_status = GitStatuses.ADDED
    script = create_script_object()
    script.pack = pack

    validator = PackMetadataVersionShouldBeRaisedValidator()
    results = validator.obtain_invalid_content_items([pack, script])
    assert len(results) == 0


def test_PackMetadataVersionShouldBeRaisedValidator_metadata_change(mocker):
    """
    Given: A previous pack version = current pack version with a price change within the pack metadata.
    When: Running PackMetadataVersionShouldBeRaisedValidator validator.
    Then: Assure the validation fails.
    """
    error_message = (
        "The pack version (currently: {old_version}) needs to be raised - "
        "make sure you are merged from master and "
        "update release notes by running:\n"
        "`demisto-sdk update-release-notes -g` - for automatically generation of release notes and version\n"
        "`demisto-sdk update-release-notes -i Packs/{pack} -u "
        "(major|minor|revision|documentation)` for a specific pack and version."
    )
    old_version = "1.0.0"
    current_version = "1.0.0"
    with ChangeCWD(REPO.path):
        pack = create_pack_object(["currentVersion", "price"], [current_version, 5])
        old_pack = pack.copy(deep=True)
        old_pack.current_version = old_version

        pack.old_base_content_object = old_pack
        mocker.patch.object(
            BaseNode,
            "to_dict",
            side_effect=[
                {"current_version": old_version, "price": 3},
                {"current_version": old_version, "price": 5},
            ],
        )
        version_bump_validator = PackMetadataVersionShouldBeRaisedValidator()
        results = version_bump_validator.obtain_invalid_content_items([pack])
        assert len(results) == 1
        for result in results:
            assert (
                error_message.format(old_version=old_version, pack=pack.name)
                in result.message
            )


@pytest.fixture
def repo_for_test_pa_124(graph_repo: Repo, mocker: MockerFixture):
    """
    Creates a test repository with three packs for testing PA124 validator.

    This fixture sets up a graph repository with the following structure:
    - CorePack: A core pack containing a playbook that uses a command from Pack2.
                Has a mandatory dependency on Pack2.
    - Pack2: Contains an integration with two commands.
             Serves as a mandatory dependency for CorePack.
    - Pack3: An empty pack for additional testing scenarios.

    The fixture also mocks the core pack identification to ensure CorePack is recognized as a core pack.
    """
    mocker.patch(
        "demisto_sdk.commands.validate.validators.PA_validators.PA124_is_core_pack_depend_on_non_core_packs_valid.get_marketplace_to_core_packs",
        return_value={MarketplaceVersions.XSOAR: {"CorePack"}},
    )
    playbook_using_pack2_command = {
        "id": "UsingPack2Command",
        "name": "UsingPack2Command",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "MyIntegration1|||test-command-1",
                    "brand": "MyIntegration1",
                    "iscommand": "true",
                },
            }
        },
    }
    # Core Pack 1: playbook uses command from pack 2
    pack_1 = graph_repo.create_pack("CorePack")

    pack_1.create_playbook("UsingCorePackCommand", yml=playbook_using_pack2_command)

    # Define Pack2 as a mandatory dependency for CorePack
    pack_1.pack_metadata.update({"dependencies": {"Pack2": {"mandatory": True}}})

    # Pack 2: mandatory dependency for CorePack
    pack_2 = graph_repo.create_pack("Pack2")
    integration = pack_2.create_integration("MyIntegration1")
    integration.set_commands(["test-command-1", "test-command-2"])

    # Pack3
    graph_repo.create_pack("Pack3")
    return graph_repo


def test_IsCorePackDependOnNonCorePacksValidatorAllFiles_invalid(
    repo_for_test_pa_124: Repo,
):
    """
    Test the IsCorePackDependOnNonCorePacksValidatorAllFiles validator for invalid dependencies.
    Given:
        - A test repository (repo_for_test_pa_124) with:
            - A core pack "CorePack" that has a mandatory dependency on "Pack2"
            - "Pack2" which is not a core pack
            - "Pack3" as an additional pack

    When:
        - Running the IsCorePackDependOnNonCorePacksValidatorAllFiles validator

    Then:
        - The validator should return a result indicating that CorePack
          depends on the non-core pack Pack2
        - The error message should clearly state the violation and suggest reverting the change
    """
    graph_interface = repo_for_test_pa_124.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsCorePackDependOnNonCorePacksValidatorAllFiles().obtain_invalid_content_items(
            []
        )
    )
    assert (
        results[0].message
        == "The core pack CorePack cannot depend on non-core pack(s): Pack2."
    )


def test_IsCorePackDependOnNonCorePacksValidatorListFiles(repo_for_test_pa_124: Repo):
    """
    Test the IsCorePackDependOnNonCorePacksValidatorListFiles validator for specific packs.
    Given:
        - A test repository (repo_for_test_pa_124) with:
            - A core pack "CorePack" that has a mandatory dependency on "Pack2"
            - "Pack2" which is not a core pack
            - "Pack3" as an additional pack without dependencies

    When:
        - Running the IsCorePackDependOnNonCorePacksValidatorListFiles validator on CorePack
        - Running the same validator on Pack3

    Then:
        - For CorePack: The validator should return a result indicating the invalid dependency
        - For Pack3: The validator should not return any results (no invalid dependencies)
    """
    graph_interface = repo_for_test_pa_124.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsCorePackDependOnNonCorePacksValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_124.packs[0]]
        )
    )
    assert (
        results[0].message
        == "The core pack CorePack cannot depend on non-core pack(s): Pack2."
    )

    results = (
        IsCorePackDependOnNonCorePacksValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_124.packs[2]]
        )
    )
    assert not results


@pytest.fixture
def repo_for_test_pa_133_valid(graph_repo: Repo):
    """
    Creates a test repository with a Base pack that has only allowed dependencies.
    The Base pack uses a script from Core pack (allowed dependency).
    """
    # Base pack with a script that uses a command from Core
    base_pack = graph_repo.create_pack("Base")
    base_pack.create_script("BaseScript")
    base_pack.pack_metadata.update({"dependencies": {"Core": {"mandatory": True}}})

    # Core pack (allowed dependency)
    core_pack = graph_repo.create_pack("Core")
    core_integration = core_pack.create_integration("CoreIntegration")
    core_integration.set_commands(["core-command"])

    # AggregatedScripts pack (allowed dependency)
    graph_repo.create_pack("AggregatedScripts")

    return graph_repo


@pytest.fixture
def repo_for_test_pa_133_invalid(graph_repo: Repo):
    """
    Creates a test repository with a Base pack that has a new (unexpected) dependency.
    The Base pack has a playbook that uses a command from NewPack (not allowed).
    """
    playbook_using_newpack_command = {
        "id": "BasePlaybook",
        "name": "BasePlaybook",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "NewIntegration|||new-command",
                    "brand": "NewIntegration",
                    "iscommand": "true",
                },
            }
        },
    }
    # Base pack with a playbook that uses a command from NewPack
    base_pack = graph_repo.create_pack("Base")
    base_pack.create_playbook("BasePlaybook", yml=playbook_using_newpack_command)
    base_pack.pack_metadata.update({"dependencies": {"NewPack": {"mandatory": True}}})

    # NewPack (not an allowed dependency)
    new_pack = graph_repo.create_pack("NewPack")
    new_integration = new_pack.create_integration("NewIntegration")
    new_integration.set_commands(["new-command"])

    return graph_repo


def test_IsBasePackHasNoNewDependenciesValidatorAllFiles_valid(
    repo_for_test_pa_133_valid: Repo,
):
    """
    Test the IsBasePackHasNoNewDependenciesValidatorAllFiles validator with valid dependencies.
    Given:
        - A test repository with a Base pack that only depends on Core (allowed dependency).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorAllFiles validator.

    Then:
        - The validator should not return any results (no invalid dependencies).
    """
    graph_interface = repo_for_test_pa_133_valid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorAllFiles().obtain_invalid_content_items(
            []
        )
    )
    assert not results


def test_IsBasePackHasNoNewDependenciesValidatorAllFiles_invalid(
    repo_for_test_pa_133_invalid: Repo,
):
    """
    Test the IsBasePackHasNoNewDependenciesValidatorAllFiles validator with invalid dependencies.
    Given:
        - A test repository with a Base pack that depends on NewPack (not allowed).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorAllFiles validator.

    Then:
        - The validator should return a result indicating that the Base pack
          has an unexpected dependency on NewPack.
    """
    graph_interface = repo_for_test_pa_133_invalid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorAllFiles().obtain_invalid_content_items(
            []
        )
    )
    assert len(results) == 1
    assert "NewPack" in results[0].message
    assert "unexpected dependencies" in results[0].message


def test_IsBasePackHasNoNewDependenciesValidatorListFiles_valid(
    repo_for_test_pa_133_valid: Repo,
):
    """
    Test the IsBasePackHasNoNewDependenciesValidatorListFiles validator with valid dependencies.
    Given:
        - A test repository with a Base pack that only depends on Core (allowed dependency).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorListFiles validator on the Base pack.

    Then:
        - The validator should not return any results (no invalid dependencies).
    """
    graph_interface = repo_for_test_pa_133_valid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_133_valid.packs[0]]
        )
    )
    assert not results


def test_IsBasePackHasNoNewDependenciesValidatorListFiles_invalid(
    repo_for_test_pa_133_invalid: Repo,
):
    """
    Test the IsBasePackHasNoNewDependenciesValidatorListFiles validator with invalid dependencies.
    Given:
        - A test repository with a Base pack that depends on NewPack (not allowed).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorListFiles validator on the Base pack.

    Then:
        - The validator should return a result indicating that the Base pack
          has an unexpected dependency on NewPack.
    """
    graph_interface = repo_for_test_pa_133_invalid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_133_invalid.packs[0]]
        )
    )
    assert len(results) == 1
    assert "NewPack" in results[0].message
    assert "unexpected dependencies" in results[0].message


def test_IsBasePackHasNoNewDependenciesValidatorListFiles_non_base_pack(
    repo_for_test_pa_133_invalid: Repo,
):
    """
    Test the IsBasePackHasNoNewDependenciesValidatorListFiles validator on a non-Base pack.
    Given:
        - A test repository with a Base pack and a NewPack.

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorListFiles validator on NewPack (not Base).

    Then:
        - The validator should not return any results (only checks the Base pack).
    """
    graph_interface = repo_for_test_pa_133_invalid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_133_invalid.packs[1]]
        )
    )
    assert not results


@pytest.fixture
def repo_for_test_pa_133_test_dependency(graph_repo: Repo):
    """
    Creates a test repository with a Base pack that has only test dependencies
    to packs outside the allowed list. This should NOT trigger PA133 because
    test dependencies should be excluded.

    The Base pack has:
    - An integration with a test playbook that uses a command from TestOnlyPack.
    - Only allowed dependencies (Core) in pack_metadata.
    """
    test_playbook_using_testonly_command = {
        "id": "BaseTestPlaybook",
        "name": "BaseTestPlaybook",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "TestOnlyIntegration|||test-only-command",
                    "brand": "TestOnlyIntegration",
                    "iscommand": "true",
                },
            }
        },
    }
    # Base pack with an integration and a test playbook
    base_pack = graph_repo.create_pack("Base")
    base_integration = base_pack.create_integration("BaseIntegration")
    base_integration.set_commands(["base-command"])
    base_integration.yml.update({"tests": ["BaseTestPlaybook"]})
    base_pack.create_test_playbook(
        "BaseTestPlaybook", yml=test_playbook_using_testonly_command
    )
    base_pack.pack_metadata.update({"dependencies": {"Core": {"mandatory": True}}})

    # Core pack (allowed dependency)
    core_pack = graph_repo.create_pack("Core")
    core_integration = core_pack.create_integration("CoreIntegration")
    core_integration.set_commands(["core-command"])

    # TestOnlyPack - only used by test playbooks, not by production content
    test_only_pack = graph_repo.create_pack("TestOnlyPack")
    test_only_integration = test_only_pack.create_integration("TestOnlyIntegration")
    test_only_integration.set_commands(["test-only-command"])

    return graph_repo


def test_IsBasePackHasNoNewDependenciesValidatorAllFiles_test_dependency_excluded(
    repo_for_test_pa_133_test_dependency: Repo,
):
    """
    Test that PA133 does not flag test-only dependencies.
    Given:
        - A Base pack with an allowed dependency (Core).
        - A test playbook in Base that uses a command from TestOnlyPack.
        - TestOnlyPack is NOT in the allowed dependencies list.

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorAllFiles validator.

    Then:
        - The validator should NOT return any results because the dependency
          on TestOnlyPack is a test-only dependency (is_test=True) and should
          be excluded from the check.
    """
    graph_interface = repo_for_test_pa_133_test_dependency.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorAllFiles().obtain_invalid_content_items(
            []
        )
    )
    assert not results


def test_IsBasePackHasNoNewDependenciesValidatorListFiles_test_dependency_excluded(
    repo_for_test_pa_133_test_dependency: Repo,
):
    """
    Test that PA133 does not flag test-only dependencies when checking specific packs.
    Given:
        - A Base pack with an allowed dependency (Core).
        - A test playbook in Base that uses a command from TestOnlyPack.
        - TestOnlyPack is NOT in the allowed dependencies list.

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorListFiles validator on the Base pack.

    Then:
        - The validator should NOT return any results because the dependency
          on TestOnlyPack is a test-only dependency (is_test=True) and should
          be excluded from the check.
    """
    graph_interface = repo_for_test_pa_133_test_dependency.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_133_test_dependency.packs[0]]
        )
    )
    assert not results


@pytest.fixture
def repo_for_test_pa_133_mixed_dependencies(graph_repo: Repo):
    """
    Creates a test repository with a Base pack that has BOTH a test dependency
    (which should be excluded) AND a real non-allowed dependency (which should
    still be flagged).

    The Base pack has:
    - A playbook that uses a command from RealDepPack (non-test, non-allowed dependency).
    - A test playbook that uses a command from TestOnlyPack (test-only dependency).
    - Only allowed dependencies (Core) in pack_metadata.
    """
    playbook_using_realdep_command = {
        "id": "BasePlaybook",
        "name": "BasePlaybook",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "RealDepIntegration|||real-dep-command",
                    "brand": "RealDepIntegration",
                    "iscommand": "true",
                },
            }
        },
    }
    test_playbook_using_testonly_command = {
        "id": "BaseTestPlaybook",
        "name": "BaseTestPlaybook",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "TestOnlyIntegration|||test-only-command",
                    "brand": "TestOnlyIntegration",
                    "iscommand": "true",
                },
            }
        },
    }
    # Base pack with a playbook (real dep) and a test playbook (test dep)
    base_pack = graph_repo.create_pack("Base")
    base_integration = base_pack.create_integration("BaseIntegration")
    base_integration.set_commands(["base-command"])
    base_integration.yml.update({"tests": ["BaseTestPlaybook"]})
    base_pack.create_playbook("BasePlaybook", yml=playbook_using_realdep_command)
    base_pack.create_test_playbook(
        "BaseTestPlaybook", yml=test_playbook_using_testonly_command
    )
    base_pack.pack_metadata.update(
        {"dependencies": {"RealDepPack": {"mandatory": True}}}
    )

    # Core pack (allowed dependency)
    core_pack = graph_repo.create_pack("Core")
    core_integration = core_pack.create_integration("CoreIntegration")
    core_integration.set_commands(["core-command"])

    # RealDepPack - used by a real playbook (non-test), should be flagged
    real_dep_pack = graph_repo.create_pack("RealDepPack")
    real_dep_integration = real_dep_pack.create_integration("RealDepIntegration")
    real_dep_integration.set_commands(["real-dep-command"])

    # TestOnlyPack - only used by test playbooks, should NOT be flagged
    test_only_pack = graph_repo.create_pack("TestOnlyPack")
    test_only_integration = test_only_pack.create_integration("TestOnlyIntegration")
    test_only_integration.set_commands(["test-only-command"])

    return graph_repo


def test_IsBasePackHasNoNewDependenciesValidatorAllFiles_mixed_deps_flags_only_real(
    repo_for_test_pa_133_mixed_dependencies: Repo,
):
    """
    Test that PA133 flags real dependencies but excludes test-only dependencies.
    Given:
        - A Base pack with:
            - A playbook using a command from RealDepPack (real, non-allowed dependency).
            - A test playbook using a command from TestOnlyPack (test-only dependency).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorAllFiles validator.

    Then:
        - The validator should return exactly 1 result flagging RealDepPack.
        - TestOnlyPack should NOT appear in the results.
    """
    graph_interface = repo_for_test_pa_133_mixed_dependencies.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorAllFiles().obtain_invalid_content_items(
            []
        )
    )
    assert len(results) == 1
    assert "RealDepPack" in results[0].message
    assert "TestOnlyPack" not in results[0].message


def test_IsBasePackHasNoNewDependenciesValidatorListFiles_mixed_deps_flags_only_real(
    repo_for_test_pa_133_mixed_dependencies: Repo,
):
    """
    Test that PA133 flags real dependencies but excludes test-only dependencies when checking specific packs.
    Given:
        - A Base pack with:
            - A playbook using a command from RealDepPack (real, non-allowed dependency).
            - A test playbook using a command from TestOnlyPack (test-only dependency).

    When:
        - Running the IsBasePackHasNoNewDependenciesValidatorListFiles validator on the Base pack.

    Then:
        - The validator should return exactly 1 result flagging RealDepPack.
        - TestOnlyPack should NOT appear in the results.
    """
    graph_interface = repo_for_test_pa_133_mixed_dependencies.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsBasePackHasNoNewDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_pa_133_mixed_dependencies.packs[0]]
        )
    )
    assert len(results) == 1
    assert "RealDepPack" in results[0].message
    assert "TestOnlyPack" not in results[0].message


# ---------------------------------------------------------------------------
# PA134 – PackSupportedModulesCoverageValidator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pack_marketplaces, pack_supported_modules, integration_marketplaces, integration_supported_modules, expected_failures",
    [
        pytest.param(
            ["xsoar"],
            ["edr", "xsiam"],
            None,
            None,
            0,
            id="non_platform_pack_no_validation",
        ),
        pytest.param(
            ["platform"],
            ["edr", "xsiam"],
            [MarketplaceVersions.PLATFORM],
            ["edr", "xsiam"],
            0,
            id="all_modules_covered_by_single_item",
        ),
        pytest.param(
            ["platform"],
            ["edr"],
            [MarketplaceVersions.PLATFORM],
            ["edr"],
            0,
            id="single_module_covered",
        ),
        pytest.param(
            ["platform"],
            ["edr", "xsiam"],
            None,
            None,
            1,
            id="no_content_items_all_modules_uncovered",
        ),
        pytest.param(
            ["platform"],
            ["edr", "xsiam", "asm"],
            [MarketplaceVersions.PLATFORM],
            ["edr", "xsiam"],
            1,
            id="one_module_uncovered",
        ),
        pytest.param(
            ["platform"],
            ["edr"],
            [MarketplaceVersions.XSOAR],
            ["edr"],
            1,
            id="content_item_not_in_platform_marketplace",
        ),
    ],
)
def test_PackSupportedModulesCoverageValidator_obtain_invalid_content_items(
    pack_marketplaces,
    pack_supported_modules,
    integration_marketplaces,
    integration_supported_modules,
    expected_failures,
):
    """
    Given
    content_items.
        - Case 1: A pack not in the platform marketplace with supportedModules declared.
        - Case 2: A platform pack with supportedModules ["edr", "xsiam"] and a content item covering both.
        - Case 3: A platform pack with supportedModules ["edr"] and a content item covering it.
        - Case 4: A platform pack with supportedModules ["edr", "xsiam"] and no content items.
        - Case 5: A platform pack with supportedModules ["edr", "xsiam", "asm"] and a content item covering only "edr" and "xsiam".
        - Case 6: A platform pack with supportedModules ["edr"] and a content item only in xsoar marketplace.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - Make sure the right amount of pack metadatas failed.
        - Case 1: Shouldn't fail (non-platform pack).
        - Case 2: Shouldn't fail (all modules covered).
        - Case 3: Shouldn't fail (module covered).
        - Case 4: Should fail (no content items to cover modules).
        - Case 5: Should fail (asm not covered).
        - Case 6: Should fail (content item not in platform marketplace).
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[pack_marketplaces, pack_supported_modules],
    )

    if integration_marketplaces is not None:
        integration = create_integration_object()
        integration.marketplaces = integration_marketplaces
        integration.supportedModules = integration_supported_modules
        pack.content_items.integration.append(integration)

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == expected_failures


def test_PackSupportedModulesCoverageValidator_uncovered_module_in_message():
    """
    Given
        - A platform pack declaring supportedModules ["xsiam", "edr", "asm"].
        - No content items covering any module.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - The error message lists the uncovered modules in sorted order.
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["xsiam", "edr", "asm"]],
    )

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == 1
    assert "asm, edr, xsiam" in results[0].message


def test_PackSupportedModulesCoverageValidator_multiple_items_cover_all_modules():
    """
    Given
        - A platform pack declaring supportedModules ["edr", "xsiam"].
        - Two content items, each covering one of the modules.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - No validation results are returned (all modules are covered across items).
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam"]],
    )
    integration1 = create_integration_object()
    integration1.marketplaces = [MarketplaceVersions.PLATFORM]
    integration1.supportedModules = ["edr"]

    integration2 = create_integration_object()
    integration2.marketplaces = [MarketplaceVersions.PLATFORM]
    integration2.supportedModules = ["xsiam"]

    pack.content_items.integration.extend([integration1, integration2])

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == 0


def test_PackSupportedModulesCoverageValidator_content_item_inherits_pack_modules():
    """
    Given
        - A platform pack declaring supportedModules ["edr", "xsiam"].
        - A content item with no explicit supportedModules (None), which should
          inherit the pack's modules via get_content_item_supported_modules.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - No validation results are returned because the content item inherits
          the pack's modules, covering all declared modules.
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam"]],
    )
    integration = create_integration_object()
    integration.marketplaces = [MarketplaceVersions.PLATFORM]
    integration.supportedModules = None
    integration.pack = pack
    pack.content_items.integration.append(integration)

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == 0


def test_PackSupportedModulesCoverageValidator_skips_test_playbook():
    """
    Given
        - A platform pack declaring supportedModules ["edr"].
        - A test playbook (excluded from upload) that covers "edr".
        - No other uploadable content items.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - One validation result is returned because test playbooks are excluded
          from upload and should not count toward module coverage.
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr"]],
    )
    test_pb = create_test_playbook_object()
    test_pb.marketplaces = [MarketplaceVersions.PLATFORM]
    test_pb.supportedModules = ["edr"]
    pack.content_items.test_playbook.append(test_pb)

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack]
    )
    assert len(results) == 1
    assert "edr" in results[0].message


def test_PackSupportedModulesCoverageValidator_multiple_packs_mixed_results():
    """
    Given
        - Two platform packs:
          - Pack 1: declares ["edr", "xsiam"], has a content item covering both → valid.
          - Pack 2: declares ["edr", "asm"], has a content item covering only "edr" → invalid.

    When
        - Calling the PackSupportedModulesCoverageValidator obtain_invalid_content_items function.

    Then
        - Exactly one validation result is returned (for Pack 2), mentioning "asm".
    """
    pack1 = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam"]],
    )
    integration1 = create_integration_object()
    integration1.marketplaces = [MarketplaceVersions.PLATFORM]
    integration1.supportedModules = ["edr", "xsiam"]
    pack1.content_items.integration.append(integration1)

    pack2 = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "asm"]],
    )
    integration2 = create_integration_object()
    integration2.marketplaces = [MarketplaceVersions.PLATFORM]
    integration2.supportedModules = ["edr"]
    pack2.content_items.integration.append(integration2)

    results = PackSupportedModulesCoverageValidator().obtain_invalid_content_items(
        [pack1, pack2]
    )
    assert len(results) == 1
    assert "asm" in results[0].message


def test_PackSupportedModulesCoverageValidator_fix_removes_uncovered_modules():
    """
    Given
        - A platform pack declaring supportedModules ["edr", "xsiam", "asm"].
        - Content items covering only "edr" and "xsiam" (not "asm").

    When
        - Calling obtain_invalid_content_items followed by fix.

    Then
        - The fix removes "asm" from the pack's supportedModules.
        - The fix message mentions the removed module.
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam", "asm"]],
    )
    integration = create_integration_object()
    integration.marketplaces = [MarketplaceVersions.PLATFORM]
    integration.supportedModules = ["edr", "xsiam"]
    pack.content_items.integration.append(integration)

    validator = PackSupportedModulesCoverageValidator()
    results = validator.obtain_invalid_content_items([pack])
    assert len(results) == 1

    fix_result = validator.fix(pack)
    assert "asm" in fix_result.message
    assert set(pack.supportedModules) == {"edr", "xsiam"}


def test_PackSupportedModulesCoverageValidator_fix_removes_all_uncovered_modules():
    """
    Given
        - A platform pack declaring supportedModules ["edr", "xsiam"].
        - No content items covering any module.

    When
        - Calling obtain_invalid_content_items followed by fix.

    Then
        - The fix removes all modules from the pack's supportedModules.
        - The fix message mentions both removed modules.
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam"]],
    )

    validator = PackSupportedModulesCoverageValidator()
    results = validator.obtain_invalid_content_items([pack])
    assert len(results) == 1

    fix_result = validator.fix(pack)
    assert "edr" in fix_result.message
    assert "xsiam" in fix_result.message
    assert pack.supportedModules == []


def test_PackSupportedModulesCoverageValidator_fix_preserves_covered_modules():
    """
    Given
        - A platform pack declaring supportedModules ["edr", "xsiam", "asm", "tim"].
        - Content items covering "edr" and "tim" but NOT "xsiam" or "asm".

    When
        - Calling obtain_invalid_content_items followed by fix.

    Then
        - The fix removes only "xsiam" and "asm", preserving "edr" and "tim".
    """
    pack = create_pack_object(
        paths=["marketplaces", "supportedModules"],
        values=[["platform"], ["edr", "xsiam", "asm", "tim"]],
    )
    integration1 = create_integration_object()
    integration1.marketplaces = [MarketplaceVersions.PLATFORM]
    integration1.supportedModules = ["edr"]

    integration2 = create_integration_object()
    integration2.marketplaces = [MarketplaceVersions.PLATFORM]
    integration2.supportedModules = ["tim"]

    pack.content_items.integration.extend([integration1, integration2])

    validator = PackSupportedModulesCoverageValidator()
    results = validator.obtain_invalid_content_items([pack])
    assert len(results) == 1

    fix_result = validator.fix(pack)
    assert "asm" in fix_result.message
    assert "xsiam" in fix_result.message
    assert set(pack.supportedModules) == {"edr", "tim"}


def test_PackSupportedModulesCoverageValidator_fix_creates_supported_modules_when_absent():
    """
    Given
        - A platform pack with NO supportedModules field (None), which implicitly
          means all default platform modules are supported.
        - A content item covering only "xsiam".

    When
        - Calling obtain_invalid_content_items followed by fix.

    Then
        - The fix creates the supportedModules field with only the covered module ("xsiam").
        - The fix message mentions the uncovered modules.
    """
    pack = create_pack_object(
        paths=["marketplaces"],
        values=[["platform"]],
    )
    pack.supportedModules = None

    integration = create_integration_object()
    integration.marketplaces = [MarketplaceVersions.PLATFORM]
    integration.supportedModules = ["xsiam"]
    pack.content_items.integration.append(integration)

    validator = PackSupportedModulesCoverageValidator()
    results = validator.obtain_invalid_content_items([pack])
    assert len(results) == 1

    fix_result = validator.fix(pack)
    assert pack.supportedModules == ["xsiam"]
    # All other default modules should be mentioned as removed
    assert "edr" in fix_result.message
    assert "asm" in fix_result.message


# ---------------------------------------------------------------------------
# PA135 – PackLevelIgnoreAddedValidator
# ---------------------------------------------------------------------------


def _make_pack_with_ignores(mocker, new_codes, old_codes, has_old=True):
    """Build a pack whose current/old [pack] codes are mocked.

    `pack_level_ignored_errors` (current, a cached_property) and
    `old_pack_level_ignored_errors` (old, reads git) are patched so the test is
    deterministic and does not touch the filesystem or git. Both are patched at
    the class level because `Pack` is a Pydantic model that rejects setting
    arbitrary instance attributes.
    """
    pack = create_pack_object()
    # current [pack] codes (cached_property stored in __dict__)
    pack.__dict__["pack_level_ignored_errors"] = list(new_codes)
    # old [pack] codes (the method ignores its prev_ver arg here)
    mocker.patch.object(
        type(pack),
        "old_pack_level_ignored_errors",
        return_value=list(old_codes),
    )
    if has_old:
        old_pack = create_pack_object()
        old_pack.git_sha = "old_sha"
        pack.old_base_content_object = old_pack
    else:
        pack.old_base_content_object = None
    return pack


def test_PA135_pack_section_newly_added_fails(mocker):
    """
    Given a pack whose [pack] section is new (old had no codes),
    When PA135 runs,
    Then it fails and lists the added codes.
    """
    pack = _make_pack_with_ignores(mocker, new_codes=["BA101"], old_codes=[])
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert len(results) == 1
    assert "BA101" in results[0].message


def test_PA135_new_code_added_to_existing_section_fails(mocker):
    """
    Given a pack with an existing [pack] section that gained a new code,
    When PA135 runs,
    Then it fails listing only the newly added code.
    """
    pack = _make_pack_with_ignores(
        mocker, new_codes=["BA101", "RM104"], old_codes=["BA101"]
    )
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert len(results) == 1
    assert "RM104" in results[0].message
    assert "BA101" not in results[0].message


def test_PA135_runs_on_pack_with_no_git_status(mocker):
    """
    Given a pack-ignore-only change: the .pack-ignore maps to pack_metadata.json,
    which is itself unchanged, so the collected Pack has git_status None,
    When PA135's status gate is evaluated,
    Then PA135 still runs (it is not restricted by expected_git_statuses).

    Regression: previously PA135 declared
    expected_git_statuses=[ADDED, MODIFIED, RENAMED], so a None-status pack
    (the pack-ignore-only case) was skipped and additions went undetected.
    """
    from demisto_sdk.commands.validate.validators.base_validator import (
        should_run_according_to_status,
    )

    validator = PackLevelIgnoreAddedValidator()
    assert validator.expected_git_statuses is None
    assert should_run_according_to_status(None, validator.expected_git_statuses) is True


def test_PA135_brand_new_pack_with_pack_section_fails(mocker):
    """
    Given a brand-new pack (no old_base_content_object) shipping a [pack] section,
    When PA135 runs,
    Then it fails (all current codes count as added).
    """
    pack = _make_pack_with_ignores(
        mocker, new_codes=["BA101"], old_codes=[], has_old=False
    )
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert len(results) == 1


def test_PA135_only_removed_codes_passes(mocker):
    """
    Given a pack where codes were only removed from [pack],
    When PA135 runs,
    Then it passes (removals are allowed).
    """
    pack = _make_pack_with_ignores(
        mocker, new_codes=["BA101"], old_codes=["BA101", "RM104"]
    )
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert results == []


def test_PA135_no_pack_section_passes(mocker):
    """
    Given a pack with no [pack] section now,
    When PA135 runs,
    Then it passes.
    """
    pack = _make_pack_with_ignores(mocker, new_codes=[], old_codes=[])
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert results == []


def test_PA135_unchanged_pack_section_passes(mocker):
    """
    Given a pack whose [pack] section is unchanged,
    When PA135 runs,
    Then it passes.
    """
    pack = _make_pack_with_ignores(mocker, new_codes=["BA101"], old_codes=["BA101"])
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    assert results == []


def test_PA135_uses_old_object_git_sha_as_prev_ver(mocker):
    """
    Given a modified pack whose old_base_content_object carries the run's prev_ver,
    When PA135 computes the added codes,
    Then it reads the old [pack] codes at that exact ref.
    """
    pack = _make_pack_with_ignores(
        mocker, new_codes=["BA101", "RM104"], old_codes=["BA101"]
    )
    pack.old_base_content_object.git_sha = "origin/master"
    PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    pack.old_pack_level_ignored_errors.assert_called_once_with("origin/master")


def test_PA135_pack_ignore_only_change_uses_old_object_prev_ver(mocker):
    """
    Given a pack-ignore-only change: the pack is collected via its unchanged
    pack_metadata.json, but the initializer still builds old_base_content_object
    from prev_ver and sets its git_sha accordingly,
    When PA135 computes the added codes,
    Then it diffs against that prev_ver (origin/master) and flags the added code.

    This is the fork/pack-ignore-only regression that previously produced a
    false negative.
    """
    pack = _make_pack_with_ignores(
        mocker, new_codes=["BA101", "RM104"], old_codes=["BA101"]
    )
    pack.old_base_content_object.git_sha = "origin/master"
    results = PackLevelIgnoreAddedValidator().obtain_invalid_content_items([pack])
    pack.old_pack_level_ignored_errors.assert_called_once_with("origin/master")
    assert len(results) == 1
    assert "RM104" in results[0].message

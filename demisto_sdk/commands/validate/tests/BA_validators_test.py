import copy
from pathlib import Path
from typing import List

import pytest

from demisto_sdk.commands.common.constants import (
    PACKS_FOLDER,
    PARTNER_SUPPORT,
    XSOAR_SUPPORT,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_assets_modeling_rule_object,
    create_classifier_object,
    create_correlation_rule_object,
    create_dashboard_object,
    create_generic_definition_object,
    create_generic_field_object,
    create_generic_module_object,
    create_generic_type_object,
    create_incident_field_object,
    create_incident_type_object,
    create_incoming_mapper_object,
    create_indicator_field_object,
    create_indicator_type_object,
    create_integration_object,
    create_job_object,
    create_layout_object,
    create_list_object,
    create_modeling_rule_object,
    create_old_file_pointers,
    create_outgoing_mapper_object,
    create_pack_object,
    create_parsing_rule_object,
    create_playbook_object,
    create_ps_integration_object,
    create_report_object,
    create_script_object,
    create_trigger_object,
    create_widget_object,
    create_wizard_object,
    create_xdrc_template_object,
    create_xsiam_dashboard_object,
    create_xsiam_report_object,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA100_is_valid_version import (
    IsValidVersionValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA103_is_tests_section_valid import (
    IsTestsSectionValidValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA104_is_marketplace_tags_valid import (
    MarketplaceTagsValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA105_id_contain_slashes import (
    IDContainSlashesValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient_all_items import (
    IsFromVersionSufficientAllItemsValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient_indicator_field import (
    IsFromVersionSufficientIndicatorFieldValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient_integration import (
    IsFromVersionSufficientIntegrationValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA108_is_folder_name_has_separators import (
    IsFolderNameHasSeparatorsValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA109_file_name_has_separators import (
    FileNameHasSeparatorsValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA110_is_entity_type_in_entity_name import (
    IsEntityTypeInEntityNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA111_is_entity_name_contain_excluded_word import (
    ERROR_MSG_TEMPLATE,
    IsEntityNameContainExcludedWordValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA112_is_valid_compliant_policy_name import (
    IsValidCompliantPolicyNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA113_is_content_item_name_contain_trailing_spaces import (
    ContentTypes as ContentTypes113,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA113_is_content_item_name_contain_trailing_spaces import (
    IsContentItemNameContainTrailingSpacesValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA114_is_pack_changed import (
    PackNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA116_cli_name_should_equal_id import (
    CliNameMatchIdValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA118_from_to_version_synched import (
    FromToVersionSyncedValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA119_is_py_file_contain_copy_right_section import (
    IsPyFileContainCopyRightSectionValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA124_is_have_unit_test_file import (
    IsHaveUnitTestFileValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA125_customer_facing_docs_disallowed_terms import (
    CustomerFacingDocsDisallowedTermsValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA126_content_item_is_deprecated_correctly import (
    IsDeprecatedCorrectlyValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA127_is_valid_context_path_depth import (
    IsValidContextPathDepthValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA128_is_command_or_script_name_starts_with_digit import (
    IsCommandOrScriptNameStartsWithDigitValidator,
)
from TestSuite.repo import ChangeCWD

VALUE_WITH_TRAILING_SPACE = "field_with_space_should_fail "
FOUND_INTERNAL_TERMS_ERROR = "Found internal terms in a customer-facing documentation: found test-module in"

@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["commonfields.id"], values=["changedName"]
                ),
                create_integration_object(),
            ],
            1,
            [
                "The name attribute (currently TestIntegration) should be identical to its `id` attribute (changedName)"
            ],
        ),
        (
            [
                create_classifier_object(paths=["id"], values=["changedName"]),
                create_classifier_object(paths=["id"], values=["Github Classifier"]),
            ],
            1,
            [
                "The name attribute (currently Github Classifier) should be identical to its `id` attribute (changedName)"
            ],
        ),
        (
            [
                create_dashboard_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_incident_type_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_wizard_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_wizard_object({"id": "should_fail"}),
            ],
            1,
            [
                "The name attribute (currently test_wizard) should be identical to its `id` attribute (should_fail)"
            ],
        ),
    ],
)
def test_IDNameValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: content_items with 2 integrations where the first one has its ID altered.
        - Case 2: content_items with 2 classifiers where the first one has its ID altered.
        - Case 3: content_items with 1 Dashboard without changes.
        - Case 3: content_items with 1 IncidentType without changes.
        - Case 3: content_items with 1 Wizard without changes.
        - Case 2: content_items with 1 Wizard with its ID altered.
    When
    - Calling the IDNameValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 classifier.
        - Case 3: Should fail anything.
        - Case 4: Should fail anything.
        - Case 5: Should fail anything.
        - Case 6: Should fail the Wizard.
    """
    results = IDNameValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_name, expected_fix_msg",
    [
        (
            create_wizard_object({"id": "should_fix"}),
            "should_fix",
            "Changing name to be equal to id (should_fix).",
        ),
        (
            create_incident_type_object(["id"], ["should_fix"]),
            "should_fix",
            "Changing name to be equal to id (should_fix).",
        ),
        (
            create_integration_object(["commonfields.id"], ["should_fix"]),
            "should_fix",
            "Changing name to be equal to id (should_fix).",
        ),
    ],
)
def test_IDNameValidator_fix(content_item, expected_name, expected_fix_msg):
    """
    Given
    content_item.
        - Case 1: a Wizard content item where the id is different from name.
        - Case 2: an IncidentType content item where the id is different from name.
        - Case 3: an Integration content item where the id is different from name.
    When
    - Calling the IDNameValidator_fix fix function.
    Then
        - Make sure that the object name was changed to match the id, and that the right fix msg is returned.
    """
    assert IDNameValidator().fix(content_item).message == expected_fix_msg
    assert content_item.name == expected_name


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_indicator_field_object(), create_incident_field_object()], 0, []),
        (
            [
                create_indicator_field_object(
                    paths=["cliName"], values=["changed_cliName"]
                ),
            ],
            1,
            [
                "The cli name changed_cliName doesn't match the standards. the cliName should be: email."
            ],
        ),
    ],
)
def test_CliNameMatchIdValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: content_items with 1 indicator field and 1 incident field.
        - Case 2: content_items with 1 indicator field, where the cliName is different from id.

    When
    - Calling the CliNameMatchIdValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail the indicator field.
    """
    results = CliNameMatchIdValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_name, expected_fix_msg",
    [
        (
            create_indicator_field_object(
                paths=["cliName"], values=["changed_cliName"]
            ),
            "email",
            "Changing the cli name to (email).",
        ),
        (
            create_incident_field_object(paths=["id"], values=["incident_domain"]),
            "domain",
            "Changing the cli name to (domain).",
        ),
    ],
)
def test_CliNameMatchIdValidator_fix(content_item, expected_name, expected_fix_msg):
    """
    Given
    content_item.
        - Case 1: a IndicatorField with the cliName modified.
        - Case 2: a IncidentField with the id modified.
    When
    - Calling the CliNameMatchIdValidator fix function.
    Then
        - Make sure that the object cli name was changed to match the id, and that the right fix msg is returned.
    """
    assert CliNameMatchIdValidator().fix(content_item).message == expected_fix_msg
    assert content_item.cli_name == expected_name


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_incident_field_object(),
                create_widget_object(),
                create_wizard_object(),
                create_report_object(),
                create_xsiam_report_object(),
                create_script_object(),
                create_dashboard_object(),
                create_incident_type_object(),
                create_generic_module_object(),
                create_generic_type_object(),
                create_incoming_mapper_object(),
                create_outgoing_mapper_object(),
                create_generic_definition_object(),
                create_classifier_object(),
                create_xsiam_dashboard_object(),
                create_job_object(),
                create_list_object(),
                create_parsing_rule_object(),
                create_playbook_object(),
                create_generic_field_object(),
                create_correlation_rule_object(),
                create_assets_modeling_rule_object(),
                create_layout_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_incident_field_object(["fromVersion"], ["4.5.0"]),
                create_wizard_object({"fromVersion": "4.5.0"}),
                create_playbook_object(["fromversion"], ["4.5.0"]),
                create_generic_field_object(["fromVersion"], ["4.5.0"]),
            ],
            4,
            [
                "The IncidentField from version field is either missing or insufficient, need at least 5.0.0, current is 4.5.0.",
                "The Wizard from version field is either missing or insufficient, need at least 6.8.0, current is 4.5.0.",
                "The Playbook from version field is either missing or insufficient, need at least 5.0.0, current is 4.5.0.",
                "The GenericField from version field is either missing or insufficient, need at least 6.5.0, current is 4.5.0.",
            ],
        ),
    ],
)
def test_IsFromVersionSufficientAllItemsValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: a list of content items with 1 item of each kind supported by the validation where the fromVersion field is valid.
        - Case 2: IncidentField, wizard, playbook, and genericField, all set to fromVersion = 4.5.0 (insufficient).
    When
    - Calling the IsFromVersionSufficientAllItemsValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = IsFromVersionSufficientAllItemsValidator().obtain_invalid_content_items(
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
    "content_items, expected_msgs, expected_new_from_versions",
    [
        (
            [
                create_incident_field_object(["fromVersion"], ["4.5.0"]),
                create_wizard_object({"fromVersion": "4.5.0"}),
                create_playbook_object(["fromversion"], ["4.5.0"]),
                create_generic_field_object(["fromVersion"], ["4.5.0"]),
            ],
            [
                "Raised the fromversion field to 5.0.0",
                "Raised the fromversion field to 6.8.0",
                "Raised the fromversion field to 5.0.0",
                "Raised the fromversion field to 6.5.0",
            ],
            ["5.0.0", "6.8.0", "5.0.0", "6.5.0"],
        ),
    ],
)
def test_IsFromVersionSufficientAllItemsValidator_fix(
    content_items, expected_msgs, expected_new_from_versions
):
    """
    Given
    content_items list.
        - Case 1: IncidentField, wizard, playbook, and genericField, all set to fromVersion = 4.5.0 (insufficient).
    When
    - Calling the IsFromVersionSufficientAllItemsValidator fix function.
    Then
        - Make sure the contentitem from version was set to the right version and the right message was returned.
    """
    for content_item, expected_msg, expected_new_from_version in zip(
        content_items, expected_msgs, expected_new_from_versions
    ):
        assert content_item.fromversion == "4.5.0"
        result = IsFromVersionSufficientAllItemsValidator().fix(content_item)
        assert result.message == expected_msg
        assert content_item.fromversion == expected_new_from_version


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_indicator_field_object(),
                create_incident_field_object(),
                create_widget_object(),
                create_wizard_object(),
                create_report_object(),
                create_xsiam_report_object(),
                create_integration_object(),
                create_script_object(),
                create_dashboard_object(),
                create_incident_type_object(),
                create_generic_module_object(),
                create_generic_type_object(),
                create_incoming_mapper_object(),
                create_outgoing_mapper_object(),
                create_generic_definition_object(),
                create_classifier_object(),
                create_xsiam_dashboard_object(),
                create_job_object(),
                create_list_object(),
                create_parsing_rule_object(),
                create_playbook_object(),
                create_generic_field_object(),
                create_correlation_rule_object(),
                create_assets_modeling_rule_object(),
                create_layout_object(),
            ],
            0,
            [],
        ),
    ],
)
def test_FromToVersionSyncedValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: a list of content items with 1 item of each kind supported by the validation where the fromVersion < toVersion / toVersion field doesn't exist.
        - Case 2: IncidentType with the fromVersion = toVersion = 5.0.0, IncidentField, Widget, and Wizard, all set to toVersion = 4.5.0 < fromVersion (insufficient).
    When
    - Calling the FromToVersionSyncedValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = FromToVersionSyncedValidator().obtain_invalid_content_items(content_items)
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
        (
            [
                create_indicator_field_object(
                    ["type", "fromVersion"], ["html", "6.1.0"]
                ),
                create_indicator_field_object(
                    ["type", "fromVersion"], ["grid", "5.5.0"]
                ),
                create_indicator_field_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_indicator_field_object(
                    ["type", "fromVersion"], ["html", "6.0.0"]
                ),
                create_indicator_field_object(
                    ["type", "fromVersion"], ["grid", "5.0.0"]
                ),
            ],
            2,
            [
                "The fromversion of IndicatorField with type html must be at least 6.1.0, current is 6.0.0.",
                "The fromversion of IndicatorField with type grid must be at least 5.5.0, current is 5.0.0.",
            ],
        ),
        (
            [
                create_indicator_field_object(
                    ["type", "fromVersion"], ["html", "6.1.0"]
                ),
                create_indicator_field_object(
                    ["type", "fromVersion"], ["grid", "5.5.0"]
                ),
                create_indicator_field_object(
                    ["type", "fromVersion"], ["html", "6.0.0"]
                ),
                create_indicator_field_object(
                    ["type", "fromVersion"], ["grid", "5.0.0"]
                ),
                create_indicator_field_object(),
            ],
            2,
            [
                "The fromversion of IndicatorField with type html must be at least 6.1.0, current is 6.0.0.",
                "The fromversion of IndicatorField with type grid must be at least 5.5.0, current is 5.0.0.",
            ],
        ),
        (
            [
                create_indicator_field_object(["fromVersion"], ["4.5.0"]),
            ],
            1,
            [
                "The fromversion of IndicatorField with type shortText must be at least 5.0.0, current is 4.5.0.",
            ],
        ),
    ],
)
def test_IsFromVersionSufficientIndicatorFieldValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: Three indicator fields:
            - one with html type and fromVersion = 6.1.0.
            - one with grid type and fromVersion = 5.5.0.
            - one with shortText type and fromVersion = 5.0.0.
        - Case 2: Two indicator fields:
            - one with html type and fromVersion = 6.0.0.
            - one with grid type and fromVersion = 5.0.0.
        - Case 3: Five indicator fields:
            - one with html type and fromVersion = 6.1.0.
            - one with grid type and fromVersion = 5.5.0.
            - one with html type and fromVersion = 6.0.0.
            - one with grid type and fromVersion = 5.0.0.
            - one with shortText type and fromVersion = 5.0.0.
        - Case 4: One indicator field:
            - one with shortText type and fromVersion = 4.5.0.
    When
    - Calling the IsFromVersionSufficientIndicatorFieldValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of content_items failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any indicator field.
        - Case 2: Should fail the two indicator fields.
        - Case 3: Should fail the third and fourth indicator fields.
        - Case 4: Should fail the indicator field.
    """
    results = (
        IsFromVersionSufficientIndicatorFieldValidator().obtain_invalid_content_items(
            content_items
        )
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "indicator_field, current_version, expected_msg, expected_fixed_version",
    [
        (
            create_indicator_field_object(["type", "fromVersion"], ["html", "6.0.0"]),
            "6.0.0",
            "Raised the fromversion field to 6.1.0",
            "6.1.0",
        ),
        (
            create_indicator_field_object(["type", "fromVersion"], ["grid", "5.0.0"]),
            "5.0.0",
            "Raised the fromversion field to 5.5.0",
            "5.5.0",
        ),
        (
            create_indicator_field_object(paths=["fromVersion"], values=["4.5.0"]),
            "4.5.0",
            "Raised the fromversion field to 5.0.0",
            "5.0.0",
        ),
    ],
)
def test_IsFromVersionSufficientIndicatorFieldValidator_fix(
    indicator_field, current_version, expected_msg, expected_fixed_version
):
    """
    Given
        - an IndicatorField.
        html type and fromVersion = 6.1.0.
            - one with grid type
        - Case 1: an Indicator field with type = html and fromversion = 6.0.0.
        - Case 2: an Indicator field with type = grid and fromversion = 5.0.0.
        - Case 3: an Indicator field with type = shortText and fromversion = 4.5.0.
    When
    - Calling the IsFromVersionSufficientIndicatorFieldValidator fix function.
    Then
        - Make sure that the integration fromversion was raised and that the right message was returned.
        - Case 1: Should raise the version to 6.1.0.
        - Case 2: Should raise the version to 5.5.0.
        - Case 3: Should raise the version to 5.0.0.
    """
    assert indicator_field.fromversion == current_version
    assert (
        IsFromVersionSufficientIndicatorFieldValidator().fix(indicator_field).message
        == expected_msg
    )
    assert indicator_field.fromversion == expected_fixed_version


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "5.5.0"],
                ),
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[False, "5.0.0"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "6.0.0"],
                ),
                create_integration_object(
                    paths=[
                        "script.feed",
                        "fromversion",
                    ],
                    values=[True, "5.0.0"],
                ),
            ],
            1,
            [
                "The integration is a feed integration and therefore require a fromversion field of at least 5.5.0, current version is: 5.0.0."
            ],
        ),
        (
            [
                create_ps_integration_object(
                    paths=["fromversion"],
                    values=["5.5.0"],
                ),
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["5.0.0"],
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["6.0.0"],
                ),
                create_ps_integration_object(
                    paths=["fromversion"],
                    values=["5.0.0"],
                ),
            ],
            1,
            [
                "The integration is a powershell integration and therefore require a fromversion field of at least 5.5.0, current version is: 5.0.0."
            ],
        ),
        (
            [
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["4.5.0"],
                ),
                create_integration_object(
                    paths=[
                        "fromversion",
                    ],
                    values=["5.0.0"],
                ),
            ],
            1,
            [
                "The integration is a regular integration and therefore require a fromversion field of at least 5.0.0, current version is: 4.5.0."
            ],
        ),
    ],
)
def test_IsFromVersionSufficientIntegrationValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: 2 integrations - one feed integration with high enough fromversion field and one none feed integration with fromversion lower than 5.5.0.
        - Case 2: 2 integration - one feed integration with fromversion lower than 5.5.0 and one with a high enough fromversion field.
        - Case 3: 2 integrations - one ps integration with high enough fromversion field and one python integration with fromversion lower than 5.5.0.
        - Case 4: 2 integration - one ps integration with fromversion lower than 5.5.0 and one with a high enough fromversion field.
        - Case 5: 2 regular integrations - one with fromversion lower than 5.0.0 and one with fromversion = 5.0.0
    When
    - Calling the IsFromVersionSufficientIntegrationValidator is valid function.
    Then
        - Make sure the validation fail when it needs to and the right error message is returned.
        - Case 1: Shouldn't fail at all.
        - Case 2: Should fail only one integration.
        - Case 3: Shouldn't fail at all.
        - Case 4: Should fail only one integration.
        - Case 5: Should fail only one integration.
    """
    results = (
        IsFromVersionSufficientIntegrationValidator().obtain_invalid_content_items(
            content_items
        )
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "integration, current_version, expected_msg, expected_fixed_version",
    [
        (
            create_ps_integration_object(paths=["fromversion"], values=["5.0.0"]),
            "5.0.0",
            "Raised the fromversion field to 5.5.0",
            "5.5.0",
        ),
        (
            create_integration_object(
                paths=["fromversion", "script.feed"], values=["5.0.0", True]
            ),
            "5.0.0",
            "Raised the fromversion field to 5.5.0",
            "5.5.0",
        ),
        (
            create_integration_object(paths=["fromversion"], values=["4.5.0"]),
            "4.5.0",
            "Raised the fromversion field to 5.0.0",
            "5.0.0",
        ),
    ],
)
def test_IsFromVersionSufficientIntegrationValidator_fix(
    integration, current_version, expected_msg, expected_fixed_version
):
    """
    Given
        - an integration.
        - Case 1: a ps integration with fromversion = 5.0.0.
        - Case 2: a feed integration with fromversion = 5.0.0.
        - Case 3: a regular integration with fromversion = 4.5.0.
    When
    - Calling the IsFromVersionSufficientIntegrationValidator fix function.
    Then
        - Make sure that the integration fromversion was raised and that the right message was returned.
        - Case 1: Should raise the version to 5.5.0.
        - Case 2: Should raise the version to 5.5.0.
        - Case 3: Should raise the version to 5.0.0.
    """
    assert integration.fromversion == current_version
    assert (
        IsFromVersionSufficientIntegrationValidator().fix(integration).message
        == expected_msg
    )
    assert integration.fromversion == expected_fixed_version


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_indicator_field_object(),
                create_incident_field_object(),
                create_widget_object(),
                create_wizard_object(),
                create_report_object(),
                create_xsiam_report_object(),
                create_integration_object(),
                create_script_object(),
                create_dashboard_object(),
                create_incident_type_object(),
                create_generic_module_object(),
                create_generic_type_object(),
                create_incoming_mapper_object(),
                create_outgoing_mapper_object(),
                create_generic_definition_object(),
                create_classifier_object(),
                create_xsiam_dashboard_object(),
                create_job_object(),
                create_list_object(),
                create_parsing_rule_object(),
                create_playbook_object(),
                create_generic_field_object(),
                create_correlation_rule_object(),
                create_assets_modeling_rule_object(),
                create_layout_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_incident_type_object(["id"], ["Tra/ps"]),
                create_incident_field_object(["id"], ["incide/nt_cv/e"]),
                create_list_object(["id"], ["checked integrations/"]),
                create_integration_object(["commonfields.id"], ["TestIntegrati/on"]),
            ],
            4,
            [
                "The IncidentType ID field (Tra/ps) include a slash (/), make sure to remove it.",
                "The IncidentField ID field (tcv/e) include a slash (/), make sure to remove it.",
                "The List ID field (checked integrations/) include a slash (/), make sure to remove it.",
                "The Integration ID field (TestIntegrati/on) include a slash (/), make sure to remove it.",
            ],
        ),
    ],
)
def test_IDContainSlashesValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: A list of one of each content_item supported by the validation with a valid ID.
        - Case 2: A list of one IncidentType, IncidentField, List, and Integration, all with invalid ids with at least one /.
    When
    - Calling the IDContainSlashesValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = IDContainSlashesValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, current_id, expected_fix_msg, expected_id",
    [
        (
            create_incident_type_object(["id"], ["Tra/ps"]),
            "Tra/ps",
            "Removed slashes (/) from ID, new ID is Traps.",
            "Traps",
        ),
        (
            create_incident_field_object(["id"], ["incident_c/v/e"]),
            "c/v/e",
            "Removed slashes (/) from ID, new ID is cve.",
            "cve",
        ),
        (
            create_list_object(["id"], ["checked integrations/"]),
            "checked integrations/",
            "Removed slashes (/) from ID, new ID is checked integrations.",
            "checked integrations",
        ),
        (
            create_integration_object(["commonfields.id"], ["TestIntegrati///on"]),
            "TestIntegrati///on",
            "Removed slashes (/) from ID, new ID is TestIntegration.",
            "TestIntegration",
        ),
    ],
)
def test_IDContainSlashesValidator_fix(
    content_item, current_id, expected_fix_msg, expected_id
):
    """
    Given
    content_item.
        - Case 1: An incident type with ID that contain slashes.
        - Case 2: An incident field with ID that contain slashes.
        - Case 3: A list with ID that contain slashes.
        - Case 4: An integration with ID that contain slashes.
    When
    - Calling the IDContainSlashesValidator fix function.
    Then
        - Make sure that all the slashes were removed, the right field was set with the fixed value and the right message was printed out.
    """
    assert content_item.object_id == current_id
    assert IDContainSlashesValidator().fix(content_item).message == expected_fix_msg
    assert content_item.object_id == expected_id


def test_IsDeprecatedCorrectlyValidator_obtain_invalid_content_items():
    """
    Given:
     - 1 integration and 1 script which are deprecated incorrectly
     - 1 integration and 1 script which are deprecated correctly
     - 1 integration and 1 script which are not deprecated

    When:
     - Running the IsDeprecatedCorrectlyValidator validator

    Then:
     - make sure the script and integration which are deprecated incorrectly fails the validation

    """
    content_items = [
        create_integration_object(
            paths=["deprecated", "description"], values=[True, "Some description"]
        ),
        create_script_object(
            paths=["deprecated", "comment"], values=[True, "Some description"]
        ),
        create_integration_object(
            paths=["deprecated", "description"],
            values=[True, "Deprecated. Use OtherIntegrationName instead."],
        ),
        create_script_object(
            paths=["deprecated", "comment"],
            values=[True, "Deprecated. No available replacement."],
        ),
        create_integration_object(paths=["description"], values=["Some description"]),
        create_script_object(paths=["comment"], values=["Some description"]),
    ]

    results = IsDeprecatedCorrectlyValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == 2
    for result in results:
        assert result.content_object.deprecated
        assert result.content_object.description == "Some description"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_indicator_field_object(),
                create_incident_field_object(),
                create_widget_object(),
                create_wizard_object(dict_to_update={"version": -1}),
                create_integration_object(),
                create_script_object(),
                create_dashboard_object(),
                create_incident_type_object(),
                create_generic_module_object(),
                create_generic_type_object(),
                create_incoming_mapper_object(),
                create_outgoing_mapper_object(),
                create_generic_definition_object(),
                create_classifier_object(),
                create_list_object(["version"], [-1]),
                create_playbook_object(),
                create_generic_field_object(),
                create_layout_object(),
            ],
            0,
            [],
        ),
        (
            [
                create_incident_field_object(["version"], [-2]),
                create_list_object(["version"], [1]),
                create_integration_object(["commonfields.version"], [0]),
            ],
            3,
            [
                "The version for our files should always be -1, please update the file.",
                "The version for our files should always be -1, please update the file.",
                "The version for our files should always be -1, please update the file.",
            ],
        ),
    ],
)
def test_IsValidVersionValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: A list of one of each content_item supported by the validation with a valid ID.
        - Case 2: A list of one IncidentField, List, and Integration, all with invalid versions.
    When
    - Calling the IsValidVersionValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 3 content items.
    """
    results = IsValidVersionValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidVersionValidator_fix():
    """
    Given
    - An integration with an invalid version.
    When
    - Calling the IsValidVersionValidator fix function.
    Then
    - Make sure that the object version was changed to -1, and that the right fix msg was returned.
    """
    content_item = create_integration_object(["commonfields.version"], [0])
    assert content_item.version != -1
    assert (
        IsValidVersionValidator().fix(content_item).message
        == "Updated the content item version to -1."
    )
    assert content_item.version == -1


@pytest.mark.parametrize(
    "content_items, expected_msg",
    [
        pytest.param(
            [
                create_integration_object(
                    paths=["name", "display"],
                    values=["Test v1", "Testv1"],
                ),
                create_integration_object(
                    paths=["name", "display"],
                    values=["Test Integration", "TestIntegration"],
                ),
            ],
            "The following fields: name, display shouldn't contain the word 'Integration'.",
            id="Case 1: Integration in name or display (valid and invalid)",
        ),
        pytest.param(
            [
                create_script_object(
                    paths=["name"],
                    values=["Test v1"],
                ),
                create_script_object(
                    paths=["name"],
                    values=["Test Script"],
                ),
            ],
            "The following field: name shouldn't contain the word 'Script'.",
            id="Case 2: Script in name or display (valid and invalid)",
        ),
        pytest.param(
            [
                create_playbook_object(
                    paths=["name"],
                    values=["Test v1"],
                ),
                create_playbook_object(
                    paths=["name"],
                    values=["Test Playbook"],
                ),
            ],
            "The following field: name shouldn't contain the word 'Playbook'.",
            id="Case 3: Playbook in name or display (valid and invalid)",
        ),
        pytest.param(
            [
                create_playbook_object(
                    paths=["name"],
                    values=["Test v1"],
                ),
                create_script_object(
                    paths=["name"],
                    values=["Test v1"],
                ),
                create_integration_object(
                    paths=["name", "display"],
                    values=["Test v1", "Testv1"],
                ),
            ],
            "",
            id="Case 4: All content items are valid",
        ),
    ],
)
def test_IsEntityTypeInEntityNameValidator_obtain_invalid_content_items(
    content_items, expected_msg
):
    """
    Given
    - Case 1: Two content items of type 'Integration' are validated.
        - The first integration doest not have its type in 'name' and 'display' fields.
        - The second integration does have its type in 'name' and 'display' fields.
    - Case 2: Two content items of type 'Script' are validated.
        - The first script doest not have its type in 'name' field.
        - The second script does have its type in 'name' field.
    - Case 3: Two content items of type 'Playbook' are validated.
        - The first playbook doest not have its type in 'name' field.
        - The second playbook does have its type in 'name' field.
    - Case 4:
        - All content items are valid.
    When
    - Running the IsEntityTypeInEntityNameValidator validation.
    Then
    - Case 1:
        - Don't fail the validation.
        - Fail the validation with a relevant message containing 'name' and 'display' fields.
    - Case 2:
        - Don't fail the validation.
        - Fail the validation with a relevant message containing 'name' field.
    - Case 3:
        - Don't fail the validation.
        - Fail the validation with a relevant message containing 'name' field.
    - Case 4:
        - Don't fail the validation and obtain_invalid_content_items function return empty array.
    """
    result = IsEntityTypeInEntityNameValidator().obtain_invalid_content_items(
        content_items
    )
    if result:
        assert result[0].message == expected_msg
        assert len(result) == 1
    else:
        assert len(result) == 0


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_error_message",
    [
        pytest.param(
            [create_integration_object()],
            0,
            "",
            id="valid integration",
        ),
        pytest.param(
            [create_integration_object(paths=["display"], values=["partner"])],
            1,
            ERROR_MSG_TEMPLATE.format("partner"),
            id="invalid integration",
        ),
        pytest.param([create_playbook_object()], 0, "", id="valid playbook"),
        pytest.param(
            [create_playbook_object(paths=["name"], values=["community"])],
            1,
            ERROR_MSG_TEMPLATE.format("community"),
            id="invalid playbook",
        ),
        pytest.param([create_script_object()], 0, "", id="valid script"),
        pytest.param(
            [create_script_object(paths=["name"], values=["community"])],
            1,
            ERROR_MSG_TEMPLATE.format("community"),
            id="invalid script",
        ),
        pytest.param([create_classifier_object()], 0, "", id="valid classifier"),
        pytest.param(
            [create_classifier_object(paths=["name"], values=["partner"])],
            1,
            ERROR_MSG_TEMPLATE.format("partner"),
            id="invalid classifier",
        ),
    ],
)
def test_IsEntityNameContainExcludedWordValidator(
    content_items, expected_number_of_failures, expected_error_message
):
    """
    Given
    - Case 1: Content item of type 'Integration' which contains a valid entity name.
    - Case 2: Content item of type 'Integration' which contains an invalid entity name.
    - Case 3: Content item of type 'Playbook' which contains a valid entity name.
    - Case 4: Content item of type 'Playbook' which contains an invalid entity name.

    - Case 5: Content item of type 'Script' which contains a valid entity name.
    - Case 6: Content item of type 'Script' which contains an invalid entity name.

    - Case 7: Content item of type 'Classifier' which contains a valid entity name.
    - Case 8: Content item of type 'Classifier' which contains an invalid entity name.

    When
    - Running the IsEntityNameContainExcludedWordValidator validation.
    Then
    - Case 1: Don't fail the validation.
    - Case 2: Fail the validation with a relevant message containing 'name' field.
    - Case 3: Don't fail the validation.
    - Case 4: Fail the validation with a relevant message containing 'name' field.
    - Case 5: Don't fail the validation.
    - Case 6: Fail the validation with a relevant message containing 'name' field.
    - Case 7: Don't fail the validation.
    - Case 8: Fail the validation with a relevant message containing 'name' field.
    """
    results = IsEntityNameContainExcludedWordValidator().obtain_invalid_content_items(
        content_items=content_items
    )
    assert len(results) == expected_number_of_failures
    if results:
        assert results[0].message == expected_error_message


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [create_pack_object(), create_pack_object()],
            1,
            [
                "Pack for content item '/newPackName' and all related files were changed from 'pack_171' to 'newPackName', please undo."
            ],
        ),
        (
            [create_integration_object(), create_integration_object()],
            1,
            [
                "Pack for content item '/newPackName/Integrations/integration_0/integration_0.yml' and all related files were changed from 'pack_173' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_parsing_rule_object(),
                create_parsing_rule_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/ParsingRules/TestParsingRule/TestParsingRule.yml' and all related files were changed from 'pack_175' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_correlation_rule_object(),
                create_correlation_rule_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/CorrelationRules/correlation_rule.yml' and all related files were changed from 'pack_177' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_playbook_object(),
                create_playbook_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Playbooks/playbook-0.yml' and all related files were changed from 'pack_179' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_modeling_rule_object(),
                create_modeling_rule_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/ModelingRules/modelingrule_0/modelingrule_0.yml' and all related files were changed from 'pack_181' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_ps_integration_object(),
                create_ps_integration_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Integrations/integration_0/integration_0.yml' and all related files were changed from 'pack_183' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_script_object(),
                create_script_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Scripts/script0/script0.yml' and all related files were changed from 'pack_185' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_classifier_object(),
                create_classifier_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Classifiers/classifier-test_classifier.json' and all related files were changed from 'pack_187' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_list_object(),
                create_list_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Lists/list-list.json' and all related files were changed from 'pack_189' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_job_object(),
                create_job_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Jobs/job-job.json' and all related files were changed from 'pack_191' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_dashboard_object(),
                create_dashboard_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Dashboards/dashboard-dashboard.json' and all related files were changed from 'pack_193' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_incident_type_object(),
                create_incident_type_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/IncidentTypes/incidenttype-incident_type.json' and all related files were changed from 'pack_195' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_incident_field_object(),
                create_incident_field_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/IncidentFields/incidentfield-incident_field.json' and all related files were changed from 'pack_197' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_report_object(),
                create_report_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Reports/report-report.json' and all related files were changed from 'pack_199' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_xsiam_report_object(),
                create_xsiam_report_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/XSIAMReports/xsiam_report.json' and all related files were changed from 'pack_201' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_xsiam_dashboard_object(),
                create_xsiam_dashboard_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/XSIAMDashboards/xsiam_dashboard.json' and all related files were changed from 'pack_203' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_xdrc_template_object(),
                create_xdrc_template_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/XDRCTemplates/pack_205_xdrc_template/xdrc_template.json' and all related files were changed from 'pack_205' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_assets_modeling_rule_object(),
                create_assets_modeling_rule_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/AssetsModelingRules/assets_modeling_rule/assets_modeling_rule.yml' and all related files were changed from 'pack_207' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_trigger_object(),
                create_trigger_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Triggers/trigger.json' and all related files were changed from 'pack_209' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_layout_object(),
                create_layout_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Layouts/layout-layout.json' and all related files were changed from 'pack_211' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_widget_object(),
                create_widget_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Widgets/widget-widget.json' and all related files were changed from 'pack_213' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_indicator_field_object(),
                create_indicator_field_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/IndicatorFields/indicatorfield-indicator_field.json' and all related files were changed from 'pack_215' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_wizard_object(),
                create_wizard_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Wizards/wizard-test_wizard.json' and all related files were changed from 'pack_217' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_generic_definition_object(),
                create_generic_definition_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/GenericDefinitions/genericdefinition-generic_definition.json' and all related files were changed from 'pack_219' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_generic_field_object(),
                create_generic_field_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/GenericFields/generic_field/genericfield-generic_field.json' and all related files were changed from 'pack_221' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_generic_type_object(),
                create_generic_type_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/GenericTypes/generic_type/generictype-generic_type.json' and all related files were changed from 'pack_223' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_generic_module_object(),
                create_generic_module_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/GenericModules/genericmodule-generic_module.json' and all related files were changed from 'pack_225' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_incoming_mapper_object(),
                create_incoming_mapper_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Classifiers/classifier-mapper-incoming_mapper.json' and all related files were changed from 'pack_227' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_outgoing_mapper_object(),
                create_outgoing_mapper_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/Classifiers/classifier-mapper-outgoing_mapper.json' and all related files were changed from 'pack_229' to 'newPackName', please undo."
            ],
        ),
        (
            [
                create_indicator_type_object(),
                create_indicator_type_object(),
            ],
            1,
            [
                "Pack for content item '/newPackName/IndicatorTypes/reputation-indicator_type.json' and all related files were changed from 'pack_231' to 'newPackName', please undo."
            ],
        ),
    ],
)
def test_ValidPackNameValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given:
    content_items.
        31 content items.
        Each test contains one object where the pack name was changed, and one where it was not.

    When:
        - Calling the PackNameValidator obtain_invalid_content_items function.

    Then:
        - Make sure the right amount of tests failed, and that the right error message is returned.
        - For each test, one should fail while the other should pass.
    """
    old_content_items = copy.deepcopy(content_items)
    create_old_file_pointers(content_items, old_content_items)
    content_item_parts = list(content_items[1].path.parts)
    packs_folder_index = content_item_parts.index(PACKS_FOLDER) + 1
    content_item_parts[packs_folder_index] = "newPackName"
    new_path = Path(*content_item_parts)
    content_items[1].path = new_path
    results = PackNameValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_error_message",
    [
        pytest.param([create_integration_object()], 0, "", id="valid: integration"),
        pytest.param(
            [create_integration_object(readme_content="test-module")],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: integration readme",
        ),
        pytest.param(
            [create_integration_object(description_content="test-module")],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: integration description",
        ),
        pytest.param([create_script_object()], 0, "", id="valid: script"),
        pytest.param(
            [create_script_object(readme_content="test-module ")],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: script readme",
        ),
        pytest.param([create_playbook_object()], 0, "", id="valid: playbook"),
        pytest.param(
            [create_playbook_object(readme_content="test-module ")],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: playbook readme",
        ),
        pytest.param([create_pack_object()], 0, "", id="valid: pack"),
        pytest.param(
            [create_pack_object(readme_text="test-module ")],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: pack readme",
        ),
        pytest.param(
            [
                create_pack_object(
                    ["currentVersion"], ["1.0.1"], release_note_content="test-module"
                )
            ],
            1,
            FOUND_INTERNAL_TERMS_ERROR,
            id="invalid: pack release note",
        ),
    ],
)
def test_CustomerFacingDocsDisallowedTermsValidator(
    content_items, expected_number_of_failures, expected_error_message
):
    """
    Given
    - Case 1: Content items containing disallowed terms in their related files.
    - Case 2: Content items containing only valid terms in their related files.
    When
    - Running the CustomerFacingDocsDisallowedTermsValidator validation.
    Then
    - Case 1: Fail the validation with a relevant message containing the found disallowed terms.
    - Case 2: Don't fail the validation.
    """
    results = CustomerFacingDocsDisallowedTermsValidator().obtain_invalid_content_items(
        content_items=content_items
    )
    assert len(results) == expected_number_of_failures
    if results:
        assert str(expected_error_message) in results[0].message


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_script_object(), create_integration_object()], 0, []),
        (
            [
                create_script_object(code="BSD\nMIT"),
                create_script_object(
                    code="MIT", test_code="here we are going to fail\nproprietary"
                ),
                create_integration_object(code="Copyright"),
            ],
            4,
            [
                "The file contains copyright key words (BSD, MIT, Copyright, proprietary) in line(s): 1, 2.",
                "The file contains copyright key words (BSD, MIT, Copyright, proprietary) in line(s): 1.",
                "The file contains copyright key words (BSD, MIT, Copyright, proprietary) in line(s): 2.",
                "The file contains copyright key words (BSD, MIT, Copyright, proprietary) in line(s): 1.",
            ],
        ),
    ],
)
def test_IsPyFileContainCopyRightSectionValidator(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    Content item iterables.
    - Case 1: One script and one integration without any copyright keywords in the code/test code.
    - Case 2: 3 content items:
        - One integration with copyright keywords in both line 1 and 2 in the code_file.
        - One script with copyright keyword in the code in line 1 and in the test_code in line 2.
        - One script with copyright keyword in the code in line 1.
    When
    - Running the IsPyFileContainCopyRightSectionValidator validation.
    Then
    - Make sure the right number of content_items failed and the right error was returned.
    - Case 1: Shouldn't fail anything.
    - Case 2: Should fail all.
    """
    results = IsPyFileContainCopyRightSectionValidator().obtain_invalid_content_items(
        content_items=content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items",
    [
        pytest.param(create_incident_field_object(), id="incident_field"),
        pytest.param(create_widget_object(), id="widget"),
        pytest.param(create_report_object(), id="report"),
        pytest.param(create_xsiam_report_object(), id="xsiam_report"),
        pytest.param(create_script_object(), id="script"),
        pytest.param(create_dashboard_object(), id="dashboard"),
        pytest.param(create_incident_type_object(), id="incident_type"),
        pytest.param(create_generic_type_object(), id="generic_type"),
        pytest.param(create_outgoing_mapper_object(), id="outgoing_mapper"),
        pytest.param(create_generic_definition_object(), id="generic_definition"),
        pytest.param(create_classifier_object(), id="classifier"),
        pytest.param(create_xsiam_dashboard_object(), id="xsiam_dashboard"),
        pytest.param(create_job_object(), id="job"),
        pytest.param(create_list_object(), id="list"),
        pytest.param(create_parsing_rule_object(), id="parsing_rule"),
        pytest.param(create_playbook_object(), id="playbook"),
        pytest.param(create_generic_field_object(), id="generic_field"),
        pytest.param(create_correlation_rule_object(), id="correlation_rule"),
        pytest.param(create_assets_modeling_rule_object(), id="assets_modeling_rule"),
        pytest.param(create_layout_object(), id="layout"),
    ],
)
def test_IsContentItemNameContainTrailingSpacesValidator_obtain_invalid_content_items_success(
    content_items: ContentTypes113,
):
    """Test validate BA113 - Trailing spaces in content item name
    Given:
        A list of content items with names that have trailing spaces.
    When:
        The IsContentItemNameContainTrailingSpacesValidator's obtain_invalid_content_items method is called.
    Then:
        The method should return False, indicating that there are no validation failures.
    """
    assert not IsContentItemNameContainTrailingSpacesValidator().obtain_invalid_content_items(
        [content_items]
    )  # no failures


@pytest.mark.parametrize(
    "content_items, expected_field_error_messages",
    [
        pytest.param(
            create_classifier_object(
                paths=["name", "id"],
                values=[VALUE_WITH_TRAILING_SPACE, VALUE_WITH_TRAILING_SPACE],
            ),
            ["object_id, name"],
            id="classifier_with_trailing_space",
        ),
        pytest.param(
            create_integration_object(
                paths=["name", "commonfields.id"],
                values=[VALUE_WITH_TRAILING_SPACE, VALUE_WITH_TRAILING_SPACE],
            ),
            ["object_id, name"],
            id="integration_with_trailing_space",
        ),
        pytest.param(
            create_indicator_field_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="indicator_field_with_trailing_space",
        ),
        pytest.param(
            create_wizard_object({"name": VALUE_WITH_TRAILING_SPACE}),
            ["name"],
            id="wizard_with_trailing_space",
        ),
        pytest.param(
            create_correlation_rule_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="correlation_rule_with_trailing_space",
        ),
        pytest.param(
            create_incident_type_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="incident_type_with_trailing_space",
        ),
        pytest.param(
            create_dashboard_object(paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]),
            ["name"],
            id="dashboard_with_trailing_space",
        ),
        pytest.param(
            create_generic_definition_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="generic_definition_with_trailing_space",
        ),
        pytest.param(
            create_generic_type_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="generic_type_with_trailing_space",
        ),
        pytest.param(
            create_generic_module_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="generic_module_with_trailing_space",
        ),
        pytest.param(
            create_generic_field_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="generic_field_with_trailing_space",
        ),
        pytest.param(
            create_layout_object(paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]),
            ["name"],
            id="layout_with_trailing_space",
        ),
        pytest.param(
            create_modeling_rule_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="modeling_rule_with_trailing_space",
        ),
        pytest.param(
            create_incoming_mapper_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="incoming_mapper_with_trailing_space",
        ),
        pytest.param(
            create_parsing_rule_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="parsing_rule_with_trailing_space",
        ),
        pytest.param(
            create_playbook_object(paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]),
            ["name"],
            id="playbook_with_trailing_space",
        ),
    ],
)
def test_IsContentItemNameContainTrailingSpacesValidator_obtain_invalid_content_items_failure(
    content_items: ContentTypes113,
    expected_field_error_messages: List[str],
):
    """
    Given:
        A list of content items with names that may contain trailing spaces.
    When:
        The `IsContentItemNameContainTrailingSpacesValidator.obtain_invalid_content_items` method is called.
    Then:
        The method should return the correct number of validation failures and the correct error messages.
    """
    results = (
        IsContentItemNameContainTrailingSpacesValidator().obtain_invalid_content_items(
            [content_items]
        )
    )
    assert len(results) == 1  # one failure
    assert (
        results[0].message
        == f"The following fields have a trailing spaces: {expected_field_error_messages[0]}."
    )


@pytest.mark.parametrize(
    "content_item, fields_with_trailing_spaces",
    [
        pytest.param(
            create_integration_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="case integration with trailing spaces in name with fix",
        ),
        pytest.param(
            create_classifier_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            {"name": "name"},
            id="case classifier with trailing spaces in name with fix",
        ),
        pytest.param(
            create_dashboard_object(paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]),
            ["name"],
            id="case dashboard with trailing spaces in name with fix",
        ),
        pytest.param(
            create_incident_type_object(
                paths=["name"], values=[VALUE_WITH_TRAILING_SPACE]
            ),
            ["name"],
            id="case incident type with trailing spaces in name with fix",
        ),
        pytest.param(
            create_wizard_object({"name": VALUE_WITH_TRAILING_SPACE}),
            ["name"],
            id="case wizard with trailing spaces in name with fix",
        ),
        pytest.param(
            create_classifier_object(
                paths=["name", "id"],
                values=[VALUE_WITH_TRAILING_SPACE, VALUE_WITH_TRAILING_SPACE],
            ),
            ["object_id", "name"],
            id="classifier and integration with trailing spaces",
        ),
    ],
)
def test_IsContentItemNameContainTrailingSpacesValidator_fix(
    content_item: ContentTypes113, fields_with_trailing_spaces: List[str]
):
    """
    Test validate BA113 - Trailing spaces in content item name

    Given:
        - A content item with a name that has trailing spaces.
    When:
        - The IsContentItemNameContainTrailingSpacesValidator's fix method is called.
    Then:
        - The trailing spaces should be removed from the content item's name, and the fix message should indicate that the trailing spaces have been removed.

    Test cases:
        - Various content items (integrations, classifiers, dashboards, incident types, wizards) are created with trailing spaces in their names.
            The validator should remove the trailing spaces and return a fix message for each.
    """
    validator = IsContentItemNameContainTrailingSpacesValidator()
    validator.violations[content_item.object_id] = fields_with_trailing_spaces

    assert content_item.name == VALUE_WITH_TRAILING_SPACE

    results = validator.fix(content_item)
    assert content_item.name == VALUE_WITH_TRAILING_SPACE.rstrip()
    assert (
        results.message
        == f"Removed trailing spaces from the {', '.join(fields_with_trailing_spaces)} fields of following content items: {VALUE_WITH_TRAILING_SPACE.rstrip()}"
    )


@pytest.mark.parametrize(
    "content_item, expected_number_of_failures, expected_messages",
    [
        pytest.param(
            create_integration_object(name="Test-Integration"),
            1,
            "The Integration files should be named without any separators in the base name:\n'Test-Integration.py' should be named 'TestIntegration.py'\n'Test-Integration.yml' should be named 'TestIntegration.yml'\n'Test-Integration_description.md' should be named 'TestIntegration_description.md'\n'Test-Integration_image.png' should be named 'TestIntegration_image.png'\n'Test-Integration_test.py' should be named 'TestIntegration_test.py'",
            id="invalid integration",
        ),
        pytest.param(
            create_integration_object(name="TestIntegration"),
            0,
            [""],
            id="valid integration",
        ),
        pytest.param(
            create_script_object(name="Test-Script"),
            1,
            "The Script files should be named without any separators in the base name:\n'Test-Script.py' should be named 'TestScript.py'\n'Test-Script.yml' should be named 'TestScript.yml'\n'Test-Script_description.md' should be named 'TestScript_description.md'\n'Test-Script_image.png' should be named 'TestScript_image.png'\n'Test-Script_test.py' should be named 'TestScript_test.py'",
            id="invalid script",
        ),
        pytest.param(
            create_script_object(name="TestScript"),
            0,
            [""],
            id="valid script",
        ),
    ],
)
def test_FileNameHasSeparatorsValidator_obtain_invalid_content_items(
    content_item, expected_number_of_failures, expected_messages
):
    """
    Test validate BA109 FileNameHasSeparatorsValidator - File names with separators

    Given:
        A content item with a name that contains separators (e.g., hyphens) or not.

    When:
        The FileNameHasSeparatorsValidator's obtain_invalid_content_items method is called.

    Then:
        The method should return the expected number of validation failures and messages.
        Failure with an appropriate message if the name contains separators.
    """
    validator = FileNameHasSeparatorsValidator()
    ValidationResultList = validator.obtain_invalid_content_items([content_item])

    assert len(ValidationResultList) == expected_number_of_failures

    if ValidationResultList:
        assert ValidationResultList[0].message == expected_messages


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msg",
    [
        pytest.param(
            [
                create_integration_object(name="invalid_integration_name"),
            ],
            1,
            "The folder name 'invalid_integration_name' should not contain any of the following separators: '_', '-'",
            id="an invalid integration name",
        ),
        pytest.param(
            [
                create_integration_object(name="invalidIntegrationName"),
            ],
            0,
            "",
            id="a valid integration name.",
        ),
        pytest.param(
            [
                create_script_object(name="invalid-script-name"),
            ],
            1,
            "The folder name 'invalid-script-name' should not contain any of the following separators: '_', '-'",
            id="an invalid script name",
        ),
        pytest.param(
            [
                create_script_object(name="invalidScriptName"),
            ],
            0,
            "",
            id="a valid script name",
        ),
    ],
)
def test_IsFolderNameHasSeparatorsValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msg
):
    result = IsFolderNameHasSeparatorsValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(result) == expected_number_of_failures

    if result:
        assert result[0].message == expected_msg


def test_IsHaveUnitTestFileValidator_obtain_invalid_content_items__all_valid():
    """
    Given
    - Two valid integrations:
        - One Xsoar supported integration with a valid unit test file name.
        - One Partner supported integration with a valid unit test file name.
    When
    - Calling the IsHaveUnitTestFileValidator obtain_invalid_content_items function.
    Then
    - Make sure no failures are returned.
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_integration_object(
                name="MyIntegration0",
                unit_test_name="MyIntegration0",
                pack_info={"support": XSOAR_SUPPORT},
            ),
            create_integration_object(
                name="MyIntegration0",
                unit_test_name="MyIntegration0",
                pack_info={"support": PARTNER_SUPPORT},
            ),
        ]

        results = IsHaveUnitTestFileValidator().obtain_invalid_content_items(
            content_items
        )

    assert len(results) == 0


def test_IsHaveUnitTestFileValidator_obtain_invalid_content_items__invalid_item():
    """
    Given
    - One invalid integration:
        - One Xsoar supported integration with an invalid unit test file name.
    When
    - Calling the IsHaveUnitTestFileValidator obtain_invalid_content_items function.
    Then
    - Make sure one failure is returned and the error message is correct.
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_integration_object(
                name="MyIntegration0",
                unit_test_name="myintegration0",
                pack_info={"support": XSOAR_SUPPORT},
            ),
        ]

        results = IsHaveUnitTestFileValidator().obtain_invalid_content_items(
            content_items
        )

    expected_msgs = [
        "The given Integration is missing a unit test file, please make sure to add one with the following name MyIntegration0_test.py."
    ]

    assert len(results) == 1
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_is_valid_context_path_depth_command():
    """
    Given
    - One invalid integration with one command:
        - One output has depth bigger then 5.
    When
    - Calling the IsValidContextPathDepthValidator obtain_invalid_content_items function.
    Then
    - Make sure one failure is returned and the error message is correct.
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "ip",
                            "description": "ip command",
                            "deprecated": False,
                            "arguments": [],
                            "outputs": [
                                {
                                    "name": "output_1",
                                    "contextPath": "path_1.2.3.4.5.6",
                                    "description": "description_1",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2",
                                    "description": "description_2",
                                },
                            ],
                        },
                    ]
                ],
                pack_info={"support": XSOAR_SUPPORT},
            ),
        ]
        expected_msg = "The level of depth for context output path for command: ip In the yml should be less or equal to 5 check the following outputs:\npath_1.2.3.4.5.6\n"
        result = IsValidContextPathDepthValidator().obtain_invalid_content_items(
            content_items
        )
        assert len(result) == 1

        if result:
            assert result[0].message == expected_msg


def test_is_valid_context_path_depth_script():
    """
    Given
    - One invalid script :
        - One output has depth bigger then 5.
    When
    - Calling the IsValidContextPathDepthValidator obtain_invalid_content_items function.
    Then
    - Make sure one failure is returned and the error message is correct.
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_script_object(
                paths=["outputs"],
                values=[
                    [
                        {"contextPath": "File.EntryID", "description": "test_3"},
                        {
                            "contextPath": "test.test.1.2.3.4.5.6",
                            "description": "test_4",
                        },
                    ]
                ],
                pack_info={"support": XSOAR_SUPPORT},
            ),
        ]
        expected_msg = "The level of depth for context output path for script: myScript In the yml should be less or equal to 5 check the following outputs:\ntest.test.1.2.3.4.5.6"
        result = IsValidContextPathDepthValidator().obtain_invalid_content_items(
            content_items
        )
        assert len(result) == 1

        if result:
            assert result[0].message == expected_msg


def test_is_valid_context_path_depth_command_multiple_invalid_outputs():
    """
    Given
    - One invalid integration with one command:
        - multiple outputs have depth bigger then 5.
    When
    - Calling the IsValidContextPathDepthValidator obtain_invalid_content_items function.
    Then
    - Make sure the paths exist in the error message that is returned
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "ip",
                            "description": "ip command",
                            "deprecated": False,
                            "arguments": [],
                            "outputs": [
                                {
                                    "name": "output_1",
                                    "contextPath": "path_1.2.3.4.5.6",
                                    "description": "description_1",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2",
                                    "description": "description_2",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2.3.4.5.6.7.8.9",
                                    "description": "description_2",
                                },
                            ],
                        },
                    ]
                ],
                pack_info={"support": XSOAR_SUPPORT},
            ),
        ]

        invalid_path_1 = "path_1.2.3.4.5.6"
        invalid_path_2 = "path_2.3.4.5.6.7.8.9"
        result = IsValidContextPathDepthValidator().obtain_invalid_content_items(
            content_items
        )
        assert len(result) == 1

        if result:
            assert invalid_path_1 in result[0].message
            assert invalid_path_2 in result[0].message


def test_is_valid_context_path_depth_command_multiple_commands_with_invalid_outputs():
    """
    Given
    - One invalid integration with two commands each has several outputs:
        - two outputs for each command have depth bigger then 5.
    When
    - Calling the IsValidContextPathDepthValidator obtain_invalid_content_items function.
    Then
    - Make sure the paths exist in the error message that is returned
    """
    with ChangeCWD(REPO.path):
        content_items = [
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "ip",
                            "description": "ip command",
                            "deprecated": False,
                            "arguments": [],
                            "outputs": [
                                {
                                    "name": "output_1",
                                    "contextPath": "path_1.2.3.4.5.6",
                                    "description": "description_1",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2",
                                    "description": "description_2",
                                },
                                {
                                    "name": "output_3",
                                    "contextPath": "path_3.3.4.5.6.7.8.9",
                                    "description": "description_3",
                                },
                            ],
                        },
                        {
                            "name": "file",
                            "description": "file command",
                            "deprecated": False,
                            "arguments": [],
                            "outputs": [
                                {
                                    "name": "output_1",
                                    "contextPath": "path_10.11.12.13.14.15",
                                    "description": "description_1",
                                },
                                {
                                    "name": "output_2",
                                    "contextPath": "path_2",
                                    "description": "description_2",
                                },
                                {
                                    "name": "output_3",
                                    "contextPath": "path_12.13.14.15.16.17.18.19",
                                    "description": "description_2",
                                },
                            ],
                        },
                    ]
                ],
                pack_info={"support": XSOAR_SUPPORT},
            ),
        ]
        invalid_path_ip_1 = "path_1.2.3.4.5.6"
        invalid_path_ip_2 = "path_3.3.4.5.6.7.8.9"
        invalid_path_file_1 = "path_10.11.12.13.14.15"
        invalid_path_file_2 = "path_12.13.14.15.16.17.18.19"
        result = IsValidContextPathDepthValidator().obtain_invalid_content_items(
            content_items
        )
        assert len(result) == 1

        if result:
            assert invalid_path_ip_1 in result[0].message
            assert invalid_path_ip_2 in result[0].message
            assert invalid_path_file_1 in result[0].message
            assert invalid_path_file_2 in result[0].message


def test_IsTestsSectionValidValidator_obtain_invalid_content_items():
    """
    Given
    - content items iterable with 5 content items:
        - One integration with a tests section which is an empty list.
        - One integration with a tests section which is the string "No tests (auto formatted)".
        - One script with a tests section which is an the string "No tests".
        - One script with a tests section which is a non empty list.
        - One script with a tests section which is an empty string.
    When
    - Calling the IsTestsSectionValidValidator obtain_invalid_content_items function.
    Then
    - Make sure the right amount of failures is returned and the error message is correct:
        - Should fail.
        - Shouldn't fail.
        - Shouldn't fail.
        - Shouldn't fail.
        - Should fail.
    """
    content_items = [
        create_integration_object(paths=["tests"], values=[[]]),
        create_integration_object(
            paths=["tests"], values=["No tests (auto formatted)"]
        ),
        create_script_object(paths=["tests"], values=["No tests"]),
        create_script_object(paths=["tests"], values=[["- test_1", "- test_2"]]),
        create_script_object(paths=["tests"], values=[""]),
    ]
    results = IsTestsSectionValidValidator().obtain_invalid_content_items(content_items)
    assert len(results) == 2
    expected_msgs = [
        'The tests section of the following Integration is malformed. It should either be a non empty list for tests or "No tests" in case there are no tests.',
        'The tests section of the following Script is malformed. It should either be a non empty list for tests or "No tests" in case there are no tests.',
    ]
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_is_command_or_script_name_starts_with_digit_invalid():
    """
    Given
    - One invalid integration with two commands (one of which starts with a digit character).
    When
    - Calling the IsCommandOrScriptNameStartsWithDigitValidator obtain_invalid_content_items function.
    Then
    - Make sure one failure is returned and the error message contains the relevant command name.
    """
    content_items = [
        create_integration_object(
            paths=["script.commands"],
            values=[
                [
                    {
                        "name": "1system-get-users",
                        "description": "Get users from 1System",
                        "deprecated": False,
                        "arguments": [],
                        "outputs": [],
                    },
                    {
                        "name": "one-system-get-assets",
                        "description": "Get cloud assets from 1System",
                        "deprecated": False,
                        "arguments": [],
                        "outputs": [],
                    },
                ]
            ],
            pack_info={"support": XSOAR_SUPPORT},
        ),
    ]
    expected_msg = (
        "The following integration command names start with a digit: 1system-get-users"
    )
    results = (
        IsCommandOrScriptNameStartsWithDigitValidator().obtain_invalid_content_items(
            content_items
        )
    )

    assert len(results) == 1
    assert results[0].message == expected_msg


def test_is_command_or_script_name_starts_with_digit_valid():
    """
    Given
    - One valid integration with one command starting with a letter character.
    When
    - Calling the IsCommandOrScriptNameStartsWithDigitValidator obtain_invalid_content_items function.
    Then
    - Make sure no failures are returned.
    """
    content_items = [
        create_integration_object(
            paths=["script.commands"],
            values=[
                [
                    {
                        "name": "one-system-get-users",
                        "description": "Get users from 1System",
                        "deprecated": False,
                        "arguments": [],
                        "outputs": [],
                    },
                ]
            ],
            pack_info={"support": XSOAR_SUPPORT},
        ),
    ]
    results = (
        IsCommandOrScriptNameStartsWithDigitValidator().obtain_invalid_content_items(
            content_items
        )
    )

    assert len(results) == 0


@pytest.mark.parametrize(
    "content_item, policy_names, expected_failures",
    [
        pytest.param(
            create_script_object(
                paths=["compliantpolicies"], values=[["valid_policy_1"]]
            ),
            {"valid_policy_1"},
            [],
            id="valid_policy_name",
        ),
        pytest.param(
            create_script_object(
                paths=["compliantpolicies"], values=[["invalid_policy"]]
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy"],
            id="invalid_policy_name",
        ),
        pytest.param(
            create_script_object(
                paths=["compliantpolicies"],
                values=[["valid_policy_1", "valid_policy_2"]],
            ),
            {"valid_policy_1", "valid_policy_2"},
            [],
            id="multiple_valid_policies",
        ),
        pytest.param(
            create_script_object(
                paths=["compliantpolicies"],
                values=[["valid_policy_1", "invalid_policy"]],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy"],
            id="mixed_valid_and_invalid_policies",
        ),
        pytest.param(
            create_script_object(paths=["compliantpolicies"], values=[[]]),
            {"valid_policy_1"},
            [],
            id="empty_policy_list",
        ),
        pytest.param(
            create_script_object(
                paths=["compliantpolicies"],
                values=[["invalid_policy_1", "invalid_policy_2"]],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy_1", "invalid_policy_2"],
            id="multiple_invalid_policies",
        ),
    ],
)
def test_script_compliant_policy_name_validator(
    content_item, policy_names, expected_failures
):
    """
    Given
    - A Script object with compliant policies.
    When
    - Calling the IsValidCompliantPolicyNameValidator content_contains_invalid_compliant_policy_name function.
    Then
    - Make sure the expected sorted list of failures is returned.

    Test cases:
    - A script with valid policy name
    - A script with invalid policy name
    - A script with multiple valid policies
    - A script with a mix of valid and invalid policies
    - A script with empty policy list
    - A script with multiple invalid policies
    """
    results = IsValidCompliantPolicyNameValidator().get_invalid_compliant_policies(
        content_item, policy_names
    )
    assert results == sorted(expected_failures)


@pytest.mark.parametrize(
    "content_item, policy_names, expected_failures",
    [
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [{"name": "test-command", "compliantpolicies": ["valid_policy_1"]}]
                ],
            ),
            {"valid_policy_1"},
            [],
            id="integration_with_valid_policy",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [{"name": "test-command", "compliantpolicies": ["invalid_policy"]}]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy"],
            id="integration_with_invalid_policy",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "test-command",
                            "compliantpolicies": ["valid_policy_1", "valid_policy_2"],
                        }
                    ]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            [],
            id="integration_with_multiple_valid_policies",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "test-command",
                            "compliantpolicies": ["valid_policy_1", "invalid_policy"],
                        }
                    ]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy"],
            id="integration_with_mixed_valid_and_invalid_policies",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[[{"name": "test-command", "compliantpolicies": []}]],
            ),
            {"valid_policy_1"},
            [],
            id="integration_with_empty_policy_list",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {
                            "name": "test-command",
                            "compliantpolicies": [
                                "invalid_policy_2",
                                "invalid_policy_1",
                            ],
                        }
                    ]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy_1", "invalid_policy_2"],
            id="integration_with_multiple_invalid_policies",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {"name": "command1", "compliantpolicies": ["valid_policy_1"]},
                        {"name": "command2", "compliantpolicies": ["invalid_policy"]},
                    ]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy"],
            id="integration_with_multiple_commands_one_invalid_policy",
        ),
        pytest.param(
            create_integration_object(
                paths=["script.commands"],
                values=[
                    [
                        {"name": "command1", "compliantpolicies": ["invalid_policy_1"]},
                        {"name": "command2", "compliantpolicies": ["invalid_policy_2"]},
                    ]
                ],
            ),
            {"valid_policy_1", "valid_policy_2"},
            ["invalid_policy_1", "invalid_policy_2"],
            id="integration_with_multiple_commands_multiple_invalid_policies",
        ),
    ],
)
def test_integration_compliant_policy_name_validator(
    content_item, policy_names, expected_failures
):
    """
    Given
    - An integration with commands containing compliant policies.
    When
    - Calling the IsValidCompliantPolicyNameValidator content_contains_invalid_compliant_policy_name function.
    Then
    - Make sure the expected sorted list of failures is returned.

    Test cases:
    - An integration with valid policy name
    - An integration with invalid policy name
    - An integration with multiple valid policies
    - An integration with a mix of valid and invalid policies
    - An integration with empty policy list
    - An integration with multiple invalid policies
    - An integration with multiple commands where one has invalid policy
    - An integration with multiple commands where multiple have invalid policies
    """
    results = IsValidCompliantPolicyNameValidator().get_invalid_compliant_policies(
        content_item, policy_names
    )
    assert results == sorted(expected_failures)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_pack_object(
                    readme_text="# Test Pack\n\n<~XSOAR>This is for XSOAR</~XSOAR>\n\n<~XSIAM>This is for XSIAM</~XSIAM>"
                ),
                create_integration_object(
                    description_content="<~XSOAR_SAAS>XSOAR SaaS only content</~XSOAR_SAAS>"
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_pack_object(
                    readme_text="<~INVALID_TAG>This is invalid</~INVALID_TAG>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_313/README.md: Invalid marketplace tag(s) found: INVALID_TAG. Allowed tags:",
            ],
        ),
        (
            [
                create_integration_object(
                    description_content="<~XSOAR>This is mismatched</~XSIAM>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_314/Integrations/integration_0/integration_0_description.md: Mismatched marketplace tags: opened with 'XSOAR' but closed with 'XSIAM'",
            ],
        ),
        (
            [
                create_pack_object(readme_text="<~XSOAR>This tag is never closed"),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_315/README.md: Unclosed marketplace tag: 'XSOAR' is missing its closing tag",
            ],
        ),
        (
            [
                create_pack_object(
                    readme_text="This closing tag has no opening </~XSOAR>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_316/README.md: Closing tag 'XSOAR' found without corresponding opening tag",
            ],
        ),
        (
            [
                create_pack_object(
                    readme_text="<~XSOAR>Outer tag <~XSIAM>Inner tag</~XSIAM></~XSOAR>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_317/README.md: Nested marketplace tags are not allowed. Tag 'XSIAM' cannot be placed inside tag 'XSOAR'",
            ],
        ),
        (
            [
                create_pack_object(
                    readme_text="<~INVALID,INVALID_B>Multiple invalid tags</~NVALID,INVALID_B>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_318/README.md: Invalid marketplace tag(s) found: INVALID, INVALID_B. Allowed tags:",
            ],
        ),
        (
            [
                create_pack_object(
                    readme_text="<~XSOAR,XSIAM>Content for both platforms</~XSOAR,XSIAM>"
                ),
            ],
            0,
            [],
        ),
        (
            [
                create_pack_object(
                    readme_text="This closing tag has no opening </~XSOAR>"
                ),
            ],
            1,
            [
                "Found malformed marketplace tags in the following files:\nPacks/pack_320/README.md: Closing tag 'XSOAR' found without corresponding opening tag",
            ],
        ),
    ],
)
def test_MarketplaceTagsValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    - Content items with various marketplace tag scenarios.
    When
    - Calling the MarketplaceTagsValidator obtain_invalid_content_items function.
    Then
    - Make sure the right amount of failures is returned and that the error msg is correct.

    Test cases:
    - Valid marketplace tags in pack README and integration description
    - Invalid marketplace tag name in pack README
    - Mismatched opening and closing tags in integration description
    - Unclosed marketplace tag in pack README
    - Closing tag without corresponding opening tag in pack README
    - Nested marketplace tags (not allowed) in pack README
    - Multiple invalid tags in comma-separated format in pack README
    - Valid multiple tags in comma-separated format in pack README
    - Duplicate case - closing tag without corresponding opening tag
    """
    results = MarketplaceTagsValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    if expected_msgs:
        result_messages = [result.message for result in results]
        assert expected_msgs[0] in result_messages[0]

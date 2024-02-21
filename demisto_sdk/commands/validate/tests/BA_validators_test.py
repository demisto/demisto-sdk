from collections.abc import Iterable
from typing import List

import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
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
    create_integration_object,
    create_job_object,
    create_layout_object,
    create_list_object,
    create_modeling_rule_object,
    create_outgoing_mapper_object,
    create_parsing_rule_object,
    create_playbook_object,
    create_ps_integration_object,
    create_report_object,
    create_script_object,
    create_widget_object,
    create_wizard_object,
    create_xsiam_dashboard_object,
    create_xsiam_report_object,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
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
from demisto_sdk.commands.validate.validators.BA_validators.BA113_is_content_item_name_contain_trailing_spaces import (
    ContentTypes as ContentTypes113,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA113_is_content_item_name_contain_trailing_spaces import (
    IsContentItemNameContainTrailingSpacesValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA116_cli_name_should_equal_id import (
    CliNameMatchIdValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA118_from_to_version_synched import (
    FromToVersionSyncedValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA126_content_item_is_deprecated_correctly import (
    IsDeprecatedCorrectlyValidator,
)

FIELD_WITH_WHITESPACES = "field_with_space_should_fail "


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
def test_IDNameValidator_is_valid(
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
    - Calling the IDNameValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 classifier.
        - Case 3: Should fail anything.
        - Case 4: Should fail anything.
        - Case 5: Should fail anything.
        - Case 6: Should fail the Wizard.
    """
    results = IDNameValidator().is_valid(content_items)
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
        - Make sure the the object name was changed to match the id, and that the right fix msg is returned.
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
def test_CliNameMatchIdValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: content_items with 1 indicator field and 1 incident field.
        - Case 2: content_items with 1 indicator field, where the cliName is different from id.

    When
    - Calling the CliNameMatchIdValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail the indicator field.
    """
    results = CliNameMatchIdValidator().is_valid(content_items)
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
        - Make sure the the object cli name was changed to match the id, and that the right fix msg is returned.
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
def test_IsFromVersionSufficientAllItemsValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: a list of content items with 1 item of each kind supported by the validation where the fromVersion field is valid.
        - Case 2: IncidentField, wizard, playbook, and genericField, all set to fromVersion = 4.5.0 (insufficient).
    When
    - Calling the IsFromVersionSufficientAllItemsValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = IsFromVersionSufficientAllItemsValidator().is_valid(content_items)
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
def test_FromToVersionSyncedValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: a list of content items with 1 item of each kind supported by the validation where the fromVersion < toVersion / toVersion field doesn't exist.
        - Case 2: IncidentType with the fromVersion = toVersion = 5.0.0, IncidentField, Widget, and Wizard, all set to toVersion = 4.5.0 < fromVersion (insufficient).
    When
    - Calling the FromToVersionSyncedValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = FromToVersionSyncedValidator().is_valid(content_items)
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
def test_IsFromVersionSufficientIndicatorFieldValidator_is_valid(
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
    - Calling the IsFromVersionSufficientIndicatorFieldValidator is_valid function.
    Then
        - Make sure the right amount of content_items failed, and that the right error message is returned.
        - Case 1: Shouldn't fail any indicator field.
        - Case 2: Should fail the two indicator fields.
        - Case 3: Should fail the third and fourth indicator fields.
        - Case 4: Should fail the indicator field.
    """
    results = IsFromVersionSufficientIndicatorFieldValidator().is_valid(content_items)
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
        - Make sure the the integration fromversion was raised and that the right message was returned.
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
def test_IsFromVersionSufficientIntegrationValidator_is_valid(
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
    results = IsFromVersionSufficientIntegrationValidator().is_valid(content_items)
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
        - Make sure the the integration fromversion was raised and that the right message was returned.
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
def test_IDContainSlashesValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: A list of one of each content_item supported by the validation with a valid ID.
        - Case 2: A list of one IncidentType, IncidentField, List, and Integration, all with invalid ids with at least one /.
    When
    - Calling the IDContainSlashesValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 4 content items.
    """
    results = IDContainSlashesValidator().is_valid(content_items)
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


def test_IsDeprecatedCorrectlyValidator_is_valid():
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

    results = IsDeprecatedCorrectlyValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        assert result.content_object.deprecated
        assert result.content_object.description == "Some description"


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_filed_error_messages",
    [
        pytest.param(
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
            id="All the content items, no failure expected",
        ),
        pytest.param(
            [
                create_classifier_object(
                    paths=["name", "id"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_integration_object(
                    paths=["name", "commonfields.id"],
                    values=[FIELD_WITH_WHITESPACES, FIELD_WITH_WHITESPACES],
                ),
            ],
            2,
            ["name, id" for _ in range(2)],
            id="classifier and integration with trailing spaces",
        ),
        pytest.param(
            [
                create_indicator_field_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_wizard_object({"name": FIELD_WITH_WHITESPACES}),
                create_correlation_rule_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_incident_type_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_dashboard_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_generic_definition_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_generic_type_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_incident_type_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_generic_module_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_generic_field_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_layout_object(paths=["name"], values=[FIELD_WITH_WHITESPACES]),
                create_incoming_mapper_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_modeling_rule_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_incoming_mapper_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_parsing_rule_object(
                    paths=["name"], values=[FIELD_WITH_WHITESPACES]
                ),
                create_playbook_object(paths=["name"], values=[FIELD_WITH_WHITESPACES]),
            ],
            16,
            ["name" for _ in range(16)],
            id="multiple content items with trailing spaces in name",
        ),
    ],
)
def test_IsContentItemNameContainTrailingSpacesValidator_is_valid(
    content_items: Iterable[ContentTypes113],
    expected_number_of_failures: int,
    expected_filed_error_messages: List[str],
):
    """Test validate BA113 - Trailing spaces in content item name
    Given:
        A list of content items with names that have trailing spaces.
    When:
        The IsContentItemNameContainTrailingSpacesValidator's is_valid method is called.
    Then:
        The validator should return a list of ValidationResult objects, each with a message indicating that the content item's name should not have trailing spaces.
    Test cases:
        - Case 1: All content items are created without trailing spaces in their names. The validator should not return any failures.
        - Case 2: A classifier and an integration are created with trailing spaces in their names. The validator should return two failures, one for each content item.
        - Case 3: Multiple content items are created with trailing spaces in their names. The validator should return a failure for each content item.
    """
    results = IsContentItemNameContainTrailingSpacesValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures

    assert all(
        [
            result.message
            == f"The following fields have a trailing spaces: {expected_field_msg} \nContent item fields can not have trailing spaces."
            for result, expected_field_msg in zip(
                results, expected_filed_error_messages
            )
        ]
    )


@pytest.mark.parametrize(
    "content_item, invalid_fields",
    [
        pytest.param(
            create_integration_object(paths=["name"], values=[FIELD_WITH_WHITESPACES]),
            {"name": "name"},
            id="case integration with trailing spaces in name with fix",
        ),
        pytest.param(
            create_classifier_object(paths=["name"], values=[FIELD_WITH_WHITESPACES]),
            {"name": "name"},
            id="case classifier with trailing spaces in name with fix",
        ),
        pytest.param(
            create_dashboard_object(paths=["name"], values=[FIELD_WITH_WHITESPACES]),
            {"name": "name"},
            id="case dashboard with trailing spaces in name with fix",
        ),
        pytest.param(
            create_incident_type_object(
                paths=["name"], values=[FIELD_WITH_WHITESPACES]
            ),
            {"name": "name"},
            id="case incident type with trailing spaces in name with fix",
        ),
        pytest.param(
            create_wizard_object({"name": FIELD_WITH_WHITESPACES}),
            {"name": "name"},
            id="case wizard with trailing spaces in name with fix",
        ),
        pytest.param(
            create_classifier_object(
                paths=["name", "id"],
                values=[FIELD_WITH_WHITESPACES, FIELD_WITH_WHITESPACES],
            ),
            {"object_id": "id", "name": "name"},
            id="classifier and integration with trailing spaces",
        ),
    ],
)
def test_IsContentItemNameContainTrailingSpacesValidator_fix(
    content_item: ContentTypes113, invalid_fields: dict
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
        - Case 1: An integration is created with trailing spaces in its name. The validator should remove the trailing spaces and return a fix message.
        - Case 2: A classifier is created with trailing spaces in its name. The validator should remove the trailing spaces and return a fix message.
        - Case 3: A dashboard is created with trailing spaces in its name. The validator should remove the trailing spaces and return a fix message.
        - Case 4: An incident type is created with trailing spaces in its name. The validator should remove the trailing spaces and return a fix message.
        - Case 5: A wizard is created with trailing spaces in its name. The validator should remove the trailing spaces and return a fix message.
        - Case 6: A classifier and an integration are created with trailing spaces in their names. The validator should remove the trailing spaces and return a fix message.
    """
    validator = IsContentItemNameContainTrailingSpacesValidator()
    validator.invalid_fields[content_item.name] = list(invalid_fields.keys())
    results = validator.fix(content_item)
    assert (
        results.message
        == f"Removed trailing spaces from the following content item {FIELD_WITH_WHITESPACES.rstrip()} fields: '{', '.join(list(invalid_fields.values()))}'."
    )
    assert content_item.name == FIELD_WITH_WHITESPACES.rstrip()

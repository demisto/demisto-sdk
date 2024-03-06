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
from demisto_sdk.commands.validate.validators.BA_validators.BA100_is_valid_version import (
    IsValidVersionValidator,
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
from demisto_sdk.commands.validate.validators.BA_validators.BA110_is_entity_type_in_entity_name import (
    IsEntityTypeInEntityNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA111_is_entity_name_contain_excluded_word import (
    ERROR_MSG_TEMPLATE,
    IsEntityNameContainExcludedWordValidator,
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
def test_IsValidVersionValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items list.
        - Case 1: A list of one of each content_item supported by the validation with a valid ID.
        - Case 2: A list of one IncidentField, List, and Integration, all with invalid versions.
    When
    - Calling the IsValidVersionValidator is_valid function.
    Then
        - Make sure the right amount of failures return and that the error msg is correct.
        - Case 1: Shouldn't fail anything.
        - Case 2: Should fail all 3 content items.
    """
    results = IsValidVersionValidator().is_valid(content_items)
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
def test_IsEntityTypeInEntityNameValidator_is_valid(content_items, expected_msg):
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
        - Don't fail the validation and is_valid function return empty array.
    """
    result = IsEntityTypeInEntityNameValidator().is_valid(content_items)
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
    results = IsEntityNameContainExcludedWordValidator().is_valid(
        content_items=content_items
    )
    assert len(results) == expected_number_of_failures
    if results:
        assert results[0].message == expected_error_message

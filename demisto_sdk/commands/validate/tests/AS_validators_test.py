import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_pack_object,
    create_playbook_object,
    create_script_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS101_is_valid_autonomous_trigger import (
    IsValidAutonomousTriggerValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS104_source_in_managed_pack import (
    SourceInManagedPackValidator,
)


@pytest.mark.parametrize(
    "grouping_element, is_auto_enabled, managed, source, expected_result_len",
    [
        # Valid cases - should pass
        (
            "Cortex Autonomous Rules",
            True,
            True,
            "autonomous",
            0,
        ),  # Autonomous pack with all correct fields
        (
            "Other Grouping",
            False,
            False,
            None,
            0,
        ),  # Non-autonomous pack, any fields are fine
        (
            "Other Grouping",
            True,
            True,
            "other",
            0,
        ),  # Non-autonomous pack (wrong source)
        (None, False, False, None, 0),  # Non-autonomous pack, no fields set
        (
            "Cortex Autonomous Rules",
            True,
            False,
            "autonomous",
            0,
        ),  # Non-autonomous pack (missing managed)
        (
            "Cortex Autonomous Rules",
            False,
            True,
            "other",
            0,
        ),  # Non-autonomous pack (wrong source)
        # Invalid cases - should fail (autonomous pack without correct fields)
        (
            "Other Grouping",
            True,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with wrong grouping
        (
            "Cortex Autonomous Rules",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with is_auto_enabled=False
        (None, True, True, "autonomous", 1),  # Autonomous pack with no grouping element
        (
            "",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with empty grouping and is_auto_enabled=False
        (
            "Cortex Autonomous Rules",
            None,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with is_auto_enabled missing
        (
            "Other Grouping",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with both fields wrong
        (
            None,
            None,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with both fields missing entirely
    ],
)
def test_IsValidAutonomousTriggerValidator(
    grouping_element, is_auto_enabled, managed, source, expected_result_len
):
    """
    Given:
        - Various combinations of triggers with different grouping_element and is_auto_enabled values
          and pack metadata with different managed/source values.

    When:
        - Running IsValidAutonomousTriggerValidator.obtain_invalid_content_items.

    Then:
        - Triggers in autonomous packs (managed: true AND source: 'autonomous')
          must have grouping_element: 'Cortex Autonomous Rules' AND is_auto_enabled: true.
        - Triggers in non-autonomous packs can have any values for these fields.
    """
    # Create pack with specified metadata
    pack_metadata = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if source is not None:
        pack_metadata["source"] = source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    # Create trigger with specified fields
    trigger_data = {}
    if grouping_element is not None:
        trigger_data["grouping_element"] = grouping_element
    if is_auto_enabled is not None:
        trigger_data["is_auto_enabled"] = is_auto_enabled

    trigger = create_trigger_object(
        paths=list(trigger_data.keys()) if trigger_data else None,
        values=list(trigger_data.values()) if trigger_data else None,
    )

    # Manually set the pack relationship
    trigger.pack = pack

    # Run validation
    invalid_content_items = (
        IsValidAutonomousTriggerValidator().obtain_invalid_content_items([trigger])
    )

    assert len(invalid_content_items) == expected_result_len


def test_IsValidAutonomousTriggerValidator_fix():
    """
    Given:
        - A trigger in an autonomous pack (managed: true, source: 'autonomous')
          but without the correct grouping_element and is_auto_enabled fields.

    When:
        - Running the fix method.

    Then:
        - The trigger's grouping_element should be set to 'Cortex Autonomous Rules'
          and is_auto_enabled should be set to true.
    """
    # Create autonomous pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create trigger without correct fields
    trigger = create_trigger_object(
        paths=["grouping_element", "is_auto_enabled"],
        values=["Other Grouping", False],
    )
    trigger.pack = pack

    # Verify it's invalid before fix
    validator = IsValidAutonomousTriggerValidator()
    invalid_items = validator.obtain_invalid_content_items([trigger])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(trigger)

    # Verify fix was applied
    assert fix_result.message == validator.fix_message
    assert trigger.grouping_element == "Cortex Autonomous Rules"
    assert trigger.is_auto_enabled is True

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([trigger])
    assert len(invalid_items_after_fix) == 0


@pytest.mark.parametrize(
    "content_source, managed, pack_source, expected_result_len",
    [
        # Valid cases - should pass
        ("autonomous", True, "autonomous", 0),  # Managed pack with matching source
        ("partner", True, "partner", 0),  # Managed pack with matching source
        ("", False, "autonomous", 0),  # Non-managed pack, source doesn't matter
        ("wrong", False, "autonomous", 0),  # Non-managed pack, source doesn't matter
        ("", False, "", 0),  # Non-managed pack, no source
        # Invalid cases - should fail
        ("", True, "autonomous", 1),  # Managed pack, missing source on content item
        ("partner", True, "autonomous", 1),  # Managed pack, mismatched source
        ("autonomous", True, "partner", 1),  # Managed pack, mismatched source
    ],
)
def test_SourceInManagedPackValidator_integration(
    content_source, managed, pack_source, expected_result_len
):
    """
    Given:
        - Various combinations of integrations with different source values
          and pack metadata with different managed/source values.

    When:
        - Running SourceInManagedPackValidator.obtain_invalid_content_items.

    Then:
        - Content items in managed packs (managed: true) must have a source field
          that matches the source in pack_metadata.
        - Content items in non-managed packs can have any source value.
    """
    # Create pack with specified metadata
    pack_metadata = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if pack_source is not None:
        pack_metadata["source"] = pack_source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    # Create integration with specified source
    integration = create_integration_object(
        paths=["source"] if content_source is not None else [],
        values=[content_source] if content_source is not None else [],
    )

    # Manually set the pack relationship
    integration.pack = pack

    # Run validation
    invalid_content_items = SourceInManagedPackValidator().obtain_invalid_content_items(
        [integration]
    )

    assert len(invalid_content_items) == expected_result_len


@pytest.mark.parametrize(
    "content_type_factory",
    [
        create_integration_object,
        create_script_object,
        create_playbook_object,
    ],
)
def test_SourceInManagedPackValidator_multiple_content_types(content_type_factory):
    """
    Given:
        - Different content types (Integration, Script, Playbook) in a managed pack
          without the correct source field.

    When:
        - Running SourceInManagedPackValidator.obtain_invalid_content_items.

    Then:
        - All content types should be validated for the source field.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create content item without source
    content_item = content_type_factory(paths=[], values=[])
    content_item.pack = pack

    # Run validation
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([content_item])

    # Should be invalid (missing source)
    assert len(invalid_items) == 1


def test_SourceInManagedPackValidator_fix():
    """
    Given:
        - An integration in a managed pack (managed: true, source: 'autonomous')
          but without the correct source field.

    When:
        - Running the fix method.

    Then:
        - The integration's source should be set to match the pack metadata source.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create integration without source
    integration = create_integration_object(paths=["source"], values=[""])
    integration.pack = pack

    # Verify it's invalid before fix
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([integration])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(integration)

    # Verify fix was applied
    assert "autonomous" in fix_result.message
    assert integration.source == "autonomous"

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([integration])
    assert len(invalid_items_after_fix) == 0


def test_SourceInManagedPackValidator_fix_mismatched_source():
    """
    Given:
        - A script in a managed pack with a mismatched source field.

    When:
        - Running the fix method.

    Then:
        - The script's source should be updated to match the pack metadata source.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "partner"],
    )

    # Create script with wrong source
    script = create_script_object(paths=["source"], values=["autonomous"])
    script.pack = pack

    # Verify it's invalid before fix
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([script])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(script)

    # Verify fix was applied
    assert "partner" in fix_result.message
    assert script.source == "partner"

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([script])
    assert len(invalid_items_after_fix) == 0

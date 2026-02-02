import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS101_is_valid_autonomous_trigger import (
    IsValidAutonomousTriggerValidator,
)


@pytest.mark.parametrize(
    "grouping_element, is_auto_enabled, managed, source, expected_result_len",
    [
        # Valid cases - should pass
        ("Cortex Autonomous Rules", True, True, "autonomous", 0),  # Autonomous pack with all correct fields
        ("Other Grouping", False, False, None, 0),  # Non-autonomous pack, any fields are fine
        ("Other Grouping", True, True, "other", 0),  # Non-autonomous pack (wrong source)
        (None, False, False, None, 0),  # Non-autonomous pack, no fields set
        ("Cortex Autonomous Rules", True, False, "autonomous", 0),  # Non-autonomous pack (missing managed)
        ("Cortex Autonomous Rules", False, True, "other", 0),  # Non-autonomous pack (wrong source)
        
        # Invalid cases - should fail (autonomous pack without correct fields)
        ("Other Grouping", True, True, "autonomous", 1),  # Autonomous pack with wrong grouping
        ("Cortex Autonomous Rules", False, True, "autonomous", 1),  # Autonomous pack with is_auto_enabled=False
        (None, True, True, "autonomous", 1),  # Autonomous pack with no grouping element
        ("", False, True, "autonomous", 1),  # Autonomous pack with empty grouping and is_auto_enabled=False
        ("Cortex Autonomous Rules", None, True, "autonomous", 1),  # Autonomous pack with is_auto_enabled missing
        ("Other Grouping", False, True, "autonomous", 1),  # Autonomous pack with both fields wrong
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
    
    pack = create_pack_object(paths=list(pack_metadata.keys()), values=list(pack_metadata.values()))
    
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
    invalid_content_items = IsValidAutonomousTriggerValidator().obtain_invalid_content_items(
        [trigger]
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
    assert trigger.data.get("grouping_element") == "Cortex Autonomous Rules"
    assert trigger.data.get("is_auto_enabled") is True
    
    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([trigger])
    assert len(invalid_items_after_fix) == 0

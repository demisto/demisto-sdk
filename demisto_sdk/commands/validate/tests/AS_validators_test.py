from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import UnknownContent
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
    create_playbook_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS101_is_valid_autonomous_trigger import (
    IsValidAutonomousTriggerValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS102_is_valid_autonomous_playbook_dependencies_all_files import (
    IsValidAutonomousPlaybookDependenciesValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS102_is_valid_autonomous_playbook_dependencies_list_files import (
    IsValidAutonomousPlaybookDependenciesValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator


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


# --- AS102 Tests ---


def _create_playbook_with_uses(
    playbook_name: str,
    dependency_names: list[str],
) -> Playbook:
    """Helper to create a Playbook object with pre-populated USES relationships.

    The returned playbook has its relationships_data[RelationshipType.USES] set
    to contain RelationshipData entries pointing to BaseNode stubs whose
    object_id matches each name in *dependency_names*.

    Args:
        playbook_name: The name / object_id of the playbook.
        dependency_names: Names of the (invalid) dependencies to attach.

    Returns:
        A Playbook instance ready for the validator to inspect.
    """
    playbook = create_playbook_object(paths=["name"], values=[playbook_name])

    relationships: defaultdict[RelationshipType, set[RelationshipData]] = defaultdict(
        set
    )

    for idx, dep_name in enumerate(dependency_names):
        # Use UnknownContent as a lightweight BaseNode stub for the dependency target.
        target_id = f"db-{dep_name}-{idx}"
        dep_node = UnknownContent(
            object_id=dep_name,
            name=dep_name,
            database_id=target_id,
        )

        rel = RelationshipData(
            relationship_type=RelationshipType.USES,
            source_id=f"db-{playbook_name}",
            target_id=target_id,
            content_item_to=dep_node,
        )
        relationships[RelationshipType.USES].add(rel)

    playbook.relationships_data = relationships
    return playbook


def test_autonomous_playbook_with_invalid_script_dependency(mocker):
    """
    Given:
        - A playbook in an autonomous pack that uses a script from a regular (non-core,
          non-autonomous) pack.

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorAllFiles
          .obtain_invalid_content_items.

    Then:
        - One validation result is returned.
        - The error message contains the invalid script dependency name.
    """
    playbook = _create_playbook_with_uses("AutoPlaybook", ["RegularPackScript"])

    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = [
        playbook
    ]
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorAllFiles()
    results = validator.obtain_invalid_content_items([])

    assert len(results) == 1
    assert "RegularPackScript" in results[0].message
    assert "AutoPlaybook" in results[0].message


def test_autonomous_playbook_with_invalid_subplaybook_dependency(mocker):
    """
    Given:
        - A playbook in an autonomous pack that uses a sub-playbook from a regular pack.

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorListFiles
          .obtain_invalid_content_items.

    Then:
        - One validation result is returned.
        - The error message contains the invalid sub-playbook dependency name.
    """
    playbook = _create_playbook_with_uses("AutoPlaybook", ["RegularSubPlaybook"])

    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = [
        playbook
    ]
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )
    # Mock CONTENT_PATH so that path.relative_to(CONTENT_PATH) works for temp paths.
    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.CONTENT_PATH",
        playbook.path.parent.parent.parent,
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorListFiles()
    results = validator.obtain_invalid_content_items([playbook])

    assert len(results) == 1
    assert "RegularSubPlaybook" in results[0].message
    assert "AutoPlaybook" in results[0].message


def test_autonomous_playbook_with_valid_dependencies_only(mocker):
    """
    Given:
        - A playbook in an autonomous pack whose dependencies are all from core packs
          or other autonomous packs (the graph query returns an empty list).

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorAllFiles
          .obtain_invalid_content_items.

    Then:
        - No validation results are returned.
    """
    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = []
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorAllFiles()
    results = validator.obtain_invalid_content_items([])

    assert len(results) == 0


def test_non_autonomous_playbook_not_checked(mocker):
    """
    Given:
        - A playbook in a non-autonomous pack (the Cypher query filters it out,
          so the graph returns an empty list).

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorListFiles
          .obtain_invalid_content_items.

    Then:
        - No validation results are returned.
    """
    playbook = create_playbook_object()

    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = []
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )
    # Mock CONTENT_PATH so that path.relative_to(CONTENT_PATH) works for temp paths.
    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.CONTENT_PATH",
        playbook.path.parent.parent.parent,
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorListFiles()
    results = validator.obtain_invalid_content_items([playbook])

    assert len(results) == 0


def test_autonomous_playbook_with_multiple_invalid_dependencies(mocker):
    """
    Given:
        - A playbook in an autonomous pack that uses multiple scripts/sub-playbooks
          from regular (non-core, non-autonomous) packs.

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorAllFiles
          .obtain_invalid_content_items.

    Then:
        - Exactly one validation result is returned (one per playbook, not per dependency).
        - The error message lists all invalid dependency names.
    """
    playbook = _create_playbook_with_uses(
        "AutoPlaybook",
        ["RegularScript1", "RegularSubPlaybook2", "RegularScript3"],
    )

    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = [
        playbook
    ]
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorAllFiles()
    results = validator.obtain_invalid_content_items([])

    assert len(results) == 1
    assert "AutoPlaybook" in results[0].message
    assert "RegularScript1" in results[0].message
    assert "RegularSubPlaybook2" in results[0].message
    assert "RegularScript3" in results[0].message


def test_autonomous_playbook_with_command_dependency_allowed(mocker):
    """
    Given:
        - A playbook in an autonomous pack that uses commands from integrations
          (commands are NOT flagged by the Cypher query, so the graph returns
          an empty list).

    When:
        - Running IsValidAutonomousPlaybookDependenciesValidatorAllFiles
          .obtain_invalid_content_items.

    Then:
        - No validation results are returned.
    """
    mock_graph = MagicMock()
    mock_graph.find_autonomous_playbooks_with_invalid_dependencies.return_value = []
    BaseValidator.graph_interface = mock_graph

    mocker.patch(
        "demisto_sdk.commands.validate.validators.AS_validators"
        ".AS102_is_valid_autonomous_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )

    validator = IsValidAutonomousPlaybookDependenciesValidatorAllFiles()
    results = validator.obtain_invalid_content_items([])

    assert len(results) == 0

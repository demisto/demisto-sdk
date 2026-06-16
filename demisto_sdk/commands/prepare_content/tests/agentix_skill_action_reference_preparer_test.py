from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.prepare_content.preparers.agentix_skill_action_reference_preparer import (
    AgentixSkillActionReferencePreparer,
)


def _action_relationship(object_id: str, name: str):
    """Builds a mock skill->action USES relationship.

    Sets a different ``display_name`` from ``name`` to prove the preparer uses
    the action ``name`` (not the display name) for the rewrite.
    """
    node = MagicMock()
    node.content_type = ContentType.AGENTIX_ACTION
    node.object_id = object_id
    node.name = name
    node.display_name = f"Display {name}"
    relationship = MagicMock()
    relationship.content_item_to = node
    return relationship


def _skill_mock(object_id: str, uses):
    skill = MagicMock()
    skill.object_id = object_id
    skill.uses = uses
    return skill


def test_prepare_rewrites_token_keeping_wrapper():
    """
    Given
    - A skill whose body references an action via '<action=action-a>', and the
      action 'action-a' resolves to name 'ActionA' in the graph.

    When
    - Running AgentixSkillActionReferencePreparer.prepare.

    Then
    - The token is rewritten to '<action=ActionA>' (the wrapper is kept, only the
      id is replaced with the action name, not the display name).
    """
    skill = _skill_mock("my-skill", uses=[_action_relationship("action-a", "ActionA")])
    data = {"content": "Use <action=action-a> to do the thing."}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "Use <action=ActionA> to do the thing."


def test_prepare_rewrites_multiple_tokens():
    """
    Given
    - A skill body referencing two different actions.

    When
    - Running the preparer.

    Then
    - Both tokens are rewritten to '<action=<action-name>>'.
    """
    skill = _skill_mock(
        "my-skill",
        uses=[
            _action_relationship("action-a", "ActionA"),
            _action_relationship("action-b", "ActionB"),
        ],
    )
    data = {"content": "First <action=action-a> then <action=action-b>."}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "First <action=ActionA> then <action=ActionB>."


def test_prepare_raises_on_unresolved_token():
    """
    Given
    - A skill body referencing an action id that does not resolve in the graph.

    When
    - Running the preparer.

    Then
    - A ValueError is raised, and its message names the skill and the unresolved
      action id.
    """
    skill = _skill_mock("my-skill", uses=[])
    data = {"content": "Use <action=missing-action> here."}

    with pytest.raises(ValueError) as exc_info:
        AgentixSkillActionReferencePreparer.prepare(skill, data)

    message = str(exc_info.value)
    assert "missing-action" in message
    assert "my-skill" in message


def test_prepare_raises_listing_all_unresolved_tokens():
    """
    Given
    - A skill body referencing several action ids, none of which resolve, plus
      one resolvable action.

    When
    - Running the preparer.

    Then
    - A single ValueError is raised listing every unresolved action id, while the
      resolvable one is not reported.
    """
    skill = _skill_mock(
        "my-skill", uses=[_action_relationship("action-a", "ActionA")]
    )
    data = {
        "content": (
            "Use <action=action-a>, <action=missing-one> and <action=missing-two>."
        )
    }

    with pytest.raises(ValueError) as exc_info:
        AgentixSkillActionReferencePreparer.prepare(skill, data)

    message = str(exc_info.value)
    assert "missing-one" in message
    assert "missing-two" in message
    assert "action-a" not in message


def test_prepare_no_content_is_noop():
    """
    Given
    - A data dict with empty content.

    When
    - Running the preparer.

    Then
    - The data is returned unchanged.
    """
    skill = _skill_mock("my-skill", uses=[_action_relationship("action-a", "ActionA")])
    data: dict = {"content": ""}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result == {"content": ""}

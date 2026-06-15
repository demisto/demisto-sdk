from unittest.mock import MagicMock

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.prepare_content.preparers.agentix_skill_action_reference_preparer import (
    AgentixSkillActionReferencePreparer,
)


def _action_relationship(object_id: str, display_name: str):
    """Builds a mock skill->action USES relationship."""
    node = MagicMock()
    node.content_type = ContentType.AGENTIX_ACTION
    node.object_id = object_id
    node.display_name = display_name
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
      action 'action-a' resolves to display name 'Action A' in the graph.

    When
    - Running AgentixSkillActionReferencePreparer.prepare.

    Then
    - The token is rewritten to '<action=Action A>' (the wrapper is kept, only the
      id is replaced with the display name).
    """
    skill = _skill_mock(
        "my-skill", uses=[_action_relationship("action-a", "Action A")]
    )
    data = {"content": "Use <action=action-a> to do the thing."}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "Use <action=Action A> to do the thing."


def test_prepare_rewrites_multiple_tokens():
    """
    Given
    - A skill body referencing two different actions.

    When
    - Running the preparer.

    Then
    - Both tokens are rewritten to '<action=<display-name>>'.
    """
    skill = _skill_mock(
        "my-skill",
        uses=[
            _action_relationship("action-a", "Action A"),
            _action_relationship("action-b", "Action B"),
        ],
    )
    data = {"content": "First <action=action-a> then <action=action-b>."}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "First <action=Action A> then <action=Action B>."


def test_prepare_leaves_unresolved_token_unchanged():
    """
    Given
    - A skill body referencing an action id that does not resolve in the graph.

    When
    - Running the preparer.

    Then
    - The original '<action=...>' token is left unchanged.
    """
    skill = _skill_mock("my-skill", uses=[])
    data = {"content": "Use <action=missing-action> here."}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "Use <action=missing-action> here."


def test_prepare_no_content_is_noop():
    """
    Given
    - A data dict with empty content.

    When
    - Running the preparer.

    Then
    - The data is returned unchanged.
    """
    skill = _skill_mock(
        "my-skill", uses=[_action_relationship("action-a", "Action A")]
    )
    data: dict = {"content": ""}

    result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result == {"content": ""}

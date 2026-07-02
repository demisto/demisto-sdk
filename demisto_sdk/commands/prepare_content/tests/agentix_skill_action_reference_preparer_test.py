from unittest.mock import MagicMock

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


def test_prepare_warns_on_unresolved_token(caplog):
    """
    Given
    - A skill body referencing an action id that does not resolve in the graph.

    When
    - Running the preparer.

    Then
    - No error is raised, the unresolved token is left unchanged, and a warning is
      logged naming the skill and the unresolved action id.
    """
    skill = _skill_mock("my-skill", uses=[])
    data = {"content": "Use <action=missing-action> here."}

    with caplog.at_level("WARNING"):
        result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == "Use <action=missing-action> here."
    assert "missing-action" in caplog.text
    assert "my-skill" in caplog.text


def test_prepare_warns_listing_all_unresolved_tokens(caplog):
    """
    Given
    - A skill body referencing several action ids, none of which resolve, plus
      one resolvable action.

    When
    - Running the preparer.

    Then
    - No error is raised, the resolvable token is rewritten, the unresolved tokens
      are left unchanged, and a single warning lists every unresolved action id
      while the resolvable one is not reported.
    """
    skill = _skill_mock("my-skill", uses=[_action_relationship("action-a", "ActionA")])
    data = {
        "content": (
            "Use <action=action-a>, <action=missing-one> and <action=missing-two>."
        )
    }

    with caplog.at_level("WARNING"):
        result = AgentixSkillActionReferencePreparer.prepare(skill, data)

    assert result["content"] == (
        "Use <action=ActionA>, <action=missing-one> and <action=missing-two>."
    )
    assert "missing-one" in caplog.text
    assert "missing-two" in caplog.text
    assert "action-a" not in caplog.text


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

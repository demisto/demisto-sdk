from demisto_sdk.commands.validate.tests.test_tools import (
    create_agentix_skill_object,
)


def test_resolve_action_tags_replaces_with_names(mocker):
    """
    Given:
        - An agentix skill and a graph-resolved action id->name map.
    When:
        - Resolving the action tags in a body referencing those actions.
    Then:
        - Each '<action: action-id>' tag is replaced with the action name.
    """
    skill = create_agentix_skill_object(skill_name="skill_with_actions")
    mocker.patch.object(
        type(skill),
        "_action_id_to_name",
        return_value={
            "first-action": "First Action",
            "second-action": "Second Action",
        },
    )

    resolved = skill._resolve_action_tags(
        "Run <action: first-action> then <action:second-action>."
    )

    assert resolved == "Run First Action then Second Action."


def test_resolve_action_tags_leaves_unresolved(mocker):
    """
    Given:
        - An agentix skill whose action id cannot be resolved (empty map, e.g.
          not prepared with --graph).
    When:
        - Resolving the action tags in the body.
    Then:
        - The original '<action: action-id>' tag is left untouched.
    """
    skill = create_agentix_skill_object(skill_name="skill_unresolved_action")
    mocker.patch.object(type(skill), "_action_id_to_name", return_value={})

    resolved = skill._resolve_action_tags("Use <action: missing-action> here.")

    assert resolved == "Use <action: missing-action> here."


def test_resolve_action_tags_no_tags_passthrough(mocker):
    """
    Given:
        - An agentix skill body with no action tags.
    When:
        - Resolving the action tags.
    Then:
        - The body is returned unchanged.
    """
    skill = create_agentix_skill_object(skill_name="skill_plain")
    mocker.patch.object(type(skill), "_action_id_to_name", return_value={})

    resolved = skill._resolve_action_tags("A plain skill body.")

    assert resolved == "A plain skill body."

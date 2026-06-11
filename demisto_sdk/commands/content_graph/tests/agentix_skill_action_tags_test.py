import pytest

from demisto_sdk.commands.content_graph.objects.agentix_skill_action_tags import (
    extract_action_ids,
    replace_action_tags,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        # No tags.
        ("Some plain skill body without tags.", []),
        ("", []),
        # Single tag, no whitespace.
        ("Use <action=my-action-id> here.", ["my-action-id"]),
        # Single tag, whitespace around the equals sign.
        ("Use <action = my-action-id> here.", ["my-action-id"]),
        # Flexible whitespace around tokens.
        ("Use <  action =  my-action-id  > here.", ["my-action-id"]),
        # Multiple distinct tags, order preserved.
        (
            "First <action= a-one> then <action=b-two>.",
            ["a-one", "b-two"],
        ),
        # Duplicates de-duplicated, first-appearance order kept.
        (
            "<action= dup> and again <action= dup> and <action= other>.",
            ["dup", "other"],
        ),
        # Dotted/underscored ids.
        ("<action= name.with.dots_and_under>", ["name.with.dots_and_under"]),
    ],
)
def test_extract_action_ids(text, expected):
    """
    Given a skill body with zero or more ``<action=action-id>`` tags.
    When extracting action-ids.
    Then the de-duplicated, order-preserving list of ids is returned.
    """
    assert extract_action_ids(text) == expected


def test_replace_action_tags_replaces_with_resolver_output():
    """
    Given a body with action tags and a resolver returning the action name.
    When replacing the tags.
    Then each tag is swapped for the resolver's plain-text output.
    """
    text = "Run <action= my-action-id> and <action=other-id> now."
    names = {"my-action-id": "My Action Name", "other-id": "Other Action"}

    result = replace_action_tags(text, lambda action_id: names[action_id])

    assert result == "Run My Action Name and Other Action now."


def test_replace_action_tags_resolver_can_keep_unresolved():
    """
    Given a resolver that returns the original tag for unknown ids.
    When replacing the tags.
    Then unresolved tags are left untouched while resolved ones are swapped.
    """
    text = "Known <action= known> unknown <action= missing>."

    def resolver(action_id: str) -> str:
        if action_id == "known":
            return "Known Name"
        return f"<action={action_id}>"

    result = replace_action_tags(text, resolver)

    assert result == "Known Known Name unknown <action=missing>."


def test_replace_action_tags_empty_text():
    """
    Given empty text.
    When replacing the tags.
    Then the empty text is returned unchanged and the resolver is not called.
    """
    calls = []

    def resolver(action_id: str) -> str:
        calls.append(action_id)
        return action_id

    assert replace_action_tags("", resolver) == ""
    assert calls == []

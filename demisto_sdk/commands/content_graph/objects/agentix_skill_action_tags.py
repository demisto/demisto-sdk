"""Helpers for the AgentixSkill ``<action: action-id>`` tag feature.

An AgentixSkill body (``<SkillName>_skill.md``) may reference other Agentix
actions inline using a tag of the form ``<action: action-id>``. The whitespace
after the colon is flexible, so both ``<action:my-action-id>`` and
``<action: my-action-id>`` are recognized.

Two behaviors are derived from these tags:

* During content-graph parsing, every referenced ``action-id`` becomes an
  (optional) dependency of the skill.
* During ``prepare-content``/upload, each tag is replaced with the resolved
  action **name** (e.g. ``<action: my-action-id>`` -> ``My Action Name``).
"""

import re
from typing import Callable, List

# Matches ``<action: action-id>`` with flexible surrounding whitespace.
# The captured group is the action-id (word characters, hyphens, dots).
ACTION_TAG_PATTERN = re.compile(r"<\s*action\s*:\s*([\w.\-]+)\s*>")


def extract_action_ids(text: str) -> List[str]:
    """Return the de-duplicated, order-preserving list of action-ids in ``text``.

    Args:
        text: The skill body (Markdown) to scan.

    Returns:
        The action-ids referenced via ``<action: action-id>`` tags, in first
        appearance order, without duplicates.
    """
    if not text:
        return []
    seen: set[str] = set()
    ordered: List[str] = []
    for match in ACTION_TAG_PATTERN.finditer(text):
        action_id = match.group(1)
        if action_id not in seen:
            seen.add(action_id)
            ordered.append(action_id)
    return ordered


def replace_action_tags(text: str, resolver: Callable[[str], str]) -> str:
    """Replace each ``<action: action-id>`` tag using ``resolver``.

    Args:
        text: The skill body (Markdown) to transform.
        resolver: A callable mapping an action-id to the replacement text. To
            leave a tag unchanged, the resolver may return the original tag.

    Returns:
        The text with every recognized tag replaced by ``resolver(action_id)``.
    """
    if not text:
        return text

    def _sub(match: "re.Match[str]") -> str:
        return resolver(match.group(1))

    return ACTION_TAG_PATTERN.sub(_sub, text)

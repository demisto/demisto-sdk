import re
from typing import TYPE_CHECKING, Dict

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    ACTION_REFERENCE_REGEX,
)

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class AgentixSkillActionReferencePreparer:
    """Rewrites ``<action=action-id>`` phrase in a skill body to ``<action=action-name>``.

    A skill's Markdown body (the ``content`` field) may reference actions via
    ``<action=action-id>`` tokens. During prepare-upload, the action id inside
    each token is replaced with the corresponding action's ``name`` (resolved
    through the content graph via ``content_item.uses`` by the action's id), while
    the ``<action=...>`` wrapper is kept — producing ``<action=action-name>``.
    """

    @staticmethod
    def prepare(content_item: "ContentItem", data: dict) -> dict:
        """Rewrite action-reference tokens in ``data["content"]`` to use action names.

        Each ``<action=action-id>`` token is rewritten to ``<action=action-name>``,
        keeping the wrapper and only substituting the resolved action ``name``.

        Args:
            content_item: The skill content item, used to resolve action
                dependencies via ``content_item.uses``.
            data: The metadata dict whose ``content`` field holds the skill body.

        Returns:
            The (possibly modified) ``data`` dict. Tokens whose action id cannot
            be resolved (e.g. the graph is not populated, or no matching action
            node exists) are left unchanged.
        """
        content = data.get("content")
        if not content:
            return data

        id_to_name = AgentixSkillActionReferencePreparer._build_action_name_map(
            content_item
        )

        unresolved: list[str] = []

        def _replace(match: "re.Match") -> str:
            action_id = match.group(1).strip()
            action_name = id_to_name.get(action_id)
            if action_name is None:
                if action_id not in unresolved:
                    unresolved.append(action_id)

                return match.group(0)
            return f"<action={action_name}>"

        data["content"] = ACTION_REFERENCE_REGEX.sub(_replace, content)

        if unresolved:
            logger.warning(
                f"Could not find the following action id(s) referenced in skill "
                f"'{content_item.object_id}': {', '.join(sorted(unresolved))}. "
                f"Ensure each referenced action exists and is a dependency of the skill."
            )

        return data

    @staticmethod
    def _build_action_name_map(
        skill: "ContentItem",
    ) -> Dict[str, str]:
        """Builds an ``action id -> action name`` map from the skill's dependencies.

        Filters ``skill.uses`` to ``AGENTIX_ACTION`` targets and maps each
        target node's ``object_id`` to its ``name``. If the graph is not
        populated, ``uses`` is empty and an empty map is returned.
        """
        id_to_name: Dict[str, str] = {}
        for relationship in skill.uses:
            node = relationship.content_item_to
            if node.content_type == ContentType.AGENTIX_ACTION:
                id_to_name[node.object_id] = node.name  # type: ignore[attr-defined]
        if not id_to_name:
            logger.debug(
                f"No AgentixAction dependencies resolved for skill "
                f"'{skill.object_id}'; action-reference tokens (if any) "
                f"will be left unchanged."
            )
        return id_to_name

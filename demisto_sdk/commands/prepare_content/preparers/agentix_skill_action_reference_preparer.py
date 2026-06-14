import re
from typing import TYPE_CHECKING, Dict

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

# Matches ``<action=action-id>`` tokens in a skill's Markdown body.
ACTION_REFERENCE_REGEX = re.compile(r"<action=([^>]+)>")


class AgentixSkillActionReferencePreparer:
    """Replaces ``<action=action-id>`` tokens in a skill body with action display names.

    A skill's Markdown body (the ``content`` field) may reference actions via
    ``<action=action-id>`` tokens. During prepare-upload, each token is replaced
    with the corresponding action's display name, resolved through the content
    graph (``content_item.uses``) by the action's id.
    """

    @staticmethod
    def prepare(content_item: "ContentItem", data: dict) -> dict:
        """Replace action-reference tokens in ``data["content"]`` with display names.

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

        id_to_display_name = (
            AgentixSkillActionReferencePreparer._build_action_display_name_map(
                content_item
            )
        )

        def _replace(match: "re.Match") -> str:
            action_id = match.group(1).strip()
            display_name = id_to_display_name.get(action_id)
            if display_name is None:
                logger.warning(
                    f"Could not resolve action id '{action_id}' referenced in skill "
                    f"'{content_item.object_id}'; leaving token '{match.group(0)}' "
                    f"unchanged."
                )
                return match.group(0)
            return display_name

        data["content"] = ACTION_REFERENCE_REGEX.sub(_replace, content)
        return data

    @staticmethod
    def _build_action_display_name_map(
        content_item: "ContentItem",
    ) -> Dict[str, str]:
        """Builds an ``action id -> display name`` map from the skill's dependencies.

        Filters ``content_item.uses`` to ``AGENTIX_ACTION`` targets and maps each
        target node's ``object_id`` to its ``display_name``. If the graph is not
        populated, ``uses`` is empty and an empty map is returned.
        """
        id_to_display_name: Dict[str, str] = {}
        for relationship in content_item.uses:
            node = relationship.content_item_to
            if node.content_type == ContentType.AGENTIX_ACTION:
                id_to_display_name[node.object_id] = node.display_name  # type: ignore[attr-defined]
        if not id_to_display_name:
            logger.debug(
                f"No AgentixAction dependencies resolved for skill "
                f"'{content_item.object_id}'; action-reference tokens (if any) "
                f"will be left unchanged."
            )
        return id_to_display_name

from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEFAULT_AGENTIX_ITEM_FROM_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_skill import (
    StrictAgentixSkill,
)
from demisto_sdk.commands.prepare_content.agentix_skill_unifier import (
    AgentixSkillUnifier,
)


class AgentixSkillParser(JSONContentItemParser, content_type=ContentType.AGENTIX_SKILL):
    """Parser for AgentixSkill content items.

    An AgentixSkill lives at ``Packs/<PackName>/AgentixSkills/<SkillName>/`` with
    two files:

    * ``metadata.json`` — the schema fields (id, name, display, description,
      fromversion, toversion, internal, supportedModules)
    * ``skill.md`` — the skill body (Markdown), merged into the ``content`` field
      during ``prepare-content``.
    """

    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        self.display: Optional[str] = self.json_data.get("display")
        self.internal: bool = self.json_data.get("internal", False)

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "id",
                "name": "name",
                "display": "display",
                "description": "description",
                "fromversion": "fromversion",
                "toversion": "toversion",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        return (
            get_value(self.json_data, self.field_mapping.get("display", ""))
            or self.name
            or self.object_id
        )

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {MarketplaceVersions.PLATFORM}

    @property
    def fromversion(self) -> str:
        return str(
            get_value(
                self.json_data,
                self.field_mapping.get("fromversion", ""),
                DEFAULT_AGENTIX_ITEM_FROM_VERSION,
            )
        )

    @property
    def content(self) -> str:
        """Get the skill body (Markdown).

        The body is read from a separate ``skill.md`` file located in the same
        directory as ``metadata.json``.
        """
        if not self.git_sha:
            return AgentixSkillUnifier.get_skill_content(self.path.parent)
        return AgentixSkillUnifier.get_skill_content_with_sha(self.path, self.git_sha)

    @property
    def strict_object(self):
        return StrictAgentixSkill

from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import (
    AgentixBaseParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_skill import (
    StrictAgentixSkill,
)
from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    AGENTIX_SKILL_FILE_SUFFIX,
    AgentixMarkdownUnifier,
)


class AgentixSkillParser(AgentixBaseParser, content_type=ContentType.AGENTIX_SKILL):
    """Parser for AgentixSkill content items.

    An AgentixSkill lives at ``Packs/<PackName>/AgentixSkills/<SkillName>/`` with
    two files:

    * ``<SkillName>.yml`` — the schema fields authored as YAML, using a nested
      ``commonfields: {id, version}`` block (symmetric with ``AgentixAgent``)
      plus top-level ``name``, ``description``, ``fromversion``, ``toversion``,
      ``internal``, ``supportedModules``. ``name`` is the human-readable
      Title Case label (no separate ``display`` field). The schema file shares
      the folder name, like most YAML content items (including ``AgentixAgent``).
    * ``<SkillName>_skill.md`` — the skill body (Markdown), merged into the
      ``content`` field during ``prepare-content``.
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
        self.internal: bool = self.yml_data.get("internal", False)

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "description": "description",
            }
        )
        return super().field_mapping

    @property
    def display_name(self) -> Optional[str]:
        """For AgentixSkill the ``name`` field is the human-readable Title Case
        label — there is no separate ``display`` field — so we surface ``name``
        as the display name to satisfy the parent ``ContentItem.display_name``.
        """
        return self.name

    @property
    def content(self) -> str:
        """Get the skill body (Markdown).

        The body is read from a separate ``<SkillName>_skill.md`` file located in
        the same directory as ``<SkillName>.yml``.
        """
        if not self.git_sha:
            return AgentixMarkdownUnifier.get_content(
                self.path.parent, file_suffix=AGENTIX_SKILL_FILE_SUFFIX
            )
        return AgentixMarkdownUnifier.get_content_with_sha(
            self.path, self.git_sha, file_suffix=AGENTIX_SKILL_FILE_SUFFIX
        )

    @property
    def strict_object(self):
        return StrictAgentixSkill

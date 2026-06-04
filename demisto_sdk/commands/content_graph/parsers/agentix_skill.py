from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import (
    AgentixBaseParser,
)
from demisto_sdk.commands.content_graph.parsers.content_item import (
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_skill import (
    StrictAgentixSkill,
)
from demisto_sdk.commands.prepare_content.agentix_skill_unifier import (
    AgentixSkillUnifier,
)

# Canonical schema-file name for AgentixSkill packages (see CRTX-251738).
SKILL_METADATA_FILE_NAME = "metadata.yml"


class AgentixSkillParser(AgentixBaseParser, content_type=ContentType.AGENTIX_SKILL):
    """Parser for AgentixSkill content items.

    An AgentixSkill lives at ``Packs/<PackName>/AgentixSkills/<SkillName>/`` with
    two files:

    * ``metadata.yml`` — the schema fields authored as YAML, using a nested
      ``commonfields: {id, version}`` block (symmetric with ``AgentixAgent``)
      plus top-level ``name``, ``display``, ``description``, ``fromversion``,
      ``toversion``, ``internal``, ``supportedModules``.
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
        self.display: Optional[str] = self.yml_data.get("display")
        self.internal: bool = self.yml_data.get("internal", False)

    def get_path_with_suffix(self, suffix: str) -> Path:
        """Resolve the canonical schema-file path for an AgentixSkill.

        AgentixSkill packages use a fixed file name (``metadata.yml``) for the
        schema, regardless of the folder name — unlike most YAML content items
        (including ``AgentixAgent``) whose schema file shares the folder name
        (e.g. ``<Folder>/<Folder>.yml``).

        When the parser receives the package directory we resolve to
        ``<dir>/metadata.yml``; when it receives a file path directly we keep it
        as-is.

        Args:
            suffix: The requested file suffix (always ``".yml"`` for YAML items).

        Returns:
            Path: The path to the skill's ``metadata.yml`` file.

        Raises:
            NotAContentItemException: If the resolved file does not exist.
        """
        if self.path.is_file():
            return self.path

        candidate = self.path / SKILL_METADATA_FILE_NAME
        if not candidate.exists():
            raise NotAContentItemException(
                f"AgentixSkill schema file '{SKILL_METADATA_FILE_NAME}' not found "
                f"in '{self.path}'."
            )
        return candidate

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "display": "display",
                "description": "description",
            }
        )
        return super().field_mapping

    @property
    def content(self) -> str:
        """Get the skill body (Markdown).

        The body is read from a separate ``skill.md`` file located in the same
        directory as ``metadata.yml``.
        """
        if not self.git_sha:
            return AgentixSkillUnifier.get_skill_content(self.path.parent)
        return AgentixSkillUnifier.get_skill_content_with_sha(self.path, self.git_sha)

    @property
    def strict_object(self):
        return StrictAgentixSkill

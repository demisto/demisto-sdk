from functools import cached_property
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import (
    AGENTIX_SKILLS_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers.related_files import (
    SkillContentRelatedFile,
)
from demisto_sdk.commands.prepare_content.agentix_skill_unifier import (
    AgentixSkillUnifier,
)


class AgentixSkill(ContentItem, content_type=ContentType.AGENTIX_SKILL):
    """Represents an AgentixSkill content item.

    Skills live under ``Packs/<PackName>/AgentixSkills/<SkillName>/`` with two
    files: ``metadata.json`` (schema fields) and ``skill.md`` (the body, merged
    into the ``content`` field at upload time).
    """

    display: Optional[str] = None
    internal: bool = False
    content: str = ""
    supportedModules: Optional[list[str]] = None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Match an AgentixSkill ``metadata.json`` file under ``AgentixSkills/``."""
        if path.suffix != ".json":
            return False
        if path.name != "metadata.json":
            return False
        return AGENTIX_SKILLS_DIR in path.parts

    @cached_property
    def skill_content_file(self) -> SkillContentRelatedFile:
        """Accessor for the related ``skill.md`` file."""
        return SkillContentRelatedFile(self.path, git_sha=self.git_sha)

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.PLATFORM,
        **kwargs,
    ) -> dict:
        """Prepare the AgentixSkill for upload by unifying the skill body.

        This method merges the skill body (Markdown) from the sibling
        ``skill.md`` file into the metadata dict's ``content`` field.

        Args:
            current_marketplace: Target marketplace (default: PLATFORM)
            **kwargs: Additional arguments

        Returns:
            Unified metadata dict with the ``content`` field populated from
            ``skill.md``.
        """
        data = super().prepare_for_upload(current_marketplace)
        data = AgentixSkillUnifier.unify(self.path, data, current_marketplace)
        return data

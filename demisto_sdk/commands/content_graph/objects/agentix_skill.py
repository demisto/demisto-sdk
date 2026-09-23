from functools import cached_property
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import (
    AGENTIX_SKILLS_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase
from demisto_sdk.commands.content_graph.parsers.related_files import (
    SkillContentRelatedFile,
)
from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    AGENTIX_SKILL_FILE_SUFFIX,
    AGENTIX_SKILL_TARGET_FIELD,
    AgentixMarkdownUnifier,
)
from demisto_sdk.commands.prepare_content.preparers.agentix_skill_action_reference_preparer import (
    AgentixSkillActionReferencePreparer,
)


class AgentixSkill(AgentixBase, content_type=ContentType.AGENTIX_SKILL):
    """Represents an AgentixSkill content item.

    Skills live under ``Packs/<PackName>/AgentixSkills/<SkillName>/`` with two
    files: ``<SkillName>.yml`` (schema fields, YAML with a nested
    ``commonfields: {id, version}`` block symmetric with ``AgentixAgent``) and
    ``<SkillName>_skill.md`` (the Markdown body, merged into the ``content``
    field at upload time).
    """

    content: str = ""
    supportedModules: Optional[list[str]] = None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Match an AgentixSkill ``<SkillName>.yml`` file under ``AgentixSkills/``."""
        if (
            path.suffix in {".yml", ".yaml"}
            and not path.stem.endswith("_test")
            and AGENTIX_SKILLS_DIR in path.parts
        ):
            return True
        return False

    @cached_property
    def skill_content_file(self) -> SkillContentRelatedFile:
        """Accessor for the related ``<SkillName>_skill.md`` file."""
        return SkillContentRelatedFile(self.path, git_sha=self.git_sha)

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.PLATFORM,
        **kwargs,
    ) -> dict:
        """Prepare the AgentixSkill for upload by unifying the skill body.

        This method merges the skill body (Markdown) from the sibling
        ``<SkillName>_skill.md`` file into the metadata dict's ``content`` field.

        Args:
            current_marketplace: Target marketplace (default: PLATFORM)
            **kwargs: Additional arguments

        Returns:
            Unified metadata dict with the ``content`` field populated from
            ``<SkillName>_skill.md``.
        """
        data = super().prepare_for_upload(current_marketplace)
        data = AgentixMarkdownUnifier.unify(
            self.path,
            data,
            current_marketplace,
            target_field=AGENTIX_SKILL_TARGET_FIELD,
            file_suffix=AGENTIX_SKILL_FILE_SUFFIX,
        )
        data = AgentixSkillActionReferencePreparer.prepare(self, data)
        return data

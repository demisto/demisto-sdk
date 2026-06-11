from functools import cached_property
from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.constants import (
    AGENTIX_SKILLS_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase
from demisto_sdk.commands.content_graph.objects.agentix_skill_action_tags import (
    replace_action_tags,
)
from demisto_sdk.commands.content_graph.parsers.related_files import (
    SkillContentRelatedFile,
)
from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    AGENTIX_SKILL_FILE_SUFFIX,
    AGENTIX_SKILL_TARGET_FIELD,
    AgentixMarkdownUnifier,
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
        if path.suffix not in {".yml", ".yaml"}:
            return False
        if path.stem.endswith("_test"):
            return False
        return AGENTIX_SKILLS_DIR in path.parts

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
        ``<SkillName>_skill.md`` file into the metadata dict's ``content`` field,
        and replaces every ``<action=action-id>`` tag in the body with the
        referenced action's human-readable name.

        The action-id -> action-name mapping is resolved from the content graph
        ``uses`` relationships, which are populated when the skill is loaded with
        the graph (``prepare-content --graph``). When an action-id cannot be
        resolved (e.g. the skill was not enriched with the graph), the original
        ``<action=action-id>`` tag is left untouched and a warning is logged.

        Args:
            current_marketplace: Target marketplace (default: PLATFORM)
            **kwargs: Additional arguments

        Returns:
            Unified metadata dict with the ``content`` field populated from
            ``<SkillName>_skill.md`` and action tags resolved to names.
        """
        data = super().prepare_for_upload(current_marketplace)
        data = AgentixMarkdownUnifier.unify(
            self.path,
            data,
            current_marketplace,
            target_field=AGENTIX_SKILL_TARGET_FIELD,
            file_suffix=AGENTIX_SKILL_FILE_SUFFIX,
        )
        content = data.get(AGENTIX_SKILL_TARGET_FIELD)
        if content:
            data[AGENTIX_SKILL_TARGET_FIELD] = self._resolve_action_tags(content)
        return data

    def _action_id_to_name(self) -> Dict[str, str]:
        """Build an action-id -> action-name map from the graph ``uses`` deps.

        Only AGENTIX_ACTION dependencies are considered. Available when the
        skill was loaded with the content graph.
        """
        from demisto_sdk.commands.content_graph.objects.agentix_action import (
            AgentixAction,
        )

        mapping: Dict[str, str] = {}
        for relationship in self.uses:
            action = relationship.content_item_to
            if isinstance(action, AgentixAction):
                mapping[action.object_id] = action.name
        return mapping

    def _resolve_action_tags(self, content: str) -> str:
        """Replace ``<action=action-id>`` tags with the resolved action name.

        Unresolved ids leave the original tag in place and emit a warning.
        """
        action_names = self._action_id_to_name()

        def resolver(action_id: str) -> str:
            name = action_names.get(action_id)
            if name is None:
                logger.warning(
                    f"AgentixSkill '{self.object_id}': could not resolve action "
                    f"id '{action_id}' to an action name (is the skill prepared "
                    f"with --graph?). Leaving the '<action={action_id}>' tag "
                    f"unchanged."
                )
                return f"<action={action_id}>"
            return name

        return replace_action_tags(content, resolver)

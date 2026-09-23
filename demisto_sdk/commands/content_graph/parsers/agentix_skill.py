from functools import cached_property
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.agentix_base import (
    AgentixBaseParser,
)
from demisto_sdk.commands.content_graph.strict_objects.agentix_skill import (
    StrictAgentixSkill,
)
from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    ACTION_REFERENCE_REGEX,
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
        self.connect_to_dependencies()

    @cached_property
    def field_mapping(self):
        super().field_mapping.update({"display": "name"})
        return super().field_mapping

    def connect_to_dependencies(self) -> None:
        """Registers the actions referenced in the skill body as optional dependencies.

        The skill's Markdown body (``<SkillName>_skill.md``) may contain tokens of
        the form ``<action=action-id>``. Each unique referenced action id is
        registered as an optional (non-mandatory) ``USES_BY_ID`` dependency so
        that, during prepare-upload, the token can be replaced with the action's
        display name. The dependency is non-mandatory (mirroring ``AgentixAgent``)
        so that a reference to an action that does not exist in the repository does
        not surface as a mandatory unresolved dependency during validation.
        """
        try:
            body = self.content
        except Exception as e:
            logger.debug(
                f"Could not read skill body for {self.path} to extract action "
                f"references: {e}"
            )
            return
        if not body:
            return
        for action_id in dict.fromkeys(
            match.group(1).strip() for match in ACTION_REFERENCE_REGEX.finditer(body)
        ):
            if action_id:
                self.add_dependency_by_id(
                    action_id, ContentType.AGENTIX_ACTION, is_mandatory=False
                )

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

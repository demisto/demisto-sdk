from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Optional, cast

from packaging.version import Version

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsActionNameChangedRequiresSkillRNValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR115"
    description = (
        "Validates that when an Agentix Action's 'name' field is changed, every "
        "Agentix Skill that depends on that action (by the action's id) bumps its "
        "version by adding a Release Note."
    )
    rationale = (
        "Skills reference actions by id (via `<action=action-id>` tokens), but the "
        "action's display 'name' is what gets surfaced to users at prepare-upload "
        "time. Changing the action's name therefore changes the behavior of every "
        "dependent skill, so each dependent skill's pack must add a Release Note."
    )
    error_message = (
        "The Agentix Action name was changed from '{old}' to '{new}', but the "
        "dependent skill '{skill}' (pack '{pack}') has no Release Note. "
        "Add a Release Note that bumps the dependent skill's pack version."
    )
    related_field = "name"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        # A name change can only be detected against the previous (git) version
        # of the action, so this validation is a no-op when running on all files.
        if validate_all_files:
            return []

        results: List[ValidationResult] = []
        for content_item in content_items:
            old_name = self.get_old_name_if_changed(content_item)
            if old_name is None:
                continue
            results.extend(self.get_results_for_renamed_action(content_item, old_name))
        return results

    @staticmethod
    def get_old_name_if_changed(content_item: ContentTypes) -> str | None:
        """Return the previous action 'name' if it was changed, otherwise None.

        The change is detected on the action's ``name`` field (the user-facing
        display name), not on its ``object_id`` (``commonfields.id``). Skills
        depend on actions by id, so the id is intentionally left untouched while
        the name change is what requires dependent skills to be re-released.
        """
        old_item = cast(ContentTypes, content_item.old_base_content_object)
        if not old_item:
            return None
        if old_item.name == content_item.name:
            return None
        return old_item.name

    def get_results_for_renamed_action(
        self, content_item: ContentTypes, old_name: str
    ) -> List[ValidationResult]:
        """Find dependent skills missing a version bump for the renamed action.

        The dependent skill is resolved from the graph (via the action's
        ``used_by`` relationship), so it does NOT carry git-status flags - those
        are only populated by the validate initializer on the disk-parsed items
        of the local diff, not on graph nodes. We therefore rely on a pack
        *version comparison* (branch ``currentVersion`` vs. the master baseline)
        as the canonical, repo-agnostic signal that a Release Note was added.
        This single check subsumes both the previous "new skill / new pack" skip
        and the "RN added" check, and works across repositories (e.g. an action
        in ``content`` whose dependent skill lives in ``content-private``).
        """
        results: List[ValidationResult] = []
        for skill in self.get_dependent_skills(content_item):
            if self.was_pack_version_bumped(skill.in_pack):
                logger.debug(
                    f"GR115: dependent skill '{skill.object_id}' "
                    f"(pack '{skill.pack_id}') has a bumped pack version "
                    f"(Release Note present) or is newly created - "
                    f"validation passes for it."
                )
                continue
            logger.debug(
                f"GR115: dependent skill '{skill.object_id}' "
                f"(pack '{skill.pack_id}') is missing a Release Note for the "
                f"renamed action '{content_item.object_id}' - reporting failure."
            )
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        old=old_name,
                        new=content_item.name,
                        skill=skill.object_id,
                        pack=skill.pack_id,
                    ),
                    content_object=content_item,
                )
            )
        return results

    @staticmethod
    def was_pack_version_bumped(pack: Optional[Pack]) -> bool:
        """Return True if the dependent skill's pack version was raised vs. master.

        A raised pack ``currentVersion`` is the canonical, repo-agnostic signal
        that a Release Note was added (every Release Note bumps the pack
        version). This mirrors PA114's version comparison and, unlike the
        previous git-status checks (``is_new_skill``/``is_new_pack``/
        ``was_rn_added``), does NOT rely on git-status flags - which the graph
        layer never populates on dependency nodes. It therefore also works
        across repositories, as long as the pack's master baseline
        (``old_base_content_object``) was parsed.

        Returns True (treated as "satisfied", i.e. no Release Note required)
        when:
        * the pack cannot be resolved (``None``) - to avoid false failures, or
        * there is no master baseline (a brand-new pack/skill needs no bump), or
        * either version is missing.

        Otherwise returns whether the branch version is strictly greater than
        the master version.
        """
        if pack is None:
            return True

        pack_id = getattr(pack, "pack_id", None) or getattr(pack, "object_id", None)
        old_obj = pack.old_base_content_object
        if old_obj is None:
            # No master baseline => brand-new pack/skill => no bump required.
            logger.debug(
                f"GR115.was_pack_version_bumped: pack '{pack_id}' has no master "
                f"baseline (old_base_content_object is None) - treating as a "
                f"brand-new pack, no bump required (returning True)."
            )
            return True

        current_version = pack.current_version
        if not isinstance(old_obj, Pack):
            logger.warning(
                f"GR115.was_pack_version_bumped: pack '{pack_id}' master baseline "
                f"(old_base_content_object) is not a Pack (got "
                f"'{type(old_obj).__name__}') - cannot compare versions, treating "
                f"as no bump required (returning True)."
            )
            return True
        old_version = old_obj.current_version
        if not current_version or not old_version:
            return True

        bumped = Version(old_version) < Version(current_version)
        logger.debug(
            f"GR115.was_pack_version_bumped: pack '{pack_id}' version comparison "
            f"{old_version} < {current_version} => bumped={bumped}."
        )
        return bumped

    def get_dependent_skills(self, content_item: ContentTypes) -> List[AgentixSkill]:
        """Return the Agentix Skills that depend on the given action via the graph.

        ``content_item`` is parsed from disk and therefore has no relationships
        hydrated. We must re-fetch the action node *from the graph* (by its
        ``object_id``) so its incoming ``USES`` relationships (``used_by``) are
        populated before we inspect them.
        """
        skills: dict[str, AgentixSkill] = {}
        # Fetch the action node from the graph so its relationships are loaded.
        graph_actions = self.graph.search(
            content_type=ContentType.AGENTIX_ACTION,
            object_id=content_item.object_id,
        )
        for graph_action in graph_actions:
            # Graph placeholders (e.g. ``UnknownContent``) lack relationship
            # attributes, so skip any node that does not expose ``used_by``.
            used_by = getattr(graph_action, "used_by", None)
            if not used_by:
                continue
            for relationship in used_by:
                skill = relationship.content_item_to
                if isinstance(skill, AgentixSkill):
                    skills[skill.object_id] = skill
        logger.debug(
            f"GR115: found {len(skills)} dependent skills for action "
            f"'{content_item.object_id}'."
        )
        return list(skills.values())

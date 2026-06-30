from __future__ import annotations

from abc import ABC
from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.tools import was_rn_added
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
            results.extend(
                self.get_results_for_renamed_action(content_item, old_name)
            )
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
        """Find dependent skills missing a Release Note for the renamed action."""
        results: List[ValidationResult] = []
        for skill in self.get_dependent_skills(content_item):
            if was_rn_added(skill.pack):
                continue
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

    def get_dependent_skills(
        self, content_item: ContentTypes
    ) -> List[AgentixSkill]:
        """Return the Agentix Skills that depend on the given action via the graph."""
        skills: dict[str, AgentixSkill] = {}
        # Graph placeholders (e.g. ``UnknownContent``) lack relationship
        # attributes, so skip any node that does not expose ``used_by``.
        used_by = getattr(content_item, "used_by", None)
        if used_by:
            for relationship in used_by:
                skill = relationship.content_item_to
                if isinstance(skill, AgentixSkill):
                    skills[skill.object_id] = skill
        logger.info(
            f"GR115: found {len(skills)} dependent skills for action "
            f"'{content_item.object_id}'."
        )
        return list(skills.values())

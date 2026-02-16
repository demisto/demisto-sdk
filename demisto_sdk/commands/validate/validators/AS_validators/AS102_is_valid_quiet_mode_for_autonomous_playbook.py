from __future__ import annotations

from typing import Iterable, List, Tuple, Union

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Playbook]

EXCLUDED_TASK_TYPES = {PlaybookTaskType.START, PlaybookTaskType.TITLE}


class IsValidQuietModeForAutonomousPlaybookValidator(BaseValidator[ContentTypes]):
    error_code = "AS102"
    description = (
        "Validate that tasks without displayLabel in autonomous playbooks have quietmode set to 1."
    )
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), playbook tasks "
        "that do not have a displayLabel must have quietmode: 1 to ensure they run silently."
    )
    error_message = (
        "The playbook is in an autonomous pack (managed: true, source: 'autonomous') "
        "but the following tasks without displayLabel do not have quietmode set to 1: {0}."
    )
    fix_message = "Set quietmode to 1 on all tasks without displayLabel."
    related_field = "quietmode"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = get_invalid_quiet_mode_tasks(content_item)
            if invalid_tasks:
                task_details = ", ".join(
                    f"task '{task_id}' (quietmode={quietmode})"
                    for task_id, quietmode in invalid_tasks
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(task_details),
                        content_object=content_item,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the playbook by setting quietmode to 1 on all tasks without displayLabel
        that currently don't have quietmode set to 1.

        Args:
            content_item: The playbook content item to fix.

        Returns:
            FixResult with the fix message.
        """
        for task_config in content_item.tasks.values():
            if task_config.type in EXCLUDED_TASK_TYPES:
                continue
            if not task_config.displayLabel and task_config.quietmode != 1:
                task_config.quietmode = 1

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def get_invalid_quiet_mode_tasks(
    content_item: ContentTypes,
) -> List[Tuple[str, int | None]]:
    """
    Check if a playbook is in an autonomous pack and has tasks without displayLabel
    that don't have quietmode set to 1.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        A list of tuples (task_id, quietmode) for invalid tasks, or an empty list if valid.
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return []

    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")
    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        return []

    invalid_tasks: List[Tuple[str, int | None]] = []
    for task_id, task_config in content_item.tasks.items():
        if task_config.type in EXCLUDED_TASK_TYPES:
            continue
        if not task_config.displayLabel and task_config.quietmode != 1:
            invalid_tasks.append((task_id, task_config.quietmode))

    return invalid_tasks

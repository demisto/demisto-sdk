from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook

EXCLUDED_TASK_TYPES = {PlaybookTaskType.START, PlaybookTaskType.TITLE}


class WarnQuietModeOnDisplayLabelTaskValidator(BaseValidator[ContentTypes]):
    error_code = "AS106"
    description = (
        "Warn when a task with a displayLabel has quietmode set to 1 "
        "in an autonomous playbook."
    )
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), tasks that have a "
        "displayLabel are visible to the user. Setting quietmode: 1 on such tasks "
        "suppresses their output, which may hide important information from the user."
    )
    error_message = (
        "The playbook is in an autonomous pack (managed: true, source: 'autonomous') "
        "but the following tasks have a displayLabel and quietmode set to 1: {0}. "
        "Consider removing quietmode: 1 from tasks that have a displayLabel."
    )
    related_field = "quietmode"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = _get_tasks_with_display_label_and_quiet_mode(content_item)
            if invalid_tasks:
                task_details = ", ".join(
                    f"task '{task_id}' (displayLabel='{display_label}')"
                    for task_id, display_label in invalid_tasks
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(task_details),
                        content_object=content_item,
                    )
                )
        return results


def _get_tasks_with_display_label_and_quiet_mode(
    content_item: ContentTypes,
) -> List[Tuple[str, str]]:
    """Check if a playbook is in an autonomous pack and has tasks with a displayLabel
    that also have quietmode set to 1.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        A list of tuples (task_id, display_label) for tasks that have both a
        displayLabel and quietmode=1, or an empty list if none found.
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return []

    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")
    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        return []

    invalid_tasks: List[Tuple[str, str]] = []
    for task_id, task_config in content_item.tasks.items():
        if task_config.type in EXCLUDED_TASK_TYPES:
            continue
        display_label = task_config.task.displayLabel
        if display_label and task_config.quietmode == 1:
            invalid_tasks.append((task_id, display_label))

    return invalid_tasks

from __future__ import annotations

import json
import re
from typing import Iterable, List, Set, Tuple, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]

# Regex to extract context key references from ${...} placeholders.
_CONTEXT_KEY_RE = re.compile(r"\$\{([^}]+)\}")


class IsValidDisplayLabelContextPathValidator(BaseValidator[ContentTypes]):
    error_code = "AS107"
    description = (
        "Validate that context keys referenced in displayLabel fields "
        "are actually used in other tasks within the same playbook."
    )
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), playbook task "
        "displayLabel fields should only reference context keys that are used in "
        "other tasks within the playbook. A displayLabel referencing a context key "
        "that is not consumed by any other task indicates the value has no functional "
        "purpose in the playbook flow."
    )
    error_message = (
        "The playbook is in an autonomous pack (managed: true, source: 'autonomous') "
        "but the following tasks have displayLabel fields referencing context keys "
        "not used in other tasks: {0}."
    )
    related_field = "displayLabel"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = get_invalid_display_label_context_keys(content_item)
            if invalid_tasks:
                task_details = ", ".join(
                    f"task '{task_id}' uses '{context_key}'"
                    for task_id, context_key in invalid_tasks
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(task_details),
                        content_object=content_item,
                    )
                )
        return results


def _extract_context_keys(text: str) -> List[str]:
    """Extract all context key references from ${...} placeholders in a string.

    Args:
        text: The string to search for context key references.

    Returns:
        A list of context key strings found in the text.
    """
    return _CONTEXT_KEY_RE.findall(text)


def _serialize_task_data(task_config_raw: dict) -> str:
    """Serialize a task's raw data to a string for context key searching.

    Args:
        task_config_raw: The raw dict representation of a TaskConfig.

    Returns:
        A string representation of the task data.
    """
    return json.dumps(task_config_raw, default=str)


def _is_context_key_used_in_other_tasks(
    context_key: str,
    current_task_id: str,
    all_tasks_serialized: dict[str, str],
) -> bool:
    """Check if a context key is used in any task other than the current one.

    Args:
        context_key: The context key to search for.
        current_task_id: The ID of the task containing the displayLabel.
        all_tasks_serialized: A dict mapping task_id -> serialized task data string.

    Returns:
        True if the context key is found in at least one other task.
    """
    for task_id, serialized_data in all_tasks_serialized.items():
        if task_id == current_task_id:
            continue
        if context_key in serialized_data:
            return True
    return False


def get_invalid_display_label_context_keys(
    content_item: ContentTypes,
) -> List[Tuple[str, str]]:
    """Check if a playbook is in an autonomous pack and has tasks with displayLabel
    fields referencing context keys not used in other tasks.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        A list of tuples (task_id, context_key) for invalid usages,
        or an empty list if all are valid.
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return []

    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")
    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        return []

    # Pre-serialize all tasks for efficient searching
    all_tasks_serialized: dict[str, str] = {}
    for task_id, task_config in content_item.tasks.items():
        all_tasks_serialized[task_id] = _serialize_task_data(task_config.to_raw_dict)

    # Check each task's displayLabel
    invalid_tasks: List[Tuple[str, str]] = []
    for task_id, task_config in content_item.tasks.items():
        display_label = task_config.task.displayLabel
        if not display_label:
            continue

        context_keys = _extract_context_keys(display_label)
        for context_key in context_keys:
            if not _is_context_key_used_in_other_tasks(
                context_key, task_id, all_tasks_serialized
            ):
                invalid_tasks.append((task_id, context_key))

    return invalid_tasks

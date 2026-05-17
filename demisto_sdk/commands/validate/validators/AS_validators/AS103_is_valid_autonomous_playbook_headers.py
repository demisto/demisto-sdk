from __future__ import annotations

from collections import deque
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    AUTONOMOUS_PLAYBOOK_ALLOWED_SECTIONS,
    AUTONOMOUS_PLAYBOOK_DUPLICATABLE_SECTIONS,
    AUTONOMOUS_PLAYBOOK_MANDATORY_SECTIONS,
    AUTONOMOUS_PLAYBOOK_SECTIONS_ORDER,
    PlaybookTaskType,
)
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsValidAutonomousPlaybookHeadersValidator(BaseValidator[ContentTypes]):
    error_code = "AS103"
    description = (
        "Validate that autonomous playbooks have correct section headers "
        "with valid names, non-empty descriptions, and proper ordering."
    )
    rationale = (
        "Autonomous playbooks must follow a standard structure with specific "
        "section headers in the correct order to ensure consistent behavior."
    )
    error_message = (
        "The playbook is in an autonomous pack but has invalid section headers: {0}"
    )
    related_field = "tasks"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            errors = validate_autonomous_playbook_headers(content_item)
            if errors:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format("; ".join(errors)),
                        content_object=content_item,
                    )
                )
        return results


def validate_autonomous_playbook_headers(content_item: ContentTypes) -> List[str]:
    """Validate section headers in an autonomous playbook.

    Returns a list of error strings, empty if valid.
    """
    # 1. Check if autonomous pack
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return []
    if not (
        pack_metadata.get("managed") is True
        and pack_metadata.get("source") == "autonomous"
    ):
        return []

    # 2. BFS traversal to collect title tasks in order
    title_tasks_ordered = _get_title_tasks_in_order(content_item)

    errors: List[str] = []

    # 3. Check for unknown section names
    for task_id, name, _ in title_tasks_ordered:
        if name not in AUTONOMOUS_PLAYBOOK_ALLOWED_SECTIONS:
            errors.append(
                f"Task '{task_id}' has unknown section name '{name}'. "
                f"Allowed: {', '.join(sorted(AUTONOMOUS_PLAYBOOK_ALLOWED_SECTIONS))}"
            )

    # 4. Check for empty descriptions
    for task_id, name, description in title_tasks_ordered:
        if not description:
            errors.append(
                f"Section '{name}' (task '{task_id}') has an empty description"
            )

    # 5. Check mandatory sections exist
    found_names = {name for _, name, _ in title_tasks_ordered}
    for section in sorted(AUTONOMOUS_PLAYBOOK_MANDATORY_SECTIONS):
        if section not in found_names:
            errors.append(f"Missing mandatory section '{section}'")

    # 6. Check ordering.
    # Duplicatable sections (e.g. "Playbook Completed") may appear multiple times;
    # for the ordering check we collapse consecutive/repeated occurrences of those
    # sections so that each unique non-duplicatable section still appears in the
    # correct relative position, while duplicatable sections are allowed anywhere
    # after their canonical position in AUTONOMOUS_PLAYBOOK_SECTIONS_ORDER.
    found_in_order = [
        name
        for _, name, _ in title_tasks_ordered
        if name in AUTONOMOUS_PLAYBOOK_ALLOWED_SECTIONS
    ]
    # Build a deduplicated view: keep only the first occurrence of each
    # duplicatable section for the ordering comparison.
    seen_duplicatable: set = set()
    deduped_found: List[str] = []
    for name in found_in_order:
        if name in AUTONOMOUS_PLAYBOOK_DUPLICATABLE_SECTIONS:
            if name not in seen_duplicatable:
                seen_duplicatable.add(name)
                deduped_found.append(name)
        else:
            deduped_found.append(name)

    expected_filtered = [
        s for s in AUTONOMOUS_PLAYBOOK_SECTIONS_ORDER if s in found_names
    ]
    if deduped_found != expected_filtered:
        errors.append(
            f"Sections are out of order. "
            f"Expected: {expected_filtered}, Found: {found_in_order}"
        )

    return errors


def _get_title_tasks_in_order(
    content_item: ContentTypes,
) -> List[tuple]:
    """BFS the playbook task graph, returning title tasks in traversal order.

    Returns list of (task_id, task_name, task_description).
    """
    start_task_id = content_item.data.get("starttaskid")
    if not start_task_id:
        return []

    tasks = content_item.tasks
    visited: set = set()
    queue: deque = deque([str(start_task_id)])
    title_tasks: List[tuple] = []

    while queue:
        task_id = queue.popleft()
        if task_id in visited:
            continue
        visited.add(task_id)

        task_config = tasks.get(task_id)
        if not task_config:
            continue

        if (
            task_config.type == PlaybookTaskType.TITLE
            and not task_config.task.isSubSection
        ):
            title_tasks.append(
                (task_id, task_config.task.name, task_config.task.description)
            )

        if task_config.nexttasks:
            for next_ids in task_config.nexttasks.values():
                for next_id in next_ids or []:
                    if next_id not in visited:
                        queue.append(next_id)

    return title_tasks

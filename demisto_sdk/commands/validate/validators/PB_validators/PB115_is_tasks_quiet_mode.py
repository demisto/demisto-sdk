from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsTasksQuietModeValidator(BaseValidator[ContentTypes]):
    error_code = "PB115"
    description = "Checks if all tasks in a playbook are in quiet mode."
    rationale = "Confirmation of turning off quitmode"
    error_message = "Playbook '{playbook_name}' contains tasks that are not in quiet mode (quietmode: 2) The tasks names is: '{tasks}'."
    fix_message = (
        "Fixed playbook '{playbook_name}' to set tasks '{tasks}' to (quietmode: 0)."
    )
    related_field = "tasks"
    is_auto_fixable = True
    related_file_type = [RelatedFileType.YML]
    invalid_tasks_in_playbooks: dict[str, str] = {}

    def get_invalid_task_ids(self, content_item: ContentTypes) -> List[tuple[str, str]]:
        """
        Identify tasks with quietmode == 2 and update self.invalid_tasks_in_playbooks with these tasks.

        Args:
            content_item (ContentTypes): The content item to check.

        Returns:
            List[str]: List of task IDs where quietmode == 2.
        """
        invalid_task_ids = [
            (task, task_key.id)
            for task, task_key in content_item.tasks.items()
            if task_key.quietmode == 2
        ]

        if invalid_task_ids:
            self.invalid_tasks_in_playbooks[content_item.name] = invalid_task_ids

        return invalid_task_ids

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """
        Validates that tasks in content_items(playbook) are in quiet mode if they contain an input query for "indicators".

        Args:
            content_items (Iterable[ContentTypes]): Content items to validate.

        Returns:
            List[ValidationResult]: Validation results for items not meeting criteria.
        """
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    playbook_name=content_item.name,
                    tasks=", ".join([task[1] for task in invalid_tasks]),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                any(
                    (input.get("playbookInputQuery") or {}).get("queryEntity")
                    == "indicators"
                    for input in content_item.data.get("inputs", {})
                )
                and (invalid_tasks := self.get_invalid_task_ids(content_item))
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Sets quietmode to 0 for all tasks with quietmode set to 2 in the given content item.

        Args:
            content_item (ContentTypes): The content item to fix.

        Returns:
            FixResult: The result of the fix operation.
        """
        tasks_to_fix = self.get_invalid_task_ids(content_item)
        for task, _ in tasks_to_fix:
            task_key = content_item.tasks.get(task)
            task_key.quietmode = 0
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                playbook_name=content_item.name,
                tasks=", ".join([task[1] for task in tasks_to_fix]),
            ),
            content_object=content_item,
        )

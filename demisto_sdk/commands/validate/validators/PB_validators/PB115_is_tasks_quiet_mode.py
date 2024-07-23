from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.tools import is_indicator_pb
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsTasksQuietModeValidator(BaseValidator[ContentTypes]):
    error_code = "PB115"
    description = "Checks if the 'quietmode' field of all tasks in playbook are not in default value."
    rationale = "Confirmation of turning off quitmode"
    error_message = "Playbook '{playbook_name}' contains tasks that are not in quiet mode (quietmode: 2) The tasks names is: '{tasks}'."
    fix_message = (
        "Fixed playbook '{playbook_name}' to set tasks '{tasks}' to (quietmode: 0)."
    )
    related_field = "tasks"
    is_auto_fixable = True
    invalid_tasks_in_playbooks: Dict[str, List[TaskConfig]] = {}

    def get_invalid_task_ids(self, content_item: Playbook) -> List[TaskConfig]:
        """
        Identify tasks with quietmode == 2 and update self.invalid_tasks_in_playbooks with these tasks.

        Args:
            content_item (ContentTypes): The content item to check.

        Returns:
            List[str]: List of task IDs where quietmode == 2.
        """
        invalid_task_ids = [
            task for task in list(content_item.tasks.values()) if task.quietmode == 2
        ]
        self.invalid_tasks_in_playbooks[content_item.name] = invalid_task_ids
        return invalid_task_ids

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
                    tasks=", ".join([task.id for task in invalid_tasks]),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if is_indicator_pb(content_item)
            and (invalid_tasks := self.get_invalid_task_ids(content_item))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Sets quietmode to 0 for all tasks with quietmode set to 2 in the given content item.

        Args:
            content_item (ContentTypes): The content item to fix.

        Returns:
            FixResult: The result of the fix operation.
        """
        invalid_tasks = self.invalid_tasks_in_playbooks.get(content_item.name, [])
        for task in invalid_tasks:
            task.quietmode = 0
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                playbook_name=content_item.name,
                tasks=", ".join([task.id for task in invalid_tasks]),
            ),
            content_object=content_item,
        )

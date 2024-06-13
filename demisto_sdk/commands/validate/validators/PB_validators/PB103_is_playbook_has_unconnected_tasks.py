from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsPlaybookHasUnconnectedTasks(BaseValidator[ContentTypes]):
    error_code = "PB103"
    description = "Checks whether there is an unconnected task."
    rationale = "Checks whether there is an unconnected task to the root task."
    error_message = (
        "Playbook conditional task with id:{task_id} has task with unreachable "
        'next task condition "{next_task_branch}". Please remove this task or add '
        "this condition to condition task with id:{task_id}."
    )
    related_field = "tasks"
    is_auto_fixable = False

    @staticmethod
    def _is_unconnected_task(playbook: ContentTypes) -> bool:
        """Checks whether a playbook has an unconnected task.
        Args:
            - playbook (ContentTypes): The playbook to check.
        Return:
            - bool. True if the playbook has an unconnected task, False otherwise.
        """
        start_task_id = playbook.data.get("starttaskid")
        tasks = playbook.tasks
        tasks_bucket = set()
        next_tasks_bucket = set()

        for task_id, task in tasks.items():
            if task_id != start_task_id:
                tasks_bucket.add(task_id)
            next_tasks = task.get("nexttasks", {})
            for next_task_ids in next_tasks.values():
                if next_task_ids:
                    next_tasks_bucket.update(next_task_ids)
        orphan_tasks = tasks_bucket.difference(next_tasks_bucket)
        if orphan_tasks:
            return False
        return tasks_bucket.issubset(next_tasks_bucket)

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (self._is_unconnected_task(content_item))
        ]

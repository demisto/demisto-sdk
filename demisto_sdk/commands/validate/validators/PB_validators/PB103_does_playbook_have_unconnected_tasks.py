from __future__ import annotations

from typing import Any, Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook
ERROR_MSG = "The following tasks ids have no previous tasks: {orphan_tasks}."


class DoesPlaybookHaveUnconnectedTasks(BaseValidator[ContentTypes]):
    error_code = "PB103"
    description = "Validate whether there is an unconnected task."
    rationale = "Make sure there are no unconnected tasks to ensure the playbook will work as expected."
    error_message = ERROR_MSG
    related_field = "tasks"
    is_auto_fixable = False

    @staticmethod
    def is_unconnected_task(playbook: ContentTypes) -> set[Any]:
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
            if next_tasks := task.nexttasks:
                for next_task_ids in next_tasks.values():
                    if next_task_ids:
                        next_tasks_bucket.update(next_task_ids)
        orphan_tasks = tasks_bucket.difference(next_tasks_bucket)
        return orphan_tasks

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(orphan_tasks=sorted(orphan_tasks)),
                content_object=content_item,
            )
            for content_item in content_items
            if (orphan_tasks := self.is_unconnected_task(content_item))
        ]

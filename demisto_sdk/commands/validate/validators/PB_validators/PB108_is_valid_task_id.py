
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import is_string_uuid
from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Playbook


class IsValidTaskIdValidator(BaseValidator[ContentTypes]):
    error_code = "PB108"
    description = "Validate that the task ID and the 'id' under the 'task' field are from UUID format"
    rationale = ""
    error_message = ("On task: {0},  the field 'taskid': {1} and the 'id' under the 'task' field: {2}, must be from "
                     "uuid format.")
    related_field = "taskid"
    is_auto_fixable = False
    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """Check whether all playbook tasks has valid taskid and the 'id' under the 'task' field is valid as well.
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = self.invalid_tasks(content_item.tasks)
            for task_id in invalid_tasks:
                taskid = invalid_tasks[task_id].taskid
                inner_id = invalid_tasks[task_id].task.id
                results.append(ValidationResult(
                    validator=self,
                    message=self.error_message.format(task_id, taskid, inner_id),
                    content_object=content_item,
                ))
        return results

    def invalid_tasks(self, tasks: dict[str, TaskConfig]) -> dict[str, TaskConfig]:
        """Check which tasks has invalid taskid or the 'id' under the 'task' field is invalid
        Args:
            - tasks dict[str, TaskConfig]: The playbook tasks.
        Return:
            - dict[str, TaskConfig] that contains the invalid tasks.
        """
        invalid_tasks = {}
        for task_id in tasks:
            task = tasks[task_id]
            taskid = task.taskid
            inner_id = task.task.id
            is_valid_task = is_string_uuid(taskid) and is_string_uuid(inner_id)
            if not is_valid_task:
                invalid_tasks[task_id] = task
        return invalid_tasks

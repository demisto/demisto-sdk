from __future__ import annotations

from typing import Iterable, List

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
    description = "Validate that the task ID and the 'id' under the 'task' field are from UUID format."
    rationale = "Each task should have a unique id in UUID format to avoid unknown behavior and breaking the playbook."
    error_message = "This playbook has tasks with invalid 'taskid' or invalid 'id' under the 'task' field.\n{0}"
    related_field = "taskid"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Check whether all playbook tasks has valid taskid and the 'id' under the 'task' field is valid as well.
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            invalid_tasks = self.invalid_tasks(content_item.tasks)
            tasks_error_message = ""
            for task_id in invalid_tasks:
                tasks_error_message = (
                    f"{tasks_error_message}Task {task_id} has invalid UUIDs in the fields "
                    f"{invalid_tasks[task_id]}.\n"
                )
            if invalid_tasks:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(tasks_error_message),
                        content_object=content_item,
                    )
                )
        return results

    def invalid_tasks(self, tasks: dict[str, TaskConfig]) -> dict[str, list]:
        """Check which tasks has invalid taskid or the 'id' under the 'task' field is invalid
        Args:
            - tasks dict[str, TaskConfig]: The playbook tasks.
        Return:
            - dict[str, TaskConfig] that contains the invalid tasks.
        """
        invalid_tasks = {}
        for task_id, task in tasks.items():
            taskid = task.taskid
            inner_id = task.task.id
            is_valid_taskid = is_string_uuid(taskid)
            is_valid_inner_id = is_string_uuid(inner_id)
            invalid_fields = []
            if not is_valid_taskid:
                invalid_fields.append("taskid")
            if not is_valid_inner_id:
                invalid_fields.append("the 'id' under the 'task' field")
            if invalid_fields:
                invalid_tasks[task_id] = invalid_fields
        return invalid_tasks

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = TestPlaybook


class IsTaskidDifferentFromidValidator(BaseValidator[ContentTypes]):
    error_code = "PB109"
    description = (
        "Check that taskid field and id field under task field contains equal values."
    )
    rationale = "Playbooks task ids should be in uuid format"
    error_message = "On tasks: {},  the field 'taskid' and the 'id' under the 'task' field must be with equal value."
    related_field = "1"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        error_results = []
        
        for content_item in content_items:
            tasks: dict = content_item.tasks
            not_valid_tasks = []
            
            for task_key, task in tasks.items():
                if task.taskid != task.task.id:
                    not_valid_tasks.append(task_key)
                    
            if not_valid_tasks:
                error_results.append(
                ValidationResult(
                validator=self,
                message=self.error_message.format(
                    not_valid_tasks,
                ),
                content_object=content_item,
                ))
            
        return error_results
        

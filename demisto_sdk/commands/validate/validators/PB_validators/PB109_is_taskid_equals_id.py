
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
        "Check that taskid field and id field under task field contains equal values"
    )
    rationale = ""
    error_message = "On task: {},  the field 'taskid': {} and the 'id' under the 'task' field: {}, must be with equal value."
    related_field = ""
    is_auto_fixable = False

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        error_results = []
        for content_item in content_items:
            tasks: dict = content_item.tasks
            for task_key, task in tasks.items():
                taskid = task.taskid
                inner_id = task.id
                is_valid_task = taskid == inner_id
                if not is_valid_task:
                    error_results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                task_key, taskid, inner_id
                            ),
                            content_object=content_item,
                        )
                    )
        return error_results
    

    

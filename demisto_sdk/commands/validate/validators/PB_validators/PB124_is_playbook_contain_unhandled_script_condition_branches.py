from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsPlaybookContainUnhandledScriptConditionBranchesValidator(
    BaseValidator[ContentTypes]
):
    error_code = "PB124"
    description = "Make sure that all conditional tasks contains at least 2 next tasks."
    rationale = "Ensure we don't miss unhandled cases in our playbook."
    error_message = (
        "The following conditional tasks contains unhandled conditions: {0}."
    )
    related_field = "task.type, task.nexttasks"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(unhandled_script_condition_tasks)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                unhandled_script_condition_tasks
                := self.get_unhandled_script_condition_tasks(
                    list(content_item.tasks.values())
                )
            )
        ]

    def get_unhandled_script_condition_tasks(
        self, tasks: List[TaskConfig]
    ) -> List[str]:
        """List all the script condition tasks with unhandled branches.

        Args:
            tasks (List[TaskConfig]): The list of the playbooks tasks.

        Returns:
            List[str]: The list of IDs of tasks with unhandled branches.
        """
        return [
            task.id
            for task in tasks
            if (
                task.type == PlaybookTaskType.CONDITION
                and task.task.scriptName
                and task.nexttasks
                and len(task.nexttasks) < 2
            )
        ]

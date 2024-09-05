from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class DoesPlaybookHaveUnhandledConditionsValidator(BaseValidator[ContentTypes]):
    error_code = "PB122"
    description = (
        "Validate whether branches of built-in conditional tasks are handled properly."
    )
    rationale = "Ensures the playbook logic is complete."
    error_message = "Playbook conditional task with ID: {task_id} has unhandled conditions: {conditions}"
    related_field = "conditions"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """Checks whether all conditional task branches are handled properly.
        Args:
            content_items (Iterable[ContentTypes]): The content items to check.
        Returns:
            List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for playbook in content_items:
            invalid_tasks = self.unhandled_conditions(playbook)

            for task_id, unhandled_conditions in invalid_tasks.items():
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            task_id=task_id,
                            conditions=",".join(unhandled_conditions),
                        ),
                        content_object=playbook,
                    )
                )

        return results

    @staticmethod
    def unhandled_conditions(playbook: ContentTypes) -> dict[str, set[str]]:
        unhandled_conditions = {}
        tasks = playbook.tasks
        for task in tasks.values():
            if task.type == PlaybookTaskType.CONDITION and task.conditions:
                nondefault_nexttasks: set[str] = {
                    k.upper()
                    for k in (task.nexttasks or {}).keys()
                    if k and k.upper() != "#DEFAULT#"
                }
                condition_labels: set[str] = {
                    str(condition.get("label")).upper()
                    for condition in task.conditions
                    if condition.get("label")
                }
                if task_unhandled_conditions := condition_labels ^ nondefault_nexttasks:
                    unhandled_conditions[task.id] = task_unhandled_conditions

        return unhandled_conditions

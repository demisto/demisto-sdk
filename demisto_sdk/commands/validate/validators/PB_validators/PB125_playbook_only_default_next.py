from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookOnlyDefaultNextValidator(BaseValidator[ContentTypes]):
    error_code = "PB125"
    description = (
        "Validates that a condition task doesn't has only a default next-task."
    )
    rationale = "Validates that a condition task doesn't has only a default next-task."
    error_message = (
        "Playbook has conditional tasks with an only default condition. Tasks IDs: {tasks}.\n"
        "Please remove these tasks or add another non-default condition to these conditional tasks."
    )
    related_field = "conditions"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: list = list()

        for content_item in content_items:
            invalid_tasks: list = []
            for task_id, task in content_item.tasks.items():
                if (
                    len(list(task.nexttasks or {})) == 1
                    and list((task.nexttasks or {}).keys())[0].lower() == "#default#"
                ):
                    invalid_tasks.append(task_id)

            if invalid_tasks:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(tasks=invalid_tasks),
                        content_object=content_item,
                    )
                )

        return validation_results

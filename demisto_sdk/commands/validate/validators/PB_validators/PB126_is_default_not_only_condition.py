from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PlaybookTaskType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsDefaultNotOnlyConditionValidator(BaseValidator[ContentTypes]):
    error_code = "PB126"
    description = (
        "Ensure that conditional tasks have an execution path besides for the default."
    )
    rationale = (
        "We want to ensure that conditional tasks have more than path which is not the default one o/w it "
        "make no sense to have such."
    )
    error_message = (
        "The following playbook conditional tasks only have a default option: {}. Please remove these tasks or add "
        "another non-default option to each task."
    )
    related_field = "conditions"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            failed_tasks = []
            for task in content_item.tasks.values():
                if (
                    task.type == PlaybookTaskType.CONDITION
                    and task.message
                    and task.message.get("replyOptions")
                ):
                    reply_options = set(
                        map(str.upper, task.message.get("replyOptions", []))
                    )
                    if len(reply_options) == 1 and "#default#".upper() in reply_options:
                        failed_tasks.append(f"Task: {task.id}")
            if failed_tasks:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(failed_tasks),
                        content_object=content_item,
                    )
                )
        return validation_results

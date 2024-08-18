from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookDeleteContextAllValidator(BaseValidator[ContentTypes]):
    error_code = "PB105"
    description = (
        "Validate whether the playbook has a DeleteContext with all set to 'Yes'."
        " If the Playbook has it, it is not valid."
    )
    rationale = "Playbook can not have DeleteContext script with arg all set to yes."
    error_message = (
        "The playbook includes DeleteContext tasks with all set to 'yes', which is not permitted."
        " Please correct the following tasks: {invalid_tasks}"
        " For more info, see: https://xsoar.pan.dev/docs/playbooks/playbooks-overview#inputs-and-outputs"
    )
    related_field = "task"
    is_auto_fixable = False

    def if_delete_context_exists(self, playbook: Playbook):
        """Check whether the playbook has a DeleteContext with all set to 'Yes'.
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - True if playbook has a DeleteContext with all set to 'Yes' and False otherwise.
        """
        tasks = playbook.tasks
        invalid_tasks = []
        for task in tasks.values():
            current_task = task.task
            script_args = task.scriptarguments
            if (
                current_task
                and current_task.scriptName == "DeleteContext"
                and script_args
                and script_args.get("all", {}).get("simple", "") == "yes"
            ):
                invalid_tasks.append(task.task.id)
        return invalid_tasks

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(invalid_tasks=invalid_tasks),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_tasks := self.if_delete_context_exists(content_item))
        ]

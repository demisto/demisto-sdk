
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
    description = ("Validate whether the playbook has a DeleteContext with all set to 'Yes'."
                   " If the Playbook has it, it is not valid.")
    rationale = "Playbook can not have DeleteContext script with arg all set to yes."
    error_message = ("The playbook contains DeleteContext with all set to True which is not allowed."
                     " For more info, see: https://xsoar.pan.dev/docs/playbooks/playbooks-overview#inputs-and-outputs")
    related_field = "task"
    is_auto_fixable = False

    def if_delete_context_exists(self, playbook: ContentTypes):
        tasks = playbook.tasks
        for task in tasks.values():
            curr_task = task.get("task", {})
            script_args = task.get("scriptarguments", {})
            if (
                curr_task and curr_task.get("scriptName", "") == "DeleteContext"
                and script_args and script_args.get("all", {}).get("simple", "") == "yes"
            ):
                return True
        return False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not self.if_delete_context_exists(content_item)
            )
        ]
    

    

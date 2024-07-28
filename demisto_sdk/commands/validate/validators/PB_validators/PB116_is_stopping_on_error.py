from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.tools import is_indicator_pb
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


def get_error_tolerant_tasks(playbook: Playbook):
    """
    Retrieve tasks from the playbook that are set to continue on error.
    """
    return [task for task in playbook.tasks.values() if task.continueonerror]


class IsStoppingOnErrorValidator(BaseValidator[ContentTypes]):
    error_code = "PB116"
    description = (
        "The validation checks that all playbook tasks stop when encountering an error."
    )
    error_message = "The following tasks of the playbook do not stop on error:\n{}"
    related_field = "tasks"
    is_auto_fixable = False
    rationale = (
        "For indicator playbooks, tasks will likely be executing on thousands of indicators. "
        "Without these validations in place, we may easily release playbooks for general availability "
        "that can crash Demisto instances if a playbook task does not stop on error, "
        "causing following tasks to rely on its output and fail."
    )

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            if is_indicator_pb(content_item) and (
                bad_tasks := get_error_tolerant_tasks(content_item)
            ):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(bad_tasks),
                        content_object=content_item,
                    )
                )
        return results

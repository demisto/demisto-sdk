from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.tools import (
    collect_all_inputs_from_inputs_section,
    collect_all_inputs_in_use,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsInputKeyNotInTasksValidator(BaseValidator[ContentTypes]):
    error_code = "PB118"
    description = "Validate that all inputs described in the playbooks input section are used in tasks."
    rationale = "For more info, see: https://xsoar.pan.dev/docs/playbooks/playbooks-overview#inputs-and-outputs"
    error_message = "The playbook '{playbook_name}' contains the following inputs that are not used in any of its tasks: {inputs_not_in_use}"
    fix_message = ""
    related_field = "input"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """Check whether all playbook inputs (defined in the "inputs" section) are in use in any of the tasks
        Args:
            - content_items (Iterable[ContentTypes]): The content items to check.
        Return:
            - List[ValidationResult]. List of ValidationResults objects.
        """
        results: List[ValidationResult] = []
        for content_item in content_items:
            inputs_in_use = collect_all_inputs_in_use(content_item)
            inputs_in_section = collect_all_inputs_from_inputs_section(content_item)

            if inputs_not_in_use := inputs_in_section.difference(inputs_in_use):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            playbook_name=content_item.name,
                            inputs_not_in_use=", ".join(inputs_not_in_use),
                        ),
                        content_object=content_item,
                    )
                )
        return results

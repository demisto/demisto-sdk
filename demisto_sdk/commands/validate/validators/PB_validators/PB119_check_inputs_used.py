from __future__ import annotations

from typing import Iterable, List

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


class CheckInputsUsedExist(BaseValidator[ContentTypes]):
    error_code = "PB119"
    description = "Validates that all inputs used are defined."
    rationale = (
        "Inputs that are used but not provided to a playbook is probably an oversight."
    )
    error_message = "Inputs [{}] were used but not provided for this playbook."
    related_field = "inputs"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            if unused_inputs := (
                collect_all_inputs_in_use(content_item)
                - collect_all_inputs_from_inputs_section(content_item)
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(sorted(unused_inputs))
                        ),
                        content_object=content_item,
                    )
                )
        return validation_results

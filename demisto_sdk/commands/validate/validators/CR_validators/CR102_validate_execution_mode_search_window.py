from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = CorrelationRule


class ExecutionModeSearchWindowValidator(BaseValidator[ContentTypes]):
    error_code = "CR102"
    description = "Validates 'search_window' existence and non-emptiness for 'execution_mode' = 'SCHEDULED'."
    rationale = ""
    error_message = "The 'search_window' key must exist and cannot be empty when the 'execution_mode' is set to 'SCHEDULED'."
    related_field = "search_window"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            if(content_item.execution_mode == "REAL_TIME"): #when execution_mode is set to REAL_TIME, search_window can be empty
                continue
            elif((not content_item.search_window) or (content_item.execution_mode == "SCHEDULED" and not content_item.search_window)):
                validation_results.append(ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            ))
                
        return validation_results


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
    description = (
        "Validates 'search_window' existence and non-emptiness for 'execution_mode' = 'SCHEDULED'."
    )
    rationale = ""
    error_message = "The 'search_window' key must exist and cannot be empty when the 'execution_mode' is set to 'SCHEDULED'."
    related_field = ""
    is_auto_fixable = False

    def __init__(self):
        self.execution_mode = self.current_file.get("execution_mode", None)
        self.search_window = self.current_file.get("search_window", None)
        
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
               ("search_window" not in self.current_file) or (
                self.execution_mode == "SCHEDULED"
                and not self.search_window)
            )
        ]
        

    

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.correlation_rule import (
    CorrelationRule,
    ExecutionMode,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = CorrelationRule


class ExecutionModeSearchWindowValidator(BaseValidator[ContentTypes]):
    error_code = "CR102"
    description = "Validates 'search_window' existence and non-emptiness for 'execution_mode' = 'SCHEDULED'."
    rationale = "'SCHEDULED' execution must have a defined time frame 'search_window' to operate within"
    error_message = "The 'search_window' key must exist and cannot be empty when the 'execution_mode' is set to 'SCHEDULED'."
    related_field = "search_window"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self, message=self.error_message, content_object=content_item
            )
            for content_item in content_items
            if (not content_item.search_window)
            and content_item.execution_mode != ExecutionMode.REAL_TIME
        ]

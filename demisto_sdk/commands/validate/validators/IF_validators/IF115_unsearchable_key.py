from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField


class UnsearchableKeyValidator(BaseValidator[ContentTypes]):
    error_code = "IF115"
    description = "Checks if the `unsearchable` key set to true"
    rationale = ""
    error_message = (
        "Warning: Indicator and incident fields should include the `unsearchable` key set to true."
        " When missing or set to false, the platform will index the data in this field."
        " Unnecessary indexing of fields might affect the performance and disk usage in environments."
        " While considering the above mentioned warning, you can bypass this error by adding it to the .pack-ignore file."
    )
    related_field = "unsearchable"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.unsearchable)
        ]

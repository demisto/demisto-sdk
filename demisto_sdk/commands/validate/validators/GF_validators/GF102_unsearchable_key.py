from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = GenericField


class UnsearchableKeyValidator(BaseValidator[ContentTypes]):
    error_code = "GF102"
    description = "Checks if the unsearchable key is set to true"
    rationale = (
        "Marking many items searchable causes index and search loads on the platform. "
        "Official demisto/content GenericField files must be set to Unsearchable. "
        "In custom content, it's recommended to keep the number of searchable fields to a minimum."
    )
    error_message = (
        "Warning: Generic fields should have `unsearchable` set to true. "
        "Otherwise, the platform will index the data in this field, potentially affecting performance and disk usage. "
        "To suppress this validation, use the .pack-ignore file."
    )
    related_field = "unsearchable"
    expected_git_statuses = [GitStatuses.ADDED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.unsearchable)
        ]

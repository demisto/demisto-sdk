from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = GenericField


class UnsearchableKeyValidator(BaseValidator[ContentTypes]):
    error_code = "GF102"
    description = "Checks if the unsearchable key is set to true"
    rationale = "Preventing resource load on the platform"
    error_message = (
        "Warning: Generic fields should include the `unsearchable` key set to true."
        " When missing or set to false, the platform will index the data in this field."
        " Unnecessary indexing of fields might affect the performance and disk usage in environments."
        " While considering the above mentioned warning, you can bypass this error by adding it to the"
        " .pack-ignore file."
    )
    related_field = "unsearchable"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not content_item.unsearchable
            )
        ]

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IndicatorType


class DetailsFieldEqualsIdValidator(BaseValidator[ContentTypes]):
    error_code = "RP102"
    description = "Validate that the id and the details fields are equal"
    error_message = "id and details fields are not equal."
    rationale = "To align with the platform requirements."
    related_field = "id"
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
            if content_item.description != content_item.object_id
        ]

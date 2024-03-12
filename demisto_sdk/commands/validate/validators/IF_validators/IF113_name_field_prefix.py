
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = IncidentField


class NameFieldPrefixValidator(BaseValidator[ContentTypes]):
    error_code = "IF113"
    description = "Checks if field name starts with its pack name or one of the itemPrefixes from pack metadata"
    rationale = ""
    error_message = "Field name: {field_name} is invalid. Field name must start with the relevant pack name"
    related_field = "name"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(field_name=content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
    

    

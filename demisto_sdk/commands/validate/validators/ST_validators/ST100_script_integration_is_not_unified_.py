from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class ScriptIntegrationNotInOldFormatValidator(BaseValidator):

    error_code = "ST100"
    description = "Validate that the given content-item is not unified"
    error_message = "content-item {0} is unified, it is not be unified"
    related_field = "script"
    is_auto_fixable = False

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.object_id),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_unified
        ]

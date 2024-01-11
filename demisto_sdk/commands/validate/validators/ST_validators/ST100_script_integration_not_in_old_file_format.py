from __future__ import annotations

from typing import ClassVar, Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class ScriptIntegrationNotInOldFormatValidator(BaseValidator):

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        for item in content_items:
            item.is_unified
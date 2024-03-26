from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[IncidentField, IndicatorField]


class CliNameMatchIdValidator(BaseValidator[ContentTypes]):
    error_code = "BA116"
    description = (
        "validate that the CLI name and the id match for incident and indicators field"
    )
    rationale = "Consistency between the CLI name (used by the platform) and the id."
    error_message = (
        "The cli name {0} doesn't match the standards. the cliName should be: {1}."
    )
    fix_message = "Changing the cli name to ({0})."
    related_field = "cli_name, id"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.cli_name,
                    content_item.object_id,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.cli_name != content_item.object_id
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.cli_name = content_item.object_id
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.object_id),
            content_object=content_item,
        )

from typing import Iterable

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration

ALLOWED_SECTIONS = [
    "Connect",
    "Collect",
    "Optimize",
]


class StrictSchemaValidator(BaseValidator[ContentTypes]):
    error_code = "ST111"
    description = "Validate that the scheme's structure is valid, no fields excluded."
    rationale = "Maintain valid structure for content items."

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> list[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            if error_message := self.is_missing_section_fields(content_item):
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=error_message,
                        content_object=content_item,
                    )
                )
        return invalid_content_items

    def is_missing_section_fields(self, content_item: ContentTypes) -> str:
        section_order = content_item.data.get("sectionorder") or content_item.data.get(
            "sectionOrder"
        )
        if not section_order:
            return "Missing section order"
        configurations = content_item.data.get("configuration")
        for configuration in configurations:  # type:ignore[union-attr]
            section = configuration.get("section")
            if not section:
                return f'Missing section for configuration {configuration.get("name")}'
        return ""

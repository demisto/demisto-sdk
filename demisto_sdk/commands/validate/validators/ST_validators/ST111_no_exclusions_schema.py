from typing import Iterable

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration

ALLOWED_SECTIONS = ["Connect", "Collect", "Optimize", "Mirroring", "Result"]


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
        """
        Validates section-related fields in content items.

        Returns specific error if 'sectionOrder' (camelCase) is used instead of 'sectionorder' (lowercase).
        Returns missing field error if neither 'sectionorder' nor 'sectionOrder' exists.
        Validates that all configuration parameters have required section fields.

        Returns:
            str: Error message if validation fails, empty string if validation passes.
        """
        section_order_lowercase = content_item.data.get("sectionorder")
        section_order_camelcase = content_item.data.get("sectionOrder")

        if section_order_camelcase and not section_order_lowercase:
            return "Found 'sectionOrder' field. Please use 'sectionorder' (lowercase) instead of 'sectionOrder'."

        section_order = section_order_lowercase or section_order_camelcase
        if not section_order:
            return (
                "Missing sectionorder key. Add sectionorder to the top of your YAML file and specify the order"
                f" of the {', '.join(ALLOWED_SECTIONS)} sections (at least one is required)."
            )
        configuration_parameters = content_item.data.get("configuration")
        parameters_missing_sections = []
        for parameter in configuration_parameters:  # type:ignore[union-attr]
            section = parameter.get("section")
            if not section:
                parameters_missing_sections.append(parameter.get("name"))
        if parameters_missing_sections:
            return (
                f"Missing section for the following parameters: {parameters_missing_sections} Please specify the "
                "section for these parameters."
            )
        return ""

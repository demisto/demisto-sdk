from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_GENERAL_CONFIG_DESCRIPTION = "General configurations for all capabilities"


class IsValidGeneralConfigDescriptionValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO108"
    description = (
        "Validates that capabilities.yaml declares a general_configurations "
        "block whose description equals the standard capabilities-page prompt."
    )
    rationale = (
        "The capabilities page always shows a general configurations section "
        "with a fixed, standardized description. Every connector (grouped or "
        "standard) must declare general_configurations, and its description "
        "must be the exact expected string."
    )
    error_message = (
        "Connector '{connector_id}' capabilities general_configurations is "
        "invalid: {details}."
    )
    related_field = "general_configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            capabilities_metadata = connector.capabilities_metadata
            if capabilities_metadata is None:
                # No capabilities.yaml - nothing to validate here.
                continue

            details: List[str] = []

            general_configurations = capabilities_metadata.general_configurations
            if general_configurations is None:
                details.append(
                    "general_configurations must be present with description "
                    f"'{EXPECTED_GENERAL_CONFIG_DESCRIPTION}'"
                )
            elif (
                general_configurations.description
                != EXPECTED_GENERAL_CONFIG_DESCRIPTION
            ):
                details.append(
                    f"general_configurations.description must be "
                    f"'{EXPECTED_GENERAL_CONFIG_DESCRIPTION}', got "
                    f"'{general_configurations.description}'"
                )

            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details="; ".join(details),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

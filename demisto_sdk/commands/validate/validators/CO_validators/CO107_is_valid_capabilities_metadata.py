from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_CAPABILITIES_TITLE = "Capabilities"
EXPECTED_CAPABILITIES_DESCRIPTION = "Name and configure the instance capabilities"


class IsValidCapabilitiesMetadataValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO107"
    description = (
        "Validates the capabilities.yaml metadata block: title must equal "
        "'Capabilities', description must equal the standard capabilities "
        "prompt, and (for grouped connectors only) metadata.help must be "
        "omitted."
    )
    rationale = (
        "The capabilities page presents a consistent, standardized experience "
        "across all connectors. Its title and description are fixed strings. "
        "For grouped connectors, help text is not permitted on the "
        "capabilities metadata block."
    )
    error_message = (
        "Connector '{connector_id}' capabilities metadata is invalid: {details}."
    )
    related_field = "metadata"
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

            if capabilities_metadata.title != EXPECTED_CAPABILITIES_TITLE:
                details.append(
                    f"metadata.title must be '{EXPECTED_CAPABILITIES_TITLE}', "
                    f"got '{capabilities_metadata.title}'"
                )

            if capabilities_metadata.description != EXPECTED_CAPABILITIES_DESCRIPTION:
                details.append(
                    f"metadata.description must be "
                    f"'{EXPECTED_CAPABILITIES_DESCRIPTION}', got "
                    f"'{capabilities_metadata.description}'"
                )

            # metadata.help must be omitted, but only for grouped connectors.
            grouped = bool(connector.settings and connector.settings.grouped)
            if grouped and capabilities_metadata.help is not None:
                details.append("metadata.help must be omitted for grouped connectors.")

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

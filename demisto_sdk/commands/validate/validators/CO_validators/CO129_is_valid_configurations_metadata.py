from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# The two canonical strings the configurations.yaml metadata block MUST
# expose. See §3.7 of the manifest. The description here matches the
# de-facto value already used by ~328 of the 356 XSOAR-owned connectors
# on disk (the manifest text drops the trailing "settings" - we go with
# the disk consensus).
EXPECTED_CONFIGURATIONS_TITLE = "Configuration"
EXPECTED_CONFIGURATIONS_DESCRIPTION = "Adjust and refine your configuration settings"


class IsValidConfigurationsMetadataValidator(ConnectorsValidator[ContentTypes]):
    """CO129 - configurations.yaml metadata block must expose the two
    canonical strings.

    Rule: ``metadata.title == "Configuration"`` AND
    ``metadata.description == "Adjust and refine your configuration
    settings"``.

    Both grouped and standard connectors run this check. The single skip
    guard is a connector with NO ``configurations.yaml`` on disk - in
    which case there's nothing to validate.
    """

    error_code = "CO129"
    description = (
        "Validates the configurations.yaml metadata block: title must "
        "equal 'Configuration' and description must equal 'Adjust and "
        "refine your configuration settings' (§3.7)."
    )
    rationale = (
        "The configurations page presents a consistent, standardized "
        "experience across all connectors. Its title and description are "
        "fixed strings so operators recognize the page instantly."
    )
    error_message = (
        "Connector '{connector_id}' configurations metadata is invalid: " "{details}."
    )
    related_field = "metadata"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONFIGURATIONS]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            configurations_file = connector.configurations_file
            # No configurations.yaml at all -> nothing to validate.
            if not configurations_file.exist:
                continue

            raw = configurations_file.file_content or {}
            metadata = raw.get("metadata")
            if not isinstance(metadata, dict):
                # File exists but has no ``metadata`` mapping - report a
                # single aggregated error rather than crashing on
                # attribute access.
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details=("metadata block is missing or not a " "mapping"),
                        ),
                        content_object=connector,
                        path=configurations_file.file_path,
                    )
                )
                continue

            details: List[str] = []

            actual_title = metadata.get("title")
            if actual_title != EXPECTED_CONFIGURATIONS_TITLE:
                details.append(
                    f"metadata.title must be "
                    f"'{EXPECTED_CONFIGURATIONS_TITLE}', got "
                    f"'{actual_title}'"
                )

            actual_description = metadata.get("description")
            if actual_description != EXPECTED_CONFIGURATIONS_DESCRIPTION:
                details.append(
                    f"metadata.description must be "
                    f"'{EXPECTED_CONFIGURATIONS_DESCRIPTION}', got "
                    f"'{actual_description}'"
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
                        path=configurations_file.file_path,
                    )
                )

        return results

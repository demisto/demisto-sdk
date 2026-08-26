from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoConnectionGeneralConfigurationsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO119"
    description = (
        "Validates that grouped connectors do not declare a "
        "'general_configurations' block in connection.yaml."
    )
    rationale = (
        "In grouped connectors every connection field is scoped to a "
        "view_group (tile). A top-level general_configurations block in "
        "connection.yaml has no view_group binding and therefore cannot be "
        "rendered under any tile - it must instead be re-homed onto the "
        "appropriate per-view-group profile / configuration."
    )
    error_message = (
        "Grouped connector '{connector_id}' declares 'general_configurations' "
        "in connection.yaml. Grouped connectors must NOT declare "
        "'general_configurations' in connection.yaml - move those rows to "
        "the appropriate per-view-group profile/configuration instead."
    )
    related_field = "general_configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Grouped-only: short-circuit for non-grouped connectors.
            if not (connector.settings and connector.settings.grouped):
                continue

            # No connection.yaml at all - nothing to validate.
            connection = connector.connection
            if connection is None:
                continue

            if connection.general_configurations is None:
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                    ),
                    content_object=connector,
                    path=connector.connection_file.file_path,
                )
            )

        return results

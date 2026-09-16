from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class GroupedConnectorXSOAROnlyCapabilitiesValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO111"
    description = (
        "Validates that a grouped connector contains only XSOAR-owned handlers "
        "and capabilities."
    )
    rationale = (
        "Only XSOAR is permitted to use grouped connectors. Ownership is "
        "determined via the handler 'module: xsoar' field; any non-XSOAR "
        "handler (and therefore its capabilities) in a grouped connector is "
        "not allowed."
    )
    error_message = (
        "Grouped connector '{connector_id}' contains non-XSOAR handlers: "
        "{handlers}. Grouped connectors may only contain XSOAR-owned handlers "
        "and capabilities."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Grouped-only: short-circuit for non-grouped connectors.
            if not (connector.settings and connector.settings.grouped):
                continue

            non_xsoar_handlers = [
                handler.id for handler in connector.handlers if not handler.is_xsoar
            ]

            if non_xsoar_handlers:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handlers=", ".join(map(repr, sorted(non_xsoar_handlers))),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

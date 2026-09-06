from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

REQUIRED_TRIGGERING_TYPE = "PUB_SUB"


class IsHandlerMigrationConstantsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO170"
    description = (
        "Validates that every migrated XSOAR handler sets "
        '`triggering.type: "PUB_SUB"`'
    )
    rationale = (
        'The migration pipeline stamps `triggering.type: "PUB_SUB"` on '
        "every XSOAR handler as part of the XSOAR → ConnectUs conversion. "
        "This selects the event-driven runtime the platform expects for "
        "migrated handlers. Any deviation indicates either a bad migration "
        "or hand-editing that will confuse the platform, the content graph, "
        "and downstream tooling."
    )
    error_message = (
        "Handler '{handler_id}' violates migration constants: "
        "triggering.type must be {expected!r} (found {actual!r})."
    )
    related_field = "triggering.type"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Validate ``triggering.type == "PUB_SUB"`` on every XSOAR handler.

        Emits one result per offending handler with the path pointing at the
        offending ``handler.yaml``.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                triggering_type = handler.triggering.type
                if triggering_type == REQUIRED_TRIGGERING_TYPE:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            expected=REQUIRED_TRIGGERING_TYPE,
                            actual=triggering_type,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

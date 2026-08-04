from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

DESCRIPTION_TEMPLATE = "XSOAR handler for {name}."


class IsHandlerDescriptionTemplatedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO157"
    description = (
        "Validates that each XSOAR handler's metadata.description follows the "
        "template 'XSOAR handler for <name>.', where <name> is the "
        "name of the handler's related integration."
    )
    rationale = (
        "XSOAR handler descriptions are auto-generated from a fixed template "
        "so they stay consistent across all connectors. A description that "
        "deviates from 'XSOAR handler for <name>.' indicates the "
        "handler.yaml was edited manually or generated incorrectly."
    )
    error_message = (
        "Handler '{handler_id}' has an invalid metadata.description "
        "'{actual}'. Expected '{expected}'."
    )
    related_field = "metadata.description"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check each XSOAR handler's description against the template.

        A separate ``ValidationResult`` is emitted per failing handler (rather
        than one aggregated result per connector) so consumers can act on each
        handler individually. Each result's ``path`` points at the offending
        ``handler.yaml`` (mirroring how CO118 points at ``connection.yaml``).

        Handlers whose ``related_integration`` is not resolved are skipped -
        the expected ``<name>`` cannot be determined without it (that case is
        covered by CO164).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                integration = handler.related_integration
                if integration is None:
                    continue

                expected = DESCRIPTION_TEMPLATE.format(name=integration.name)
                actual = handler.metadata.description or ""

                if actual != expected:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                handler_id=handler.id,
                                actual=actual,
                                expected=expected,
                            ),
                            content_object=connector,
                            path=handler.file_path,
                        )
                    )

        return results

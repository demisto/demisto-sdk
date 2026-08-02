from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class HasSubCapabilityValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO112"
    description = (
        "Validates that every capability in a grouped connector declares at "
        "least one sub-capability."
    )
    rationale = (
        "In grouped connectors, handlers subscribe to sub-capabilities, so "
        "every capability must expose at least one sub-capability. A "
        "capability with no sub-capabilities cannot be subscribed to by any "
        "handler."
    )
    error_message = (
        "Grouped connector '{connector_id}' has capabilities with no "
        "sub-capabilities: {capabilities}. Each capability must declare at "
        "least one sub-capability."
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

            capabilities_without_sub = [
                capability.id
                for capability in connector.capabilities
                if not capability.sub_capabilities
            ]

            if capabilities_without_sub:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            capabilities=", ".join(
                                map(repr, sorted(capabilities_without_sub))
                            ),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

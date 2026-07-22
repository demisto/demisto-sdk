from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

XSOAR_CONTENT_MAINTAINER = "@xsoar-content"


class IsConnectorOwnershipFieldsAlignValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO100"
    description = (
        "Validates that a collected connector's "
        "metadata.ownership.maintainers contains the '@xsoar-content' "
        "maintainer."
    )
    rationale = (
        "Since a collected connector is assumed to have an XSOAR handler, its "
        "ownership must reflect that the XSOAR content team maintains it."
    )
    error_message = (
        "Connector '{connector_id}' metadata.ownership.maintainers must "
        "contain '{maintainer}'. Current maintainers: {maintainers}."
    )
    related_field = "metadata.ownership.maintainers"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            maintainers = connector.connector_metadata.ownership.maintainers
            if XSOAR_CONTENT_MAINTAINER not in maintainers:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            maintainer=XSOAR_CONTENT_MAINTAINER,
                            maintainers=maintainers or "[]",
                        ),
                        content_object=connector,
                    )
                )

        return results

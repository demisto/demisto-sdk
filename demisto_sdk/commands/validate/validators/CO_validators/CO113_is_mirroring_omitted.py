from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector

FORBIDDEN_MIRRORING_FIELDS = {"mirror_direction", "close_incident", "close_out"}


class IsMirroringOmittedValidator(BaseValidator[ContentTypes]):
    error_code = "CO113"
    description = (
        "Validates that mirroring parameters (mirror_direction, close_incident, "
        "close_out) are not present in the connector's capability configurations."
    )
    rationale = (
        "Mirroring is handled at the platform level and should not be exposed "
        "through connector capability configurations. Including these fields "
        "can cause conflicts with the platform's mirroring mechanism."
    )
    error_message = (
        "Connector '{connector_id}' contains forbidden mirroring fields "
        "in capability configurations: {details}"
    )
    related_field = "configurations"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            found: List[Tuple[str, str]] = []  # (field_id, capability_id)
            for cap in connector.capabilities:
                for fg in cap.configurations:
                    for field in fg.fields:
                        if field.id in FORBIDDEN_MIRRORING_FIELDS:
                            found.append((field.id, cap.id))
            if found:
                details = ", ".join(
                    f"'{fid}' in capability '{cid}'" for fid, cid in found
                )
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details=details,
                        ),
                        content_object=connector,
                    )
                )
        return results

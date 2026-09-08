"""CO134 - IsValidFetchCredentialsValidator.

Every handler that
subscribes to the ``fetch-secrets`` capability MUST emit the legacy
``isFetchCredentials: true`` backend flag via its ``serializer.yaml``
``computed_fields`` block, gated by a capability condition matching
the subscribed cap id with ``value == "on"``.

In UCP the ``isFetchCredentials`` user checkbox is removed (picking
the capability IS the opt-in. The backend flag is delivered exclusively via
serializer computed_fields.

Sibling of CO131 (feed serializer-flag only). Same shape - just
swap the constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
ContentTypes = Connector

# ============================================================
# CO134 constants
# ============================================================
FETCH_CREDENTIALS_CAPABILITY = "fetch-secrets"
FETCH_CREDENTIALS_FLAG = "isFetchCredentials"


class IsValidFetchCredentialsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO134"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`fetch-secrets` capability emits the `isFetchCredentials: "
        "true` backend flag via its serializer.yaml "
        "`computed_fields` block, gated on a capability condition."
    )
    rationale = (
        "The XSOAR BE needs the legacy `isFetchCredentials: true` "
        "flag to schedule the recurring secrets fetch job. In UCP "
        "the `isFetchCredentials` checkbox is removed (choosing the "
        "capability IS the opt-in - see CO145), so the flag must be "
        "emitted via serializer `computed_fields`. Without this "
        "gated computed_field, an instance with the fetch-secrets "
        "capability declared but no flag delivered will never fetch."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the '{capability}' capability but the fetch-credentials "
        "flag wiring is incomplete: {issues}"
    )
    related_field = "serializer"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            results.extend(self._collect_serializer_results(connector))
        return results

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in handler.capability_ids_matching(
                FETCH_CREDENTIALS_CAPABILITY
            ):
                if not handler.serializer_emits_capability_flag(
                    FETCH_CREDENTIALS_FLAG, cap_id
                ):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FETCH_CREDENTIALS_FLAG}: true' under a "
                        f"capability condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        capability=FETCH_CREDENTIALS_CAPABILITY,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=handler.serializer_path,
                )
            )
        return results


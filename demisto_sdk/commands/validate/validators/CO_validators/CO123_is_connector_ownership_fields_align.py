from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector

XSOAR_MAINTAINER_TAG = "@xsoar-content"


class IsConnectorOwnershipFieldsAlignValidator(BaseValidator[ContentTypes]):
    error_code = "CO123"
    description = (
        "Validates that any connector containing at least one XSOAR handler "
        "(module='xsoar' AND team='xsoar') has '@xsoar-content' in its "
        "connector-level metadata.ownership.maintainers field (exact, "
        "case-sensitive)."
    )
    rationale = (
        "When a connector exposes XSOAR-owned handlers, the connector itself "
        "must be co-maintained by the XSOAR Content team. The "
        "'@xsoar-content' tag in metadata.ownership.maintainers is the "
        "machine-readable signal that triggers XSOAR-only release-management, "
        "review, and CI behavior at the connector level. Without it, an "
        "XSOAR-handler connector is silently treated as third-party and "
        "skips those flows."
    )
    error_message = (
        "Connector '{connector_id}' contains at least one XSOAR handler "
        "({xsoar_handler_ids}) but its metadata.ownership.maintainers field "
        "is {issue} (got: {maintainers}).{case_hint}"
    )
    related_field = "metadata.ownership.maintainers"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check connector-level maintainers tag for XSOAR-handler connectors.

        Trigger gate: only validate connectors that have at least one XSOAR
        handler — `len(connector.xsoar_handlers) >= 1`. The `xsoar_handlers`
        property filters via `HandlerData.is_xsoar`, which requires BOTH
        `module=='xsoar'` AND `team=='xsoar'` (exact lowercase). Misaligned
        handlers (e.g., wrong team case) are NOT counted here — those are
        already caught by CO114 (IsHandlerOwnershipFieldsAlign).

        For triggered connectors, validate `metadata.ownership.maintainers`:
          R1. `'@xsoar-content'` (exact, case-sensitive) is in the list → pass
          R2. Missing entirely → error: "missing '@xsoar-content'"
          R3. A case-insensitive match exists (e.g., `'@XSOAR-Content'`) but
              not the exact tag → error with "case mismatch detected, fix the
              case" hint
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            if not (xsoar_handlers := connector.xsoar_handlers):
                # Trigger gate: no XSOAR handlers → nothing to validate
                continue

            maintainers = connector.connector_metadata.ownership.maintainers
            if XSOAR_MAINTAINER_TAG in maintainers:
                # R1 — happy path
                continue

            # R2/R3 — tag missing; check for a case-insensitive variant
            case_insensitive_match = any(
                m.lower() == XSOAR_MAINTAINER_TAG.lower() for m in maintainers
            )
            case_hint = (
                " Case mismatch detected, fix the case."
                if case_insensitive_match
                else ""
            )

            xsoar_handler_ids = ", ".join(f"'{h.id}'" for h in xsoar_handlers)
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        xsoar_handler_ids=xsoar_handler_ids,
                        issue=f"missing '{XSOAR_MAINTAINER_TAG}'",
                        maintainers=list(maintainers),
                        case_hint=case_hint,
                    ),
                    content_object=connector,
                )
            )

        return results

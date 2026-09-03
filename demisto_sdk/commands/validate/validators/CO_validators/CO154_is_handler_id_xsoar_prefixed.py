"""CO154 - IsHandlerIdXsoarPrefixedValidator.

Per §3.8 handler-naming rules, every XSOAR handler's ``id`` MUST
equal ``"xsoar-" + normalize_integration_id(related_integration.object_id)``.

Rationale
---------
XSOAR handlers are the runtime binding between a connector tile and
a specific XSOAR integration YML. The handler id has to be
mechanically derivable from the integration id so:

- Migration scripts can auto-name new handlers from the integration
  they replace.
- Downstream tooling (CO153 folder-name check, CO122 view_group
  match, CO164 label-vs-id verification) can cross-reference by
  integration without a separate mapping table.

The ``normalize_integration_id`` slug rule (CO113) is the same one
sub-capability ids use — a shared shape means "the id derived from
integration X" always yields the same slug, whether it lands as a
handler id, a sub-capability id, or anywhere else.

Scope
-----
Runs on every XSOAR-classified handler (``HandlerData.is_xsoar``).
Non-XSOAR handlers are skipped.

Two defects:

- ``unresolved-integration``: handler is XSOAR-classified but
  ``related_integration`` is None (cross-repo resolution failed).
  Emitted so the user knows why we can't check id conformance;
  structurally distinct from CO164 (which flags the same case for a
  different downstream concern — label-vs-id verification).
- ``id-mismatch``: handler id differs from the mechanically derived
  expected id.

Per-finding granularity: one ``ValidationResult`` per handler with a
defect. Path points at ``handler.yaml`` so
``.connector-ignore`` per-file suppressions resolve.
"""

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_sub_capability_id_derived import (
    normalize_integration_id,
)

ContentTypes = Connector

XSOAR_PREFIX = "xsoar-"


class IsHandlerIdXsoarPrefixedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO154"
    description = (
        "Every XSOAR handler's `id` MUST equal "
        "`xsoar-<normalize_integration_id(related_integration.object_id)>` "
        "so the handler id is mechanically derivable from the "
        "backing integration id (shared slug rule with CO113)."
    )
    rationale = (
        "The handler id is the runtime binding between a connector "
        "tile and a specific XSOAR integration YML. Anchoring it to "
        "a normalized derivation of the integration id lets "
        "migration scripts, CO153 folder-name checks, CO122 "
        "view_group resolution, and CO164 label-vs-id verification "
        "all cross-reference by integration without a separate "
        "mapping table. Drift here means every downstream "
        "cross-reference falls back to hand-maintained tables."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': XSOAR "
        "handler id must be 'xsoar-<normalized_integration_id>'. "
        "Expected '{expected}' (from integration '{integration_id}'), "
        "got '{handler_id}'. Rename the handler and its folder "
        "(CO153 will flag the folder rename separately)."
    )
    unresolved_message = (
        "Connector '{connector_id}' handler '{handler_id}': handler "
        "is XSOAR but no related integration is resolved — cannot "
        "verify id prefix conformance. Ensure the "
        "`xsoar-integration-id` label points at an integration in "
        "the content graph (see CO164)."
    )
    related_field = "id"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                integration = handler.related_integration
                if integration is None:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.unresolved_message.format(
                                connector_id=connector.object_id,
                                handler_id=handler.id,
                            ),
                            content_object=connector,
                            path=handler.file_path,
                        )
                    )
                    continue

                integration_id = getattr(integration, "object_id", None)
                if not isinstance(integration_id, str):
                    # Integration model exists but object_id is not a
                    # string — treat as unresolved.
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.unresolved_message.format(
                                connector_id=connector.object_id,
                                handler_id=handler.id,
                            ),
                            content_object=connector,
                            path=handler.file_path,
                        )
                    )
                    continue

                expected = XSOAR_PREFIX + normalize_integration_id(integration_id)
                if handler.id == expected:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            expected=expected,
                            integration_id=integration_id,
                        ),
                        content_object=connector,
                        path=handler.file_path,
                    )
                )

        return results

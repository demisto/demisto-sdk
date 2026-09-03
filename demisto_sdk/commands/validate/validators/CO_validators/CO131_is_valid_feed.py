"""CO131 - IsValidFeedValidator (SCOPED-DOWN v1).

Per §3.9.1 of the standard connector guide, every handler that
subscribes to the ``threat-intelligence-and-enrichment`` (TI&E)
capability MUST emit the legacy ``feed: true`` backend flag via its
``serializer.yaml`` ``computed_fields`` block, gated by a capability
condition. In UCP the user-visible ``feed`` checkbox is removed
(picking the capability IS the opt-in - see CO145), so the flag
must be delivered via serializer ``computed_fields``.

**Scope (v1):** this validator only checks the serializer-flag half.
The full CO131 spec also requires 6 user-visible parameters
(``feedFetchInterval``, ``feedReputation``, ``feedReliability``,
``feedExpirationPolicy``, ``feedExpirationInterval``,
``feedBypassExclusionList``) to exist in ``configurations.yaml``
under the TI&E capability entry. That half is DEFERRED - see the
"PARTIAL" note in ``Manifest validations.md`` next to CO131; a
follow-up decision is pending on whether to enforce presence of
those 6 params.

Mirrors CO130's Part-1 shape (the ``_collect_serializer_results``
method): iterate every XSOAR handler subscribing to the TI&E cap
(bare id or ``<base_id>_<suffix>`` grouped variant), then check
``handler.serializer.computed_fields`` for a rule that emits
``feed: true`` gated on a ``type: capability`` condition matching
the subscribed cap id with ``value == "on"``.

Result granularity: one ``ValidationResult`` per offending handler
(same as CO130), ``path`` = handler's ``serializer.yaml`` so the
``.connector-ignore`` per-handler chain
(``[file:<handler-folder>/serializer.yaml]``) resolves cleanly.

Reuses ``iter_handler_capability_ids`` and
``computed_field_emits_flag`` from CO130 to avoid duplication.
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
from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
    computed_field_emits_flag,
    iter_handler_capability_ids,
)

ContentTypes = Connector

# ============================================================
# CO131 constants
# ============================================================
FEED_CAPABILITY = "threat-intelligence-and-enrichment"
FEED_FLAG = "feed"


# ============================================================
# CO131 validator
# ============================================================
class IsValidFeedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO131"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`threat-intelligence-and-enrichment` capability emits the "
        "`feed: true` backend flag via its serializer.yaml "
        "`computed_fields` block, gated on a capability condition. "
        "Scoped-down v1: only the serializer-flag half is enforced; "
        "presence of the 6 user-visible feed params in "
        "configurations.yaml (feedFetchInterval, feedReputation, "
        "feedReliability, feedExpirationPolicy, feedExpirationInterval, "
        "feedBypassExclusionList) is DEFERRED pending decision - see "
        "the PARTIAL note in the Manifest validations tracker."
    )
    rationale = (
        "The XSOAR BE is capability-agnostic - it still needs the "
        "legacy `feed: true` flag to schedule the recurring TI&E "
        "fetch job. In UCP the `feed` checkbox is removed (choosing "
        "the capability IS the opt-in - see CO145), so the flag must "
        "be emitted via serializer `computed_fields`. Without this "
        "gated computed_field, an instance with the TI&E capability "
        "declared but no `feed: true` delivered will never actually "
        "fetch feeds."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the '{capability}' capability but the feed-flag wiring "
        "is incomplete: {issues}"
    )
    related_field = "serializer"
    is_auto_fixable = False
    # Two file types feed independent ignore chains (mirrors CO130's
    # NOTE): CONNECTOR_SERIALIZER for the preflight
    # ``[file:<handler>/serializer.yaml]`` lookup, CONNECTOR_HANDLER
    # for the post-hoc per-handler filter in
    # ``ValidateManager.filter_validation_results``. Without both,
    # per-handler ignore entries won't reliably suppress CO131.
    related_file_type = [
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per handler that subscribes to
        the TI&E capability but is missing the ``feed: true``
        computed_fields rule.

        Path routes to the handler's ``serializer.yaml`` (via
        ``_serializer_path``) so
        ``ValidateManager.filter_validation_results`` routes each
        finding through the per-handler ignore lookup, which resolves
        ``[file:<handler-folder>/serializer.yaml]``. Same pattern as
        CO130 Part 1 / CO171 / CO172.
        """
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
            for cap_id in iter_handler_capability_ids(handler, FEED_CAPABILITY):
                if not computed_field_emits_flag(handler, FEED_FLAG, cap_id):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FEED_FLAG}: true' under a capability "
                        f"condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        capability=FEED_CAPABILITY,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=self._serializer_path(handler),
                )
            )
        return results

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[Path]:
        """Best-effort path to the handler's ``serializer.yaml``.

        Mirrors CO130 / CO171 / CO172 so the per-handler ignore key
        (``<handler-folder>/serializer.yaml``) resolves the same way.
        Falls back to ``None`` if the handler's on-disk location
        can't be determined; downstream per-handler ignore lookup
        handles ``None`` gracefully (safe default: not ignored).
        """
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"

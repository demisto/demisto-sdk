"""CO133 - IsValidFetchEventsValidator.

Every handler that subscribes to the ``log-collection`` capability MUST:

1. Emit the legacy ``isFetchEvents: true`` backend flag via its
   ``serializer.yaml`` ``computed_fields`` block, gated by a
   capability condition matching the subscribed cap id with
   ``value == "on"``. In UCP the ``isFetchEvents`` user checkbox
   is removed (picking the capability IS the opt-in - CO145 owns
   the "must not emit as user checkbox" side); the backend flag
   is delivered exclusively via serializer computed_fields.

2. Have an ``eventFetchInterval`` field that is visible to the
   handler at runtime from a ``configurations.yaml`` surface (the
   per-cap entry or ``general_configurations``). Without this field
   the user has no way to control how frequently events are
   fetched. Runtime-name matched (via serializer field_mappings)
   so grouped connectors that authored the field under a namespaced
   id (e.g. ``xsoar-akamai-waf-siem_eventFetchInterval``) and
   renamed it back are correctly recognised.


Result granularity: one ``ValidationResult`` per (handler, defect)
finding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    FieldOrigin,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
ContentTypes = Connector

# ============================================================
# CO133 constants
# ============================================================
FETCH_EVENTS_CAPABILITY = "log-collection"
FETCH_EVENTS_FLAG = "isFetchEvents"
FETCH_EVENTS_INTERVAL_FIELD = "eventFetchInterval"

# The interval field is a per-connector user knob, so only
# configurations.yaml surfaces count as satisfying it.
_CONFIGURATIONS_YAML_ORIGINS = frozenset(
    {
        FieldOrigin.CONFIGURATIONS_GENERAL,
        FieldOrigin.CONFIGURATIONS_CAPABILITY,
    }
)


class IsValidFetchEventsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO133"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`log-collection` capability emits `isFetchEvents: true` via "
        "its serializer.yaml `computed_fields`, and that "
        "`eventFetchInterval` is a user-visible field in "
        "configurations.yaml so the user can control fetch frequency."
    )
    rationale = (
        "The XSOAR BE needs the legacy `isFetchEvents: true` flag "
        "to schedule the recurring events fetch job; the flag is "
        "delivered via serializer `computed_fields` since the user "
        "checkbox is removed (CO145). Independently, "
        "`eventFetchInterval` must be a user-visible field so the "
        "customer can tune fetch cadence - a log-collection "
        "capability without it would be uncontrollable."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the '{capability}' capability but fetch-events wiring "
        "is incomplete: {issues}"
    )
    related_field = "serializer"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            results.extend(self._collect_serializer_results(connector))
            results.extend(self._collect_interval_field_results(connector))
        return results

    # ------------------------------------------------------------------
    # Serializer half - ``isFetchEvents: true`` computed_field rule.
    # ------------------------------------------------------------------

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in handler.capability_ids_matching(FETCH_EVENTS_CAPABILITY):
                if not handler.serializer_emits_capability_flag(
                    FETCH_EVENTS_FLAG, cap_id
                ):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FETCH_EVENTS_FLAG}: true' under a capability "
                        f"condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        capability=FETCH_EVENTS_CAPABILITY,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=handler.serializer_path,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Interval-field half - ``eventFetchInterval`` must be visible to
    # the handler at runtime from a configurations.yaml surface (either
    # the per-cap entry or general_configurations). The walker resolves
    # per-handler serializer renames and grouped sub-cap visibility so
    # a namespaced authored id (e.g.
    # ``xsoar-akamai-waf-siem_eventFetchInterval``) that the handler's
    # serializer renames back to ``eventFetchInterval`` is correctly
    # recognised.
    #
    # Collapsed message shape (matches CO132's Phase 2 migration):
    # "no visible '<field>' field in configurations.yaml" — the old
    # split between "no cap entry" and "cap entry missing field" no
    # longer maps onto the walker output (walker unifies both under
    # "not present in the handler's visible surface").
    # ------------------------------------------------------------------

    def _collect_interval_field_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        cfg_file = connector.configurations_file
        cfg_path: Optional[Path] = getattr(cfg_file, "file_path", None)

        # One error per (subscribed cap id) across the connector,
        # deduplicated across handlers that subscribe to the same cap.
        cap_ids_missing_interval: Set[str] = set()

        for handler in connector.xsoar_handlers:
            subscribed_cap_ids = list(
                handler.capability_ids_matching(FETCH_EVENTS_CAPABILITY)
            )
            if not subscribed_cap_ids:
                continue

            if self._handler_sees_interval_in_configurations(connector, handler):
                continue

            for cap_id in subscribed_cap_ids:
                cap_ids_missing_interval.add(cap_id)

        for cap_id in sorted(cap_ids_missing_interval):
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        capability=FETCH_EVENTS_CAPABILITY,
                        issues=(
                            f"capability '{cap_id}' has no visible "
                            f"'{FETCH_EVENTS_INTERVAL_FIELD}' field in "
                            f"configurations.yaml (users need it to "
                            f"control events-fetch cadence); declare it "
                            f"under the `configurations[]` entry for "
                            f"'{cap_id}' or under `general_configurations`"
                        ),
                    ),
                    content_object=connector,
                    path=cfg_path,
                )
            )

        return results

    @staticmethod
    def _handler_sees_interval_in_configurations(
        connector: Connector, handler: HandlerData
    ) -> bool:
        """True iff ``eventFetchInterval`` is a user-visible field on
        the handler from ANY ``configurations.yaml`` surface (the
        per-cap entry or ``general_configurations``).

        Matches on ``runtime_name`` (post-serializer), so grouped
        connectors that authored the field under a namespaced id and
        renamed it back via ``serializer.yaml`` are recognised.
        """
        for vf in connector.visible_fields_for_handler(handler):
            if vf.origin not in _CONFIGURATIONS_YAML_ORIGINS:
                continue
            if vf.runtime_name == FETCH_EVENTS_INTERVAL_FIELD:
                return True
        return False

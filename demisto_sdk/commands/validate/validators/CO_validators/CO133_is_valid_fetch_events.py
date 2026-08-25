"""CO133 - IsValidFetchEventsValidator.

Per §3.9.1 of the standard connector guide, every handler that
subscribes to the ``log-collection`` capability MUST:

1. Emit the legacy ``isFetchEvents: true`` backend flag via its
   ``serializer.yaml`` ``computed_fields`` block, gated by a
   capability condition matching the subscribed cap id with
   ``value == "on"``. In UCP the ``isFetchEvents`` user checkbox
   is removed (picking the capability IS the opt-in - CO145 owns
   the "must not emit as user checkbox" side); the backend flag
   is delivered exclusively via serializer computed_fields.

2. Have an ``eventFetchInterval`` field declared in
   ``configurations.yaml`` under the capability entry (bare id or
   grouped-namespaced variant, e.g. ``log-collection_akamai-waf-siem``).
   Without this field the user has no way to control how frequently
   events are fetched.

Sibling of CO132 (fetch-assets). The two validators share the same
shape and both reuse ``_find_cap_entry`` + ``_entry_has_field``
helpers from CO132 to walk configurations.yaml consistently.

Result granularity: one ``ValidationResult`` per (handler, defect)
finding. See CO132's module docstring for the design details
(raw-YAML walkers, per-handler serializer routing, CO171 overlap
rationale).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

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
from demisto_sdk.commands.validate.validators.CO_validators.CO132_is_valid_fetch_assets import (
    _entry_has_field,
    _find_cap_entry,
)

ContentTypes = Connector

# ============================================================
# CO133 constants
# ============================================================
FETCH_EVENTS_CAPABILITY = "log-collection"
FETCH_EVENTS_FLAG = "isFetchEvents"
FETCH_EVENTS_INTERVAL_FIELD = "eventFetchInterval"


class IsValidFetchEventsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO133"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`log-collection` capability emits `isFetchEvents: true` via "
        "its serializer.yaml `computed_fields`, and that the "
        "capability's `configurations.yaml` entry declares the "
        "`eventFetchInterval` field so the user can control fetch "
        "frequency."
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
            results.extend(self._collect_configurations_results(connector))
        return results

    # ------------------------------------------------------------------
    # Serializer half
    # ------------------------------------------------------------------

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in iter_handler_capability_ids(
                handler, FETCH_EVENTS_CAPABILITY
            ):
                if not computed_field_emits_flag(
                    handler, FETCH_EVENTS_FLAG, cap_id
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
                    path=self._serializer_path(handler),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Configurations half
    # ------------------------------------------------------------------

    def _collect_configurations_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        subscribed_cap_ids: Set[str] = set()
        for handler in connector.xsoar_handlers:
            for cap_id in iter_handler_capability_ids(
                handler, FETCH_EVENTS_CAPABILITY
            ):
                subscribed_cap_ids.add(cap_id)

        if not subscribed_cap_ids:
            return results

        raw = connector.configurations_file.file_content
        cfg_path = connector.configurations_file.file_path
        for cap_id in sorted(subscribed_cap_ids):
            entry = _find_cap_entry(raw, cap_id)
            if entry is None:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            capability=FETCH_EVENTS_CAPABILITY,
                            issues=(
                                f"capability '{cap_id}' has no "
                                f"`configurations[]` entry in "
                                f"configurations.yaml - the entry is "
                                f"required to declare the "
                                f"'{FETCH_EVENTS_INTERVAL_FIELD}' field"
                            ),
                        ),
                        content_object=connector,
                        path=cfg_path,
                    )
                )
                continue
            if not _entry_has_field(entry, FETCH_EVENTS_INTERVAL_FIELD):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            capability=FETCH_EVENTS_CAPABILITY,
                            issues=(
                                f"capability '{cap_id}' entry in "
                                f"configurations.yaml is missing the "
                                f"required '{FETCH_EVENTS_INTERVAL_FIELD}' "
                                f"field (users need it to control "
                                f"events-fetch cadence)"
                            ),
                        ),
                        content_object=connector,
                        path=cfg_path,
                    )
                )

        return results

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[Path]:
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"

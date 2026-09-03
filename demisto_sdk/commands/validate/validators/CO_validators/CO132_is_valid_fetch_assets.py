"""CO132 - IsValidFetchAssetsValidator.

Per §3.9.1 of the standard connector guide, every handler that
subscribes to the ``fetch-assets-and-vulnerabilities`` capability
MUST:

1. Emit the legacy ``isFetchAssets: true`` backend flag via its
   ``serializer.yaml`` ``computed_fields`` block, gated by a
   capability condition matching the subscribed cap id with
   ``value == "on"``. In UCP the ``isFetchAssets`` user checkbox
   is removed (picking the capability IS the opt-in - CO145 owns
   the "must not emit as user checkbox" side); the backend flag
   is delivered exclusively via serializer computed_fields.

2. Have an ``assetsFetchInterval`` field declared in
   ``configurations.yaml`` under the capability entry (bare id or
   grouped-namespaced variant). Without this field the user has no
   way to control how frequently assets are fetched.

Mirrors:

- CO131 (v1, feed-flag) for the serializer half. Reuses
  ``iter_handler_capability_ids`` + ``computed_field_emits_flag``
  from CO130.
- CO145 for the raw-YAML walker approach on the configurations.yaml
  half. This is required (rather than reading
  ``handler.resolved_params``) because
  ``ConnectorParser._parse_capabilities_with_configs`` merges
  configurations entries by PARENT capability id, and grouped
  connectors write per-cap entries keyed by SUB-capability id
  (e.g. ``fetch-assets-and-vulnerabilities_myvendor``). Reading
  ``resolved_params`` for grouped connectors would silently miss
  the sub-cap entries. Reading raw ``configurations_file.file_content``
  matches the author's actual YAML shape.

Result granularity: one ``ValidationResult`` per (handler, defect)
finding. The serializer half's ``path`` = handler's
``serializer.yaml`` (per-handler ignore chain resolves cleanly);
the configurations half's ``path`` = ``configurations.yaml``
(connector-scoped ignore key).

Serializer-flag half overlaps CO171 (which enforces the same
mapping for all 5 collection caps). Keeping CO132 separate gives
authors a per-capability error code and preserves symmetry with
CO130/CO131/CO133/CO134.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

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
# CO132 constants
# ============================================================
FETCH_ASSETS_CAPABILITY = "fetch-assets-and-vulnerabilities"
FETCH_ASSETS_FLAG = "isFetchAssets"
FETCH_ASSETS_INTERVAL_FIELD = "assetsFetchInterval"


# ============================================================
# CO132 validator
# ============================================================
class IsValidFetchAssetsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO132"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`fetch-assets-and-vulnerabilities` capability emits "
        "`isFetchAssets: true` via its serializer.yaml "
        "`computed_fields`, and that the capability's "
        "`configurations.yaml` entry declares the "
        "`assetsFetchInterval` field so the user can control fetch "
        "frequency."
    )
    rationale = (
        "The XSOAR BE needs the legacy `isFetchAssets: true` flag "
        "to schedule the recurring assets fetch job; the flag is "
        "delivered via serializer `computed_fields` since the user "
        "checkbox is removed (CO145). Independently, "
        "`assetsFetchInterval` must be a user-visible field so the "
        "customer can tune fetch cadence - a fetch-assets capability "
        "without it would be uncontrollable."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the '{capability}' capability but fetch-assets wiring "
        "is incomplete: {issues}"
    )
    related_field = "serializer"
    is_auto_fixable = False
    # Two file types feed independent ignore chains (same rationale
    # documented on CO130):
    #   - CONNECTOR_SERIALIZER for the serializer-flag half's
    #     ``[file:<handler>/serializer.yaml]`` preflight,
    #   - CONNECTOR_HANDLER for the post-hoc per-handler filter,
    #   - CONNECTOR_CONFIGURATIONS for the interval-field half's
    #     ``[file:configurations.yaml]`` preflight.
    related_file_type = [
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, defect) finding.

        Two halves per handler, each emitted independently:
        - Serializer half: missing/misshaped ``isFetchAssets: true``
          computed_field rule for a subscribed cap id.
          ``path = <handler>/serializer.yaml``.
        - Configurations half: missing ``assetsFetchInterval`` field
          under the cap's ``configurations[]`` entry.
          ``path = configurations.yaml``.
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            results.extend(self._collect_serializer_results(connector))
            results.extend(self._collect_configurations_results(connector))
        return results

    # ------------------------------------------------------------------
    # Serializer half (mirrors CO131 / CO130 Part 1)
    # ------------------------------------------------------------------

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in iter_handler_capability_ids(handler, FETCH_ASSETS_CAPABILITY):
                if not computed_field_emits_flag(handler, FETCH_ASSETS_FLAG, cap_id):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FETCH_ASSETS_FLAG}: true' under a capability "
                        f"condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        capability=FETCH_ASSETS_CAPABILITY,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=self._serializer_path(handler),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Configurations half (walks raw configurations.yaml file_content
    # to sidestep the parent-id-only merge in the parser - same as CO145)
    # ------------------------------------------------------------------

    def _collect_configurations_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        """Emit one result per capability entry missing
        ``assetsFetchInterval``.

        Deduplicates across handlers that subscribe to the same cap id
        (the underlying `configurations[]` entry is shared - the same
        defect would surface once per handler otherwise).
        """
        results: List[ValidationResult] = []

        # Collect unique cap ids subscribed by ANY XSOAR handler.
        subscribed_cap_ids: Set[str] = set()
        for handler in connector.xsoar_handlers:
            for cap_id in iter_handler_capability_ids(handler, FETCH_ASSETS_CAPABILITY):
                subscribed_cap_ids.add(cap_id)

        if not subscribed_cap_ids:
            return results

        raw = connector.configurations_file.file_content
        cfg_path = connector.configurations_file.file_path
        # For each subscribed cap id, look for a matching
        # configurations[] entry and check for assetsFetchInterval.
        # A missing entry OR a present entry without the field both
        # fail; the message distinguishes the two.
        for cap_id in sorted(subscribed_cap_ids):
            entry = _find_cap_entry(raw, cap_id)
            if entry is None:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            capability=FETCH_ASSETS_CAPABILITY,
                            issues=(
                                f"capability '{cap_id}' has no "
                                f"`configurations[]` entry in "
                                f"configurations.yaml - the entry is "
                                f"required to declare the "
                                f"'{FETCH_ASSETS_INTERVAL_FIELD}' field"
                            ),
                        ),
                        content_object=connector,
                        path=cfg_path,
                    )
                )
                continue
            if not _entry_has_field(entry, FETCH_ASSETS_INTERVAL_FIELD):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            capability=FETCH_ASSETS_CAPABILITY,
                            issues=(
                                f"capability '{cap_id}' entry in "
                                f"configurations.yaml is missing the "
                                f"required '{FETCH_ASSETS_INTERVAL_FIELD}' "
                                f"field (users need it to control "
                                f"assets-fetch cadence)"
                            ),
                        ),
                        content_object=connector,
                        path=cfg_path,
                    )
                )

        return results

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[Path]:
        """Best-effort path to the handler's ``serializer.yaml``.
        Mirrors CO130 / CO131 / CO171 / CO172 so per-handler ignore
        keys (``<handler-folder>/serializer.yaml``) resolve cleanly.
        """
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"


# ============================================================
# Module-level helpers (shared with CO133 - both walk
# configurations.yaml the same way looking for a specific field
# under a per-cap entry).
# ============================================================


def _find_cap_entry(raw: Any, cap_id: str) -> Optional[Dict[str, Any]]:
    """Return the raw ``configurations[]`` entry dict whose ``id``
    equals ``cap_id``, or ``None`` if not present / raw is malformed.

    Mirrors ``CO130.find_capability_config_entry`` but takes the raw
    file_content directly (so callers with the raw dict in hand don't
    round-trip through the connector object).
    """
    if not isinstance(raw, dict):
        return None
    entries = raw.get("configurations")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == cap_id:
            return entry
    return None


def _entry_has_field(entry: Dict[str, Any], field_id: str) -> bool:
    """True if any ``fields[]`` block under
    ``entry.configurations[*]`` contains a field with the given id.

    Walks the standard shape:
        entry.configurations[*].fields[*].id == field_id
    """
    groups = entry.get("configurations")
    if not isinstance(groups, list):
        return False
    for group in groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field in fields:
            if isinstance(field, dict) and field.get("id") == field_id:
                return True
    return False

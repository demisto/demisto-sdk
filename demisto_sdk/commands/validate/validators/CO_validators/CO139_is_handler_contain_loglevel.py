"""CO139 - every XSOAR handler must be reachable by an
`integrationLogLevel` field under `configurations.yaml`
`general_configurations`.

Per guide §3.7 "Canonical `integrationLogLevel` block" + Appendix J:
`integrationLogLevel` is a connector-wide, backend-managed `select`
field that lives ONCE in `configurations.yaml`
`general_configurations.configurations[]`, wrapped in a field group
gated by `required_for_capabilities`.

The shape / placement differs between standard and grouped connectors:

**Standard connectors** (`settings.grouped != true`)
    - ONE (or more) `general_configurations.configurations[]` entries
      contain a field whose runtime id (post-serializer) is
      `integrationLogLevel`.
    - Each entry carries `required_for_capabilities: [...]`.
    - The UNION of `required_for_capabilities` across those entries
      MUST cover every capability id any XSOAR handler subscribes to.

**Grouped connectors** (`settings.grouped == true`)
    - ONE `general_configurations.configurations[]` entry per view_group
      (per integration tile), each with `view_group: <tile-id>` and
      `advanced: true`.
    - Each entry contains an `integrationLogLevel` field (runtime id
      after serializer resolution).
    - Per XSOAR handler we resolve the handler's view_group id from
      ``handler.related_integration.object_id`` (same pattern as
      CO122) and verify a matching entry exists.

**Field-shape sub-checks common to both**:
    - `field_type: select`
    - `metadata.xsoar.config_type: backend`
    - `options.searchable: true`, `options.clearable: true`
    - `options.values` keys include `Off`, `Debug`, `Verbose`

Skip only if the connector has NO XSOAR handlers OR NO
configurations.yaml. If XSOAR handlers exist but no
`integrationLogLevel` is found anywhere, that's a hard failure —
never a silent skip.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
    _field_config_type,
    _runtime_id,
    _serializer_rename_map,
)

ContentTypes = Connector

# ============================================================
# CO139 constants
# ============================================================
INTEGRATION_LOG_LEVEL_ID = "integrationLogLevel"
EXPECTED_FIELD_TYPE = "select"
EXPECTED_CONFIG_TYPE = "backend"
EXPECTED_VALUES_KEYS: Set[str] = {"Off", "Debug", "Verbose"}


def _normalize_id(value: str) -> str:
    """Same alphanumeric-only normalization as CO122's view_group id
    match. Lowercase + strip every non-alphanumeric character so
    ``"Palo Alto Networks Threat Vault v2"`` and
    ``"palo-alto-networks-threat-vault-v2"`` collapse to the same
    canonical form.
    """
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


# ============================================================
# Traversal helpers
# ============================================================
def _iter_general_config_groups(
    connector: Connector,
) -> Iterable[Dict[str, Any]]:
    """Yield every raw field-group dict from
    ``configurations.yaml`` `general_configurations.configurations[]`.
    Returns nothing if configurations.yaml is missing.
    """
    conf_file = connector.configurations_file
    if not conf_file.exist:
        return
    raw = conf_file.file_content
    if not isinstance(raw, dict):
        return
    gc = raw.get("general_configurations")
    if not isinstance(gc, dict):
        return
    groups = gc.get("configurations")
    if not isinstance(groups, list):
        return
    for group in groups:
        if isinstance(group, dict):
            yield group


def _combined_rename_map(connector: Connector) -> Dict[str, str]:
    """Combine `field_mappings` renames across ALL XSOAR handlers so a
    single ``integrationLogLevel`` field id lookup can canonicalize
    namespaced ids from any handler's serializer."""
    combined: Dict[str, str] = {}
    for handler in connector.xsoar_handlers:
        combined.update(_serializer_rename_map(handler))
    return combined


def _group_has_integration_log_level(
    group: Dict[str, Any], rename_map: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """Return the raw field dict whose runtime id (post-serializer) is
    ``integrationLogLevel`` inside ``group.fields[]``, or None."""
    fields = group.get("fields")
    if not isinstance(fields, list):
        return None
    for field in fields:
        if not isinstance(field, dict):
            continue
        raw_id = field.get("id")
        if not isinstance(raw_id, str):
            continue
        if _runtime_id(raw_id, rename_map) == INTEGRATION_LOG_LEVEL_ID:
            return field
    return None


# ============================================================
# Field-shape sub-checks (common to both shapes)
# ============================================================
def _check_log_level_field_shape(field: Dict[str, Any], where: str) -> List[str]:
    """Return a list of shape sub-rule failures for
    ``integrationLogLevel`` field. ``where`` is a locator string used
    in messages (e.g. "general_configurations entry #1" /
    "view_group 'qualysfim'")."""
    issues: List[str] = []
    prefix = f"integrationLogLevel in {where}"

    actual_type = field.get("field_type")
    if actual_type != EXPECTED_FIELD_TYPE:
        issues.append(
            f"{prefix}: field_type='{actual_type}' but must be "
            f"'{EXPECTED_FIELD_TYPE}'"
        )

    actual_ct = _field_config_type(field)
    if actual_ct != EXPECTED_CONFIG_TYPE:
        issues.append(
            f"{prefix}: metadata.xsoar.config_type='{actual_ct}' but "
            f"must be '{EXPECTED_CONFIG_TYPE}'"
        )

    options = field.get("options")
    if not isinstance(options, dict):
        issues.append(f"{prefix}: `options` mapping is missing")
        return issues

    if options.get("searchable") is not True:
        issues.append(
            f"{prefix}: options.searchable={options.get('searchable')!r} "
            f"but must be True"
        )
    if options.get("clearable") is not True:
        issues.append(
            f"{prefix}: options.clearable={options.get('clearable')!r} "
            f"but must be True"
        )

    values = options.get("values")
    keys: Set[str] = set()
    if isinstance(values, list):
        for v in values:
            if isinstance(v, dict):
                k = v.get("key")
                if isinstance(k, str):
                    keys.add(k)
    missing = EXPECTED_VALUES_KEYS - keys
    if missing:
        issues.append(
            f"{prefix}: options.values is missing keys "
            f"{sorted(missing)!r} (expected all of "
            f"{sorted(EXPECTED_VALUES_KEYS)!r})"
        )

    return issues


# ============================================================
# CO139 validator
# ============================================================
class IsHandlerContainLoglevelValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO139"
    description = (
        "Validates that every XSOAR handler is reachable by an "
        "`integrationLogLevel` (select, config_type=backend) field "
        "under `configurations.yaml` `general_configurations`. For "
        "standard connectors the field's containing field-group's "
        "`required_for_capabilities` must (in aggregate across all "
        "such entries) cover every capability id XSOAR handlers "
        "subscribe to. For grouped connectors, each XSOAR handler's "
        "view_group must have its own `general_configurations` entry "
        "with `advanced: true` containing the field. Namespaced "
        "field ids are canonicalized via serializer.yaml "
        "`field_mappings` before matching."
    )
    rationale = (
        "The backend cannot honor per-handler log-level controls "
        "without the `integrationLogLevel` backend-managed field. In "
        "standard connectors this is a single shared field gated per "
        "capability via `required_for_capabilities`; in grouped "
        "connectors each integration/tile needs its own advanced "
        "entry gated by `view_group`. Missing or mis-scoped log-level "
        "wiring means users cannot set Debug/Verbose logging for the "
        "affected integration(s) without touching every capability's "
        "config."
    )
    error_message = (
        "Connector '{connector_id}': integrationLogLevel wiring is "
        "incomplete: {issues}"
    )
    related_field = "integrationLogLevel"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONFIGURATIONS]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            issues = self._check_connector(connector)
            if not issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(issues),
                    ),
                    content_object=connector,
                    path=connector.configurations_file.file_path,
                )
            )
        return results

    def _check_connector(self, connector: Connector) -> List[str]:
        """Return aggregated issue strings, or empty list if all good."""
        xsoar_handlers = list(connector.xsoar_handlers)
        if not xsoar_handlers:
            return []  # No XSOAR ownership -> not our concern.

        conf_file = connector.configurations_file
        if not conf_file.exist:
            return []  # No configurations.yaml -> other validators
            # cover the missing-file case; nothing to check here.

        rename_map = _combined_rename_map(connector)
        # Find all general_config groups that contain integrationLogLevel.
        matching: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for group in _iter_general_config_groups(connector):
            field = _group_has_integration_log_level(group, rename_map)
            if field is not None:
                matching.append((group, field))

        if not matching:
            return [
                "connector has XSOAR handler(s) but no "
                "`integrationLogLevel` field is declared in "
                "configurations.yaml `general_configurations` (checked "
                "runtime ids after serializer field_mappings "
                "resolution)"
            ]

        is_grouped = bool(connector.settings and connector.settings.grouped)
        if is_grouped:
            return self._check_grouped(connector, xsoar_handlers, matching)
        return self._check_standard(xsoar_handlers, matching)

    # ---------- standard ----------
    def _check_standard(
        self,
        xsoar_handlers: List[HandlerData],
        matching: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    ) -> List[str]:
        issues: List[str] = []

        # Union of required_for_capabilities across all matching entries.
        declared: Set[str] = set()
        for group, _ in matching:
            rfc = group.get("required_for_capabilities")
            if isinstance(rfc, list):
                for c in rfc:
                    if isinstance(c, str):
                        declared.add(c)

        # Union of capability ids XSOAR handlers subscribe to. Standard
        # connectors don't use grouped-namespaced ids so cap.id is
        # authoritative.
        needed: Set[str] = set()
        for handler in xsoar_handlers:
            for cap in handler.capabilities:
                if isinstance(cap.id, str):
                    needed.add(cap.id)

        missing = needed - declared
        if missing:
            issues.append(
                f"standard connector: integrationLogLevel "
                f"`required_for_capabilities` (aggregated across all "
                f"general_configurations entries: {sorted(declared)!r}) "
                f"does not cover XSOAR-handler capabilities "
                f"{sorted(missing)!r}"
            )

        # Field-shape checks on each matching field.
        for idx, (_, field) in enumerate(matching, start=1):
            where = f"general_configurations entry #{idx}"
            issues.extend(_check_log_level_field_shape(field, where))

        return issues

    # ---------- grouped ----------
    def _check_grouped(
        self,
        connector: Connector,
        xsoar_handlers: List[HandlerData],
        matching: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    ) -> List[str]:
        issues: List[str] = []

        # Index matching entries by NORMALIZED view_group id (same
        # lenient alphanumeric-only rule as CO122: developer-facing
        # ids can drift stylistically as long as they collapse to the
        # same canonical form).
        by_vg: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
        for group, field in matching:
            vg = group.get("view_group")
            if isinstance(vg, str):
                by_vg[_normalize_id(vg)] = (group, field)

        checked_shape_for_vgs: Set[str] = set()
        for handler in xsoar_handlers:
            integration = handler.related_integration
            if integration is None:
                issues.append(
                    f"XSOAR handler '{handler.id}' has no resolved "
                    f"integration; cannot verify view_group binding "
                    f"for integrationLogLevel"
                )
                continue
            vg_id = integration.object_id
            vg_key = _normalize_id(vg_id)
            entry = by_vg.get(vg_key)
            if entry is None:
                issues.append(
                    f"grouped connector: XSOAR handler '{handler.id}' "
                    f"(integration '{vg_id}') has no "
                    f"general_configurations entry whose view_group id "
                    f"normalizes to '{vg_key}' containing "
                    f"`integrationLogLevel`"
                )
                continue
            group, field = entry
            if group.get("advanced") is not True:
                issues.append(
                    f"grouped connector: general_configurations entry "
                    f"for view_group '{group.get('view_group')}' must "
                    f"set `advanced: true` (per guide §3.7)"
                )
            if vg_key not in checked_shape_for_vgs:
                checked_shape_for_vgs.add(vg_key)
                issues.extend(
                    _check_log_level_field_shape(
                        field, f"view_group '{group.get('view_group')}'"
                    )
                )

        return issues

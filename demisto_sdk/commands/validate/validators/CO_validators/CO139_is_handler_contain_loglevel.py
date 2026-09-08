"""CO139 - every XSOAR handler must be reachable by an
``integrationLogLevel`` field under
``configurations.yaml.general_configurations``.

``integrationLogLevel`` is a connector-wide, backend-managed
``select`` field that lives in ``configurations.yaml`` under
``general_configurations``. It is emitted **once per XSOAR handler**
and must be visible for **every** capability the handler subscribes
to.

Standard vs grouped scoping:

**Standard connectors** (``settings.grouped != true``)
    - Exactly ONE ``general_configurations.configurations[]``
      field-group carries the ``integrationLogLevel`` field.
    - Either the group has no ``required_for_capabilities`` (shared
      across every handler) OR its ``required_for_capabilities`` list
      is a **superset** of every capability id the handler subscribes
      to. The looser "any intersection" semantics of
      :func:`general_configurations_field_group_visible_for_handler`
      is not enough here: a handler that subscribes to
      ``[cap-a, cap-b]`` under a group gated by
      ``required_for_capabilities: [cap-a]`` would have the log-level
      field hidden the moment the user disables cap-a while cap-b
      stays on. The superset rule ensures the log-level UI stays
      visible for every subscribed cap.
    - Duplicates (two field-groups both carrying the field) are a
      bug.

**Grouped connectors** (``settings.grouped == true``)
    - ONE ``general_configurations.configurations[]`` entry per
      view_group (per integration tile), each with the
      ``integrationLogLevel`` field and ``advanced: true``.
    - Each XSOAR handler is associated with exactly one view_group
      (via ``connection.yaml.profiles[].view_group``, resolved
      through :meth:`Connector.owned_view_groups_for_handler`), so
      the handler must see exactly ONE ``integrationLogLevel`` field
      from ``general_configurations``. More than one is a bug.
    - The enclosing field-group must set ``advanced: true``.

Field-shape sub-checks (common to both):
    - ``field_type: select``
    - ``metadata.xsoar.config_type: backend``
    - ``options.searchable: true``, ``options.clearable: true``
    - ``options.values`` keys include ``Off``, ``Debug``, ``Verbose``

Walker migration notes:
    - The per-handler ``integrationLogLevel`` visibility lookup uses
      the unified :func:`Connector.visible_fields_for_handler`
      walker. Serializer-rename resolution and grouped-vs-standard
      view_group scoping are handled centrally — no bespoke
      ``_serializer_rename_map`` / ``_iter_general_config_groups``
      helpers are needed.
    - Group-level attributes (``required_for_capabilities``,
      ``advanced``, duplicate detection) are read from the raw YAML
      via a targeted per-group walk — the walker itself intentionally
      surfaces per-FIELD data, not per-GROUP metadata (adding it
      would bloat the walker's contract for a single-consumer need).
      A helper module-local :func:`_iter_general_config_groups` does
      the raw-YAML sweep.
    - Non-XSOAR handlers are skipped (as before).
    - Missing configurations.yaml is skipped (as before) — other
      validators cover the missing-file case.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    FieldOrigin,
    HandlerVisibleField,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# ============================================================
# CO139 constants
# ============================================================
INTEGRATION_LOG_LEVEL_ID = "integrationLogLevel"
EXPECTED_FIELD_TYPE = "select"
EXPECTED_CONFIG_TYPE = "backend"
EXPECTED_VALUES_KEYS: Set[str] = {"Off", "Debug", "Verbose"}


# ============================================================
# Raw-YAML helpers for GROUP-level attributes
#
# The walker surfaces per-field visibility (which is exactly what
# ``_find_visible_log_level_fields`` needs), but group-level
# attributes (``required_for_capabilities``, ``advanced``, duplicate
# detection) are NOT on the walker's contract. A targeted per-group
# raw-YAML sweep here is the smallest, most local way to get them
# without bloating the walker for a single consumer.
# ============================================================
def _iter_general_config_groups(
    connector: Connector,
) -> Iterable[Dict[str, Any]]:
    """Yield every raw field-group dict from
    ``configurations.yaml.general_configurations.configurations[]``.

    Returns nothing if configurations.yaml is missing or malformed.
    Defensive against non-dict entries — matches the parsing style
    used elsewhere in the walker.
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


def _group_carries_log_level(
    group: Dict[str, Any],
    rename_map: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """Return the raw field dict whose runtime id (post-serializer
    rename) is ``integrationLogLevel`` inside ``group.fields[]`` — or
    None. ``rename_map`` is per-handler; a per-connector combined map
    is passed for duplicate detection across all handlers' renames.
    """
    fields = group.get("fields")
    if not isinstance(fields, list):
        return None
    for field in fields:
        if not isinstance(field, dict):
            continue
        raw_id = field.get("id")
        if not isinstance(raw_id, str):
            continue
        runtime = rename_map.get(raw_id, raw_id)
        if runtime == INTEGRATION_LOG_LEVEL_ID:
            return field
    return None


def _combined_rename_map(connector: Connector) -> Dict[str, str]:
    """Combine ``field_mappings`` renames across ALL XSOAR handlers.

    Used for the duplicate-count sweep so a single ``integrationLogLevel``
    id lookup canonicalises namespaced ids from any handler's
    serializer. When two handlers rename different raw ids to the
    same runtime name (e.g. ``xsoar-a_integrationLogLevel`` and
    ``xsoar-b_integrationLogLevel`` both → ``integrationLogLevel``),
    both are counted.
    """
    combined: Dict[str, str] = {}
    for handler in connector.xsoar_handlers:
        ser = handler.serializer
        if ser is None:
            continue
        for fm in ser.field_mappings or []:
            if fm.field_name:
                combined[fm.id] = fm.field_name
    return combined


# ============================================================
# Field-shape sub-checks
# ============================================================
def _check_log_level_field_shape(
    field: HandlerVisibleField, where: str
) -> List[str]:
    """Return a list of shape sub-rule failures for a visible
    ``integrationLogLevel`` field. ``where`` is a locator string used
    in messages (e.g. ``"general_configurations entry #1"``).

    Reads from the field's ``raw_dict`` sidecar so validations against
    keys the pydantic ``ConnectorField`` model may not round-trip
    losslessly (e.g. ``options.values[].key``) stay faithful to the
    on-disk YAML.
    """
    issues: List[str] = []
    prefix = f"integrationLogLevel in {where}"
    raw = field.raw_dict or {}

    actual_type = field.field.field_type
    if actual_type != EXPECTED_FIELD_TYPE:
        issues.append(
            f"{prefix}: field_type='{actual_type}' but must be "
            f"'{EXPECTED_FIELD_TYPE}'"
        )

    actual_ct = field.xsoar_config_type
    if actual_ct != EXPECTED_CONFIG_TYPE:
        issues.append(
            f"{prefix}: metadata.xsoar.config_type='{actual_ct}' but "
            f"must be '{EXPECTED_CONFIG_TYPE}'"
        )

    options = raw.get("options")
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
        "Validates that every XSOAR handler sees exactly one visible "
        "`integrationLogLevel` (select, config_type=backend) field "
        "under `configurations.yaml` `general_configurations`. Standard "
        "connectors: one field-group carries the field, and its "
        "`required_for_capabilities` (if set) must be a superset of "
        "every capability id the handler subscribes to. Grouped "
        "connectors: one field-group per view_group with `advanced: "
        "true`. Namespaced field ids are canonicalized via "
        "serializer.yaml `field_mappings` before matching (walker-"
        "driven)."
    )
    rationale = (
        "The backend cannot honor per-handler log-level controls "
        "without the `integrationLogLevel` backend-managed field. "
        "Standard connectors expose one field-group covering every "
        "handler capability so the UI knob is never gated off; grouped "
        "connectors expose one advanced field-group per integration "
        "tile so each tile's runtime debug/verbose controls surface "
        "under its own view_group. Duplicates or under-scoped "
        "`required_for_capabilities` leave subscribers unable to set "
        "log level for at least one of their capabilities."
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

        is_grouped = bool(connector.settings and connector.settings.grouped)

        issues: List[str] = []
        # Field-shape sub-rules can trigger from multiple handlers
        # observing the same field; dedupe per raw id to avoid
        # spamming the aggregated message.
        seen_shape_raw_ids: Set[str] = set()

        for handler in xsoar_handlers:
            visible = self._find_visible_log_level_fields(connector, handler)

            if not visible:
                issues.append(
                    f"XSOAR handler '{handler.id}' has no visible "
                    f"`integrationLogLevel` field in "
                    f"configurations.yaml `general_configurations` "
                    f"(checked runtime ids after serializer "
                    f"field_mappings resolution)"
                )
                continue

            if len(visible) > 1:
                # Grouped: >1 means multiple view_group entries are
                # visible to this handler (shouldn't happen — handler
                # binds to a single view_group). Standard: >1 means
                # multiple field-groups declare the field.
                issues.append(
                    f"XSOAR handler '{handler.id}' sees "
                    f"{len(visible)} `integrationLogLevel` field "
                    f"instances in `general_configurations` (must "
                    f"be exactly one)"
                )
                # Continue with the FIRST visible instance for
                # shape/coverage checks so authors get every kind of
                # finding in one pass rather than only the duplicate.

            field = visible[0]
            if field.raw_id not in seen_shape_raw_ids:
                seen_shape_raw_ids.add(field.raw_id)
                where = f"field group scoped to '{field.field_group_scope}'" \
                    if field.field_group_scope else "general_configurations"
                issues.extend(_check_log_level_field_shape(field, where))

            # Group-level checks require the raw group dict, which the
            # walker doesn't surface (by design — per-group metadata is
            # out of scope for a per-field walker).
            group = self._find_containing_group(
                connector, handler, field.raw_id
            )
            if group is None:
                continue  # Defensive: walker & raw walk should agree.

            if is_grouped:
                issues.extend(
                    self._check_grouped_group_attrs(handler, group)
                )
            else:
                issues.extend(
                    self._check_standard_group_coverage(handler, group)
                )

        # Duplicate detection at the file level (grouped OR standard).
        # A field-group that carries the log-level field but is NOT
        # visible to ANY XSOAR handler still counts as a duplicate for
        # this file — it's YAML the author needs to reconcile.
        issues.extend(self._check_file_level_duplicates(connector, is_grouped))

        return issues

    # ------------------------------------------------------------------
    # Walker-driven visibility lookup.
    # ------------------------------------------------------------------
    @staticmethod
    def _find_visible_log_level_fields(
        connector: Connector,
        handler: HandlerData,
    ) -> List[HandlerVisibleField]:
        """Return every ``HandlerVisibleField`` visible to ``handler``
        whose runtime name is ``integrationLogLevel`` and that
        originates from ``CONFIGURATIONS_GENERAL``.

        Uses the unified walker so serializer-rename resolution and
        grouped-vs-standard visibility scoping are handled centrally.
        List (not first-hit) because we care about the visible-count
        invariant.
        """
        return [
            vf
            for vf in connector.visible_fields_for_handler(handler)
            if vf.origin == FieldOrigin.CONFIGURATIONS_GENERAL
            and vf.runtime_name == INTEGRATION_LOG_LEVEL_ID
        ]

    # ------------------------------------------------------------------
    # Group-level checks (raw YAML — walker doesn't surface these).
    # ------------------------------------------------------------------
    @staticmethod
    def _find_containing_group(
        connector: Connector, handler: HandlerData, raw_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return the first raw field-group dict in
        ``general_configurations`` that declares a field with the given
        ``raw_id``.

        We look up by raw_id (not runtime name) because a group only
        carries a single physical field entry; the walker already picked
        the visible one via its per-handler visibility predicate, so we
        just need to locate that same physical group.
        """
        for group in _iter_general_config_groups(connector):
            fields = group.get("fields")
            if not isinstance(fields, list):
                continue
            for field in fields:
                if not isinstance(field, dict):
                    continue
                if field.get("id") == raw_id:
                    return group
        return None

    @staticmethod
    def _check_standard_group_coverage(
        handler: HandlerData, group: Dict[str, Any]
    ) -> List[str]:
        """Standard-connector rule: ``required_for_capabilities`` must
        be either absent/empty OR a superset of every capability id
        ``handler`` subscribes to.

        The looser "any intersection" semantics of the visibility
        predicate is not enough here — the user could enable a
        capability that the required_for_capabilities list omits, at
        which point the log-level field disappears from the UI.
        """
        rfc = group.get("required_for_capabilities")
        if rfc is None or (isinstance(rfc, list) and len(rfc) == 0):
            return []  # unrestricted — always visible.
        if not isinstance(rfc, list):
            return [
                f"XSOAR handler '{handler.id}': "
                f"integrationLogLevel group has invalid "
                f"`required_for_capabilities` (expected list, got "
                f"{type(rfc).__name__})"
            ]
        declared = {c for c in rfc if isinstance(c, str)}
        needed = set(handler.capability_ids)
        missing = needed - declared
        if missing:
            return [
                f"standard connector: integrationLogLevel group's "
                f"`required_for_capabilities` "
                f"({sorted(declared)!r}) does not cover XSOAR "
                f"handler '{handler.id}' capabilities "
                f"{sorted(missing)!r} - the field must remain visible "
                f"for every capability the handler subscribes to"
            ]
        return []

    @staticmethod
    def _check_grouped_group_attrs(
        handler: HandlerData, group: Dict[str, Any]
    ) -> List[str]:
        """Grouped-connector rule: the enclosing group must set
        ``advanced: true`` (guide §3.7).
        """
        if group.get("advanced") is not True:
            return [
                f"grouped connector: general_configurations entry "
                f"for view_group '{group.get('view_group')}' "
                f"(handler '{handler.id}') must set `advanced: true` "
                f"(per guide §3.7)"
            ]
        return []

    @staticmethod
    def _check_file_level_duplicates(
        connector: Connector, is_grouped: bool
    ) -> List[str]:
        """Enforce §3.7 uniqueness:

        - Standard: at most one field-group in ``general_configurations``
          carries the ``integrationLogLevel`` field.
        - Grouped: at most one field-group per ``view_group`` carries
          the field.

        Uses a per-connector combined serializer rename map so
        namespaced raw ids from different handlers still collapse
        under the same runtime name for the duplicate count.
        """
        rename_map = _combined_rename_map(connector)
        # (view_group_or_None, log_level_field_dict) tuples
        occurrences: List[Tuple[Optional[str], Dict[str, Any]]] = []
        for group in _iter_general_config_groups(connector):
            field = _group_carries_log_level(group, rename_map)
            if field is None:
                continue
            vg = group.get("view_group") if is_grouped else None
            occurrences.append((vg, field))

        issues: List[str] = []
        if is_grouped:
            per_view_group: Dict[Optional[str], int] = {}
            for vg, _ in occurrences:
                per_view_group[vg] = per_view_group.get(vg, 0) + 1
            for vg, count in per_view_group.items():
                if count > 1:
                    label = (
                        f"view_group '{vg}'" if vg else "no-view_group group"
                    )
                    issues.append(
                        f"grouped connector: {label} has {count} "
                        f"`integrationLogLevel` field-groups in "
                        f"`general_configurations` (must be exactly "
                        f"one per view_group)"
                    )
        else:
            if len(occurrences) > 1:
                issues.append(
                    f"standard connector: `general_configurations` "
                    f"has {len(occurrences)} field-groups carrying "
                    f"`integrationLogLevel` (must be exactly one)"
                )
        return issues

"""CO130 - `fetch-issues` capability must include the correct fetch fields.

Per §3.9.1 of the standard connector guide, every handler that
subscribes to the ``fetch-issues`` capability MUST emit the
``isFetch: true`` backend flag via its ``serializer.yaml``
``computed_fields`` block, gated by a capability condition. Per §3.7,
the ``fetch-issues`` capability's ``configurations[]`` entry MUST
contain four specific fields (incident type, fetch interval,
incoming mapper, classifier).

Public helpers (kept small and CO130-scoped; sibling validators
CO131-CO134 own their own capability/flag constants when written):

- ``iter_handler_capability_ids(handler, base_id)`` - yields every
  capability id on the handler that matches ``base_id`` (or its
  ``<base_id>_<suffix>`` namespaced form used by grouped connectors).
- ``find_capability_config_entry(connector, capability_id)`` - locate
  the ``configurations[]`` entry whose ``id`` equals a namespaced
  capability id (returns the raw dict from ``configurations_file``).
- ``field_dicts_in_capability_entry(entry)`` - yield every raw field
  dict from every field group in a capability configurations entry.
- ``computed_field_emits_flag(handler, flag_id, capability_id)`` -
  True if the handler's serializer has a ``computed_fields`` rule that
  outputs ``flag_id: true`` under a capability condition matching
  ``capability_id`` with value ``on``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
# CO130 constants
# ============================================================
FETCH_ISSUES_CAPABILITY = "fetch-issues"
FETCH_ISSUES_FLAG = "isFetch"

# Each entry is (field_id, expected_field_type, expected_dynamic_field_or_None).
# `expected_dynamic_field=None` means the field is not a dynamic-values
# select (e.g. `incidentFetchInterval` is a duration).
FETCH_ISSUES_REQUIRED_FIELDS: List[Tuple[str, str, Optional[str]]] = [
    ("incidentType", "select", "incident-type"),
    ("incidentFetchInterval", "duration", None),
    ("incomingMapperId", "select", "mapper-incoming"),
    ("mappingId", "select", "classifier"),
]


# ============================================================
# Helpers
# ============================================================
def iter_handler_capability_ids(handler: HandlerData, base_id: str) -> Iterable[str]:
    """Yield every capability id on ``handler`` that matches ``base_id``.

    A handler's ``capabilities[].id`` may be:
    - the bare capability id (e.g. ``fetch-issues``), OR
    - a namespaced variant used by grouped connectors
      (e.g. ``fetch-issues_qualys_fim``).

    We treat both as subscriptions to ``base_id``.
    """
    prefix = f"{base_id}_"
    for cap in handler.capabilities:
        cap_id = cap.id
        if cap_id == base_id or cap_id.startswith(prefix):
            yield cap_id


def find_capability_config_entry(
    connector: Connector, capability_id: str
) -> Optional[Dict[str, Any]]:
    """Return the ``configurations[]`` entry (raw dict) whose ``id``
    equals ``capability_id`` — or ``None`` if the connector has no
    configurations.yaml or the entry is missing.

    We read from ``connector.configurations_file.file_content`` (raw
    dict) instead of a strongly-typed attribute because per-capability
    configurations aren't hoisted onto ``connector.capabilities``
    (that field holds the ``capabilities.yaml`` shape, not the
    ``configurations.yaml`` per-capability field lists).
    """
    configurations_file = connector.configurations_file
    if not configurations_file.exist:
        return None
    raw = configurations_file.file_content or {}
    if not isinstance(raw, dict):
        return None
    entries = raw.get("configurations")
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("id") == capability_id:
            return entry
    return None


def field_dicts_in_capability_entry(
    entry: Dict[str, Any],
) -> Iterable[Dict[str, Any]]:
    """Yield every raw field dict (``{id, field_type, metadata, ...}``)
    from every field group in a capability configurations entry.

    Structure:
        entry.configurations[*].fields[*] -> ConnectorField dict
    """
    groups = entry.get("configurations")
    if not isinstance(groups, list):
        return
    for group in groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field in fields:
            if isinstance(field, dict):
                yield field


def _field_dynamic_field(field: Dict[str, Any]) -> Optional[str]:
    """Return ``metadata.dynamic_values.params.dynamicField`` or None."""
    metadata = field.get("metadata")
    if not isinstance(metadata, dict):
        return None
    dv = metadata.get("dynamic_values")
    if not isinstance(dv, dict):
        return None
    params = dv.get("params")
    if not isinstance(params, dict):
        return None
    val = params.get("dynamicField")
    return val if isinstance(val, str) else None


def computed_field_emits_flag(
    handler: HandlerData, flag_id: str, capability_id: str
) -> bool:
    """True if ``handler`` has a ``computed_fields`` rule that outputs
    ``flag_id: true`` under a capability condition referencing
    ``capability_id`` with value ``on``.

    Per §3.9.1 the rule shape is:

        computed_fields:
          - output:
              - id: <flag_id>
                value: true
            any_of:
              - conditions:
                  - type: capability
                    options:
                      capability_id: <capability_id>
                      value: 'on'
    """
    serializer = handler.serializer
    if serializer is None:
        return False
    for rule in serializer.computed_fields or []:
        outputs = rule.output or []
        has_flag = any(out.id == flag_id and out.value is True for out in outputs)
        if not has_flag:
            continue
        for group in rule.any_of or []:
            for cond in group.conditions or []:
                if cond.type != "capability":
                    continue
                opts = cond.options or {}
                if not isinstance(opts, dict):
                    continue
                if (
                    opts.get("capability_id") == capability_id
                    and str(opts.get("value")).lower() == "on"
                ):
                    return True
    return False


def _serializer_rename_map(handler: HandlerData) -> Dict[str, str]:
    """Return the ``connector_id -> runtime_name`` map built from
    ``handler.serializer.field_mappings``. Empty when no serializer or
    no ``field_mappings`` entries.

    A grouped connector namespaces its ``configurations.yaml`` field
    ids per view_group (e.g. ``xsoar-fireeyehelix_incidentType``) and
    renames them back to their canonical runtime name (e.g.
    ``incidentType``) via a serializer entry:

        field_mappings:
          - id: xsoar-fireeyehelix_incidentType
            field_name: incidentType

    Duplicated in CO130 (rather than imported from CO136) because
    CO136 already imports helpers from CO130; introducing the reverse
    edge would create a circular import.
    """
    mapping: Dict[str, str] = {}
    ser = handler.serializer
    if ser is None:
        return mapping
    for fm in ser.field_mappings or []:
        if fm.field_name:
            mapping[fm.id] = fm.field_name
    return mapping


# ============================================================
# CO130 validator
# ============================================================
class IsValidFetchValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO130"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`fetch-issues` capability (a) emits the `isFetch: true` "
        "backend flag via its serializer.yaml `computed_fields`, and "
        "(b) has the required fetch-issues configuration fields "
        "(incidentType, incidentFetchInterval, incomingMapperId, "
        "mappingId) declared under the capability's configurations "
        "entry with the correct field_type and dynamicField."
    )
    rationale = (
        "The XSOAR BE is capability-agnostic - it still needs the "
        "legacy `isFetch: true` flag to schedule the recurring fetch "
        "job. In UCP the `isFetch` checkbox is removed (choosing the "
        "capability IS the opt-in), so the flag must be emitted via "
        "serializer `computed_fields`. Additionally the capability's "
        "configurations must expose the mandatory fetch-issues fields "
        "(interval, incident type, incoming mapper, classifier) with "
        "the correct field_type/dynamic-values shape so instance "
        "creation succeeds."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the 'fetch-issues' capability but the fetch-issues wiring "
        "is incomplete: {issues}"
    )
    related_field = "configurations"
    is_auto_fixable = False
    # ``related_file_type`` feeds TWO independent ignore chains; each type
    # is needed by a different one (mirrors CO171's NOTE):
    #
    #   1. ``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    #      ``_resolve_ignore_file_keys``. This is the preflight; it expands
    #      each type into ``.connector-ignore`` section keys and short-
    #      circuits the validator when suppression is universal. Without
    #      CONNECTOR_SERIALIZER, ``[file:<handler>/serializer.yaml]`` entries
    #      are never consulted here and the validator runs even when every
    #      handler explicitly opts out.
    #
    #   2. ``ValidateManager.filter_validation_results`` ->
    #      ``_is_connector_handler_validation``. This is the post-hoc
    #      per-result filter, and it triggers when EITHER
    #      CONNECTOR_HANDLER OR CONNECTOR_SERIALIZER is present — so this
    #      chain was already active before CONNECTOR_SERIALIZER was added
    #      (CO130 has always carried CONNECTOR_HANDLER). What it does need
    #      is the per-result ``path`` split done in ``obtain_invalid_content_items``
    #      below, so each Part-1 result lands under
    #      ``<handler>/serializer.yaml`` and the per-handler ignore key
    #      resolves correctly.
    #
    # CONNECTOR_CONFIGURATIONS keeps Part-2 results discoverable under
    # ``[file:configurations.yaml]`` in chain 1.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
        RelatedFileType.CONNECTOR_HANDLER,
        RelatedFileType.CONNECTOR_SERIALIZER,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Emit one ValidationResult per defect, keyed by the file that
        owns the fix. The per-result ``path`` is what
        ``ValidateManager.filter_validation_results`` reads to route each
        result through the correct ignore lookup — so the split below is
        what makes per-handler ``.connector-ignore`` entries actually
        drop the right result (and only the right result):

        * Part 1 (serializer missing ``isFetch`` computed_field) — one
          result per offending handler, ``path=<handler>/serializer.yaml``.
          Routed by ``filter_validation_results`` to the connector's
          per-handler ignore check, which resolves
          ``[file:<handler-folder>/serializer.yaml]``. Sibling validators
          CO171/CO172 emit results the same way.

        * Part 2 (missing/wrong fields in ``configurations.yaml`` for a
          fetch-issues capability entry) — one result per offending
          capability id, ``path=configurations.yaml``. This is a
          connector-scoped concern (the configurations entry is shared
          across every handler subscribing to that capability id), so it
          keeps its historical placement and falls through to the
          general-case ignore lookup (``[file:configurations.yaml]``).
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            results.extend(self._collect_serializer_results(connector))
            results.extend(self._collect_configurations_results(connector))
        return results

    def _collect_serializer_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        """One result per handler whose serializer.yaml is missing the
        required ``isFetch: true`` ``computed_fields`` rule for one of
        its ``fetch-issues*`` capability ids."""
        results: List[ValidationResult] = []
        for handler in connector.xsoar_handlers:
            per_handler_issues: List[str] = []
            for cap_id in iter_handler_capability_ids(handler, FETCH_ISSUES_CAPABILITY):
                if not computed_field_emits_flag(handler, FETCH_ISSUES_FLAG, cap_id):
                    per_handler_issues.append(
                        f"handler '{handler.id}' subscribes to "
                        f"capability '{cap_id}' but its serializer.yaml "
                        f"does not emit `computed_fields` output "
                        f"'{FETCH_ISSUES_FLAG}: true' under a capability "
                        f"condition '{cap_id} == on'"
                    )
            if not per_handler_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(per_handler_issues),
                    ),
                    content_object=connector,
                    path=self._serializer_path(handler),
                )
            )
        return results

    def _collect_configurations_results(
        self, connector: Connector
    ) -> List[ValidationResult]:
        """One result per unique fetch-issues capability id whose
        ``configurations.yaml`` entry is missing / has wrong-shape
        required fields. A capability id may be subscribed to by
        multiple handlers via alternative auth options; the underlying
        configurations entry is shared, so we check each cap id once.
        The first subscribing handler's serializer rename map is used
        for id resolution (same behavior as before the split)."""
        results: List[ValidationResult] = []
        seen_capability_ids: Dict[str, HandlerData] = {}
        for handler in connector.xsoar_handlers:
            for cap_id in iter_handler_capability_ids(handler, FETCH_ISSUES_CAPABILITY):
                if cap_id in seen_capability_ids:
                    continue
                seen_capability_ids[cap_id] = handler

        for cap_id, handler in seen_capability_ids.items():
            rename_map = _serializer_rename_map(handler)
            capability_issues = self._check_capability_fields(
                connector, cap_id, rename_map
            )
            if not capability_issues:
                continue
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        issues="; ".join(capability_issues),
                    ),
                    content_object=connector,
                    path=connector.configurations_file.file_path,
                )
            )
        return results

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[Path]:
        """Best-effort path to ``handler``'s ``serializer.yaml`` — mirrors
        CO171/CO172's ``_serializer_path`` so the per-handler ignore key
        (``<handler-folder>/serializer.yaml``) resolves the same way.

        Falls back to ``None`` when the handler's on-disk location can't
        be determined; the per-handler ignore branch handles ``None``
        gracefully (returns False → the result is not ignored, which is
        the safe default)."""
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"

    def _check_capability_fields(
        self,
        connector: Connector,
        capability_id: str,
        rename_map: Dict[str, str],
    ) -> List[str]:
        entry = find_capability_config_entry(connector, capability_id)
        if entry is None:
            return [
                f"configurations.yaml has no `configurations[]` entry "
                f"with id '{capability_id}' - the fetch-issues capability "
                f"must have its own configurations entry containing the "
                f"required fields"
            ]

        # Grouped connectors namespace their configurations.yaml field ids
        # per view_group (e.g. ``xsoar-fireeyehelix_incidentType``) and
        # rename them back to the canonical name via
        # ``serializer.yaml`` ``field_mappings``. We index fields by their
        # RUNTIME id (post-rename) so the required-field lookup below
        # works for both bare and namespaced ids - mirrors CO136's
        # `_find_default_ignore_field` resolution pattern.
        fields_by_runtime_id: Dict[str, Dict[str, Any]] = {}
        for field in field_dicts_in_capability_entry(entry):
            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_id = rename_map.get(raw_id, raw_id)
            fields_by_runtime_id[runtime_id] = field

        issues: List[str] = []
        for expected_id, expected_type, expected_dyn in FETCH_ISSUES_REQUIRED_FIELDS:
            found_field = fields_by_runtime_id.get(expected_id)
            if found_field is None:
                issues.append(
                    f"capability '{capability_id}' is missing required "
                    f"field '{expected_id}'"
                )
                continue

            actual_type = found_field.get("field_type")
            if actual_type != expected_type:
                issues.append(
                    f"capability '{capability_id}' field '{expected_id}' "
                    f"has field_type='{actual_type}' but must be "
                    f"'{expected_type}'"
                )

            if expected_dyn is not None:
                actual_dyn = _field_dynamic_field(found_field)
                if actual_dyn != expected_dyn:
                    issues.append(
                        f"capability '{capability_id}' field "
                        f"'{expected_id}' has "
                        f"metadata.dynamic_values.params.dynamicField="
                        f"'{actual_dyn}' but must be '{expected_dyn}'"
                    )

        return issues

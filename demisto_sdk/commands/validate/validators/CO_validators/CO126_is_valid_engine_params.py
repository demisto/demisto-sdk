"""CO126 - conformance rules for the engine picker triplet.

Assumes CO125 has already established that the triplet is PRESENT.
CO126 walks the actual ``ConnectorField`` objects for ``engine_mode``,
``engine``, and ``engine_group`` (aka ``engineGroup``) and verifies
every field-level constraint from the connector spec.

Sub-rules enforced (per profile for grouped, once at
general_configurations for standard):

A. ``engine_mode.field_type == "radio"``.
B. ``engine_mode.options.orientation == "horizontal"``.
C. ``engine_mode.options.values`` keys == exactly
   ``{"no_engine", "engine", "engineGroup"}``. Appendix H integrations
   (single-engine) are skipped here because CO128 enforces their
   narrower 2-option set.
D. All three engine fields live in the SAME ``FieldGroup`` (the row
   that hosts the triplet).
E. ``engine.field_type == "select"`` and
   ``engineGroup.field_type == "select"``.
F. ``engine.metadata.xsoar.config_type == "backend"`` and same for
   ``engineGroup``.
G. ``engine.metadata.dynamic_values.provider == "xsoar"``; trigger set
   contains BOTH ``on_create`` AND ``on_edit``; same for ``engineGroup``.
H. ``engine.metadata.dynamic_values.params.integrationID ==
   handler.related_integration.object_id``; same for ``engineGroup``.
I. ``engine.metadata.dynamic_values.params.dynamicField == "engine"``;
   ``engineGroup.metadata.dynamic_values.params.dynamicField ==
   "engine-group"``.

Skip guards:
- No ``connector.connection`` -> skip.
- Appendix G integrations (EDL, TAXII Server, ...) -> skip (CO127
  enforces the opposite direction).
- Fields that CO125 would flag as MISSING are silently skipped by CO126
  (nothing to check).
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    ConnectorField,
    FieldGroup,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO125_is_auth_profile_has_engine import (
    ENGINE_GROUP_IDS,
    ENGINE_ID,
    ENGINE_MODE_ID,
    connector_is_appendix_g,
    connector_is_appendix_h,
    xsoar_handlers_for_profile,
)

ContentTypes = Connector

# ------------------------------------------------------------------
# Constants driving the sub-rules
# ------------------------------------------------------------------

_EXPECTED_ENGINE_MODE_KEYS: Set[str] = {"no_engine", "engine", "engineGroup"}
_EXPECTED_TRIGGERS: Set[str] = {"on_create", "on_edit"}
_EXPECTED_PROVIDER = "xsoar"
_EXPECTED_CONFIG_TYPE = "backend"
_ENGINE_DYNAMIC_FIELD = "engine"
_ENGINE_GROUP_DYNAMIC_FIELD = "engine-group"


# ------------------------------------------------------------------
# Small resolved-field record
# ------------------------------------------------------------------


class _ResolvedField:
    """A ConnectorField together with the canonical id we resolved for it
    (either its raw id in a standard connector, or its post-serializer id
    for a grouped-connector profile) AND the ``FieldGroup`` it lives in
    (for the same-group check).
    """

    __slots__ = ("field", "canonical_id", "group")

    def __init__(
        self,
        field: ConnectorField,
        canonical_id: str,
        group: FieldGroup,
    ) -> None:
        self.field = field
        self.canonical_id = canonical_id
        self.group = group


def _resolver_for_profile(connector: Connector, profile_id: str) -> dict:
    """Build ``{raw_id -> canonical_id}`` from the profile's owning XSOAR
    handlers' serializer rewrites (identical logic to CO125)."""
    resolver: dict = {}
    for handler in xsoar_handlers_for_profile(connector, profile_id):
        for rp in handler.resolved_params:
            if rp.connector_param_name in resolver:
                continue
            resolver[rp.connector_param_name] = rp.content_param_name
    return resolver


def _find_engine_fields(
    groups: List[FieldGroup],
    resolver: dict,
) -> List[_ResolvedField]:
    """Walk every field in ``groups`` and return only those whose
    canonical id is ``engine_mode``, ``engine``, or one of the
    ``engine_group`` spellings.
    """
    found: List[_ResolvedField] = []
    for grp in groups:
        for field in grp.fields:
            if not field.id:
                continue
            canonical = resolver.get(field.id, field.id)
            if canonical == ENGINE_MODE_ID:
                found.append(_ResolvedField(field, ENGINE_MODE_ID, grp))
            elif canonical == ENGINE_ID:
                found.append(_ResolvedField(field, ENGINE_ID, grp))
            elif canonical in ENGINE_GROUP_IDS:
                # Store under the canonical spelling ``engine_group`` so
                # downstream lookups can key on a single value.
                found.append(_ResolvedField(field, "engine_group", grp))
    return found


# ------------------------------------------------------------------
# Helpers for individual sub-rules
# ------------------------------------------------------------------


def _key_set(values: Optional[List[dict]]) -> Set[str]:
    """Extract the ``key`` values from an ``options.values`` list."""
    if not values:
        return set()
    keys: Set[str] = set()
    for v in values:
        k = v.get("key")
        if isinstance(k, str):
            keys.add(k)
    return keys


def _dynamic_values(field: ConnectorField) -> Optional[dict]:
    md = field.metadata or {}
    dv = md.get("dynamic_values")
    return dv if isinstance(dv, dict) else None


def _xsoar_metadata(field: ConnectorField) -> Optional[dict]:
    md = field.metadata or {}
    xs = md.get("xsoar")
    return xs if isinstance(xs, dict) else None


# ------------------------------------------------------------------
# Validator
# ------------------------------------------------------------------


class IsValidEngineParamsValidator(ConnectorsValidator[ContentTypes]):
    """CO126 - conformance of the 3 engine params.

    Runs one check per {connector, profile (grouped) OR
    general_configurations (standard)} pair. Emits one
    ``ValidationResult`` per pair with all sub-rule failures aggregated
    into the message. Only fields that are ACTUALLY PRESENT are checked;
    missing fields are CO125's responsibility.
    """

    error_code = "CO126"
    description = (
        "Verifies conformance of the engine triplet: engine_mode is a "
        "horizontal radio with keys {no_engine, engine, engineGroup}; "
        "engine and engine_group are backend-config selects with "
        "xsoar-provider dynamic_values triggered on_create+on_edit; "
        "dynamic_values.params.integrationID matches the handler's "
        "integration id; dynamicField is 'engine' or 'engine-group'; "
        "all three engine fields live in the same FieldGroup."
    )
    rationale = (
        "The engine picker is a UX contract: users pick 'no engine' / "
        "'engine' / 'engine group' via a radio; the follow-up select "
        "must fetch options dynamically from XSOAR and re-fetch on both "
        "create and edit. Any drift from this contract breaks the engine "
        "flow silently at runtime."
    )
    error_message = (
        "Connector '{connector_id}' {location}: engine-params "
        "conformance failed. {details}"
    )
    related_field = "connection.profiles / connection.general_configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Sub-rule checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_engine_mode(field: ConnectorField) -> List[str]:
        errors: List[str] = []
        if field.field_type != "radio":
            errors.append(
                f"engine_mode field_type must be 'radio', got " f"{field.field_type!r}"
            )
        opts = field.options
        if opts is None:
            errors.append("engine_mode.options is missing")
            return errors
        if opts.orientation != "horizontal":
            errors.append(
                f"engine_mode.options.orientation must be 'horizontal', "
                f"got {opts.orientation!r}"
            )
        keys = _key_set(opts.values)
        if keys != _EXPECTED_ENGINE_MODE_KEYS:
            missing = _EXPECTED_ENGINE_MODE_KEYS - keys
            extra = keys - _EXPECTED_ENGINE_MODE_KEYS
            parts = []
            if missing:
                parts.append(f"missing {sorted(missing)}")
            if extra:
                parts.append(f"unexpected {sorted(extra)}")
            errors.append(
                "engine_mode.options.values keys must be "
                f"{sorted(_EXPECTED_ENGINE_MODE_KEYS)}: " + "; ".join(parts)
            )
        return errors

    @classmethod
    def _check_engine_or_group(
        cls,
        field: ConnectorField,
        label: str,
        expected_dynamic_field: str,
        expected_integration_ids: Set[str],
    ) -> List[str]:
        """Common checks for the ``engine`` and ``engineGroup`` fields
        (E, F, G, H, I).
        """
        errors: List[str] = []

        # E. field_type
        if field.field_type != "select":
            errors.append(
                f"{label} field_type must be 'select', got " f"{field.field_type!r}"
            )

        # F. metadata.xsoar.config_type
        xs = _xsoar_metadata(field)
        if xs is None or xs.get("config_type") != _EXPECTED_CONFIG_TYPE:
            actual = xs.get("config_type") if xs else None
            errors.append(
                f"{label} metadata.xsoar.config_type must be "
                f"{_EXPECTED_CONFIG_TYPE!r}, got {actual!r}"
            )

        # G, H, I. dynamic_values block
        dv = _dynamic_values(field)
        if dv is None:
            errors.append(f"{label} metadata.dynamic_values is missing")
        else:
            # G. provider + trigger
            if dv.get("provider") != _EXPECTED_PROVIDER:
                errors.append(
                    f"{label} metadata.dynamic_values.provider must be "
                    f"{_EXPECTED_PROVIDER!r}, got {dv.get('provider')!r}"
                )
            triggers = set(dv.get("trigger") or [])
            if not _EXPECTED_TRIGGERS.issubset(triggers):
                missing_triggers = _EXPECTED_TRIGGERS - triggers
                errors.append(
                    f"{label} metadata.dynamic_values.trigger must "
                    f"contain both 'on_create' and 'on_edit'; missing "
                    f"{sorted(missing_triggers)}"
                )
            # H, I. params
            params = dv.get("params") or {}
            if not isinstance(params, dict):
                errors.append(
                    f"{label} metadata.dynamic_values.params must be a " f"mapping"
                )
            else:
                # I. dynamicField (checked even without an integration).
                actual_field = params.get("dynamicField")
                if actual_field != expected_dynamic_field:
                    errors.append(
                        f"{label} metadata.dynamic_values.params."
                        f"dynamicField must be "
                        f"{expected_dynamic_field!r}, got "
                        f"{actual_field!r}"
                    )
                # H. integrationID must match one of the owning XSOAR
                # handlers' resolved integration ids.
                actual_int_id = params.get("integrationID")
                if expected_integration_ids:
                    if actual_int_id not in expected_integration_ids:
                        errors.append(
                            f"{label} metadata.dynamic_values.params."
                            f"integrationID must match the owning "
                            f"handler's integration id (one of "
                            f"{sorted(expected_integration_ids)}), got "
                            f"{actual_int_id!r}"
                        )
                elif actual_int_id is None:
                    # No expected id from the graph AND no id declared
                    # in the yaml - flag it as unverifiable-missing.
                    errors.append(
                        f"{label} metadata.dynamic_values.params."
                        f"integrationID is missing (and no resolved "
                        f"integration on the owning XSOAR handler to "
                        f"validate against)"
                    )

        return errors

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            connection = connector.connection
            if connection is None:
                continue

            # Appendix G: skip entirely (CO127 handles those).
            if connector_is_appendix_g(connector):
                continue

            path = (
                connector.connection_file.file_path
                if connector.connection_file
                else connector.path
            )
            is_grouped = bool(connector.settings and connector.settings.grouped)
            # Appendix H: engine_mode uses a 2-option key-set, no
            # engineGroup field expected. CO128 enforces that shape.
            # CO126 skips option-set validation for those integrations
            # to avoid double-flagging.
            skip_options_key_set = connector_is_appendix_h(connector)

            if is_grouped:
                for profile in connection.profiles:
                    resolver = _resolver_for_profile(connector, profile.id)
                    fields = _find_engine_fields(list(profile.configurations), resolver)
                    if not fields:
                        continue
                    location = f"profile '{profile.id}'"
                    handlers = list(xsoar_handlers_for_profile(connector, profile.id))
                    detail = self._validate_engine_fields(
                        fields,
                        handlers=handlers,
                        skip_options_key_set=skip_options_key_set,
                    )
                    if detail:
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(
                                    connector_id=connector.object_id,
                                    location=location,
                                    details=detail,
                                ),
                                content_object=connector,
                                path=path,
                            )
                        )
            else:
                gc = connection.general_configurations
                gc_groups = list(gc.configurations) if gc else []
                # Standard: canonical ids (no serializer rewrite).
                fields = _find_engine_fields(gc_groups, resolver={})
                if not fields:
                    continue
                # Standard connectors: use ALL XSOAR handlers on the
                # connector for the integrationID pool.
                handlers = [h for h in connector.handlers if h.is_xsoar]
                detail = self._validate_engine_fields(
                    fields,
                    handlers=handlers,
                    skip_options_key_set=skip_options_key_set,
                )
                if detail:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                connector_id=connector.object_id,
                                location="general_configurations",
                                details=detail,
                            ),
                            content_object=connector,
                            path=path,
                        )
                    )

        return results

    # ------------------------------------------------------------------
    # Per-scope aggregator
    # ------------------------------------------------------------------

    def _validate_engine_fields(
        self,
        fields: List[_ResolvedField],
        handlers: List[HandlerData],
        skip_options_key_set: bool,
    ) -> str:
        errors: List[str] = []

        # Expected integration ids for the H sub-rule.
        expected_int_ids: Set[str] = set()
        for h in handlers:
            integration = h.related_integration
            if integration is None:
                continue
            obj_id = getattr(integration, "object_id", None)
            if obj_id:
                expected_int_ids.add(obj_id)

        # Index by canonical id.
        by_canonical: dict = {}
        for f in fields:
            by_canonical.setdefault(f.canonical_id, []).append(f)

        # D. all three in the same FieldGroup: only check if at least 2
        # of the 3 canonical ids are present (otherwise D is vacuous).
        groups_seen = {id(f.group) for f in fields}
        if len(fields) >= 2 and len(groups_seen) > 1:
            errors.append(
                "engine_mode, engine, and engine_group must live in the "
                f"same FieldGroup (found {len(groups_seen)} groups)"
            )

        # A, B, C. engine_mode.
        for rf in by_canonical.get(ENGINE_MODE_ID, []):
            for err in self._check_engine_mode(rf.field):
                # Sub-rule C is skipped for Appendix H integrations.
                if skip_options_key_set and err.startswith(
                    "engine_mode.options.values keys must be"
                ):
                    continue
                errors.append(err)

        # E-J. engine.
        for rf in by_canonical.get(ENGINE_ID, []):
            errors.extend(
                self._check_engine_or_group(
                    rf.field,
                    label=ENGINE_ID,
                    expected_dynamic_field=_ENGINE_DYNAMIC_FIELD,
                    expected_integration_ids=expected_int_ids,
                )
            )

        # E-J. engine_group / engineGroup.
        for rf in by_canonical.get("engine_group", []):
            errors.extend(
                self._check_engine_or_group(
                    rf.field,
                    label="engine_group",
                    expected_dynamic_field=_ENGINE_GROUP_DYNAMIC_FIELD,
                    expected_integration_ids=expected_int_ids,
                )
            )

        return "; ".join(errors)

"""Handler-visible-fields walker.

Unified per-handler visible-field API on the ``Connector`` content item.
See ``plans/handler-visible-fields-walker.md`` for the design spec.

Public surface:

- :class:`FieldOrigin` — the six ``(file × structural-surface)`` combinations
  a visible field can originate from.
- :class:`HandlerVisibleField` — one instance per physical field-definition
  location for a given handler.
- :func:`walk_visible_fields` — pure aggregator; produces a deterministic
  ordered list of ``HandlerVisibleField`` for ``(connector, handler)``.

The walker fixes the four bugs enumerated in Section 1 of the spec:

1. **View_group leak** — every ``general_configurations`` branch filters
   through :func:`general_configurations_field_group_visible_for_handler`.
2. **Loses field body** — every ``HandlerVisibleField`` carries the full
   parsed :class:`ConnectorField` plus a ``raw_dict`` sidecar for legacy
   validators that need raw YAML fidelity.
3. **Grouped sub-cap entries dropped** — the
   :func:`_walk_configurations_capability` helper walks the RAW YAML at
   ``connector.configurations_file.file_content["configurations"]`` and
   matches entry ``id`` against ``handler.capability_ids`` (which stores
   both parent-cap and sub-cap ids verbatim per its docstring).
4. **``source_file`` collapsed to a bare filename** — every emitted
   ``HandlerVisibleField.source_file`` is an absolute :class:`Path`
   harvested from ``connector.<file>.file_path``.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
)

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectorField,
    general_configurations_field_group_visible_for_handler,
)
from demisto_sdk.commands.content_graph.parsers.connector import ConnectorParser

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from demisto_sdk.commands.content_graph.objects.connector import (
        Connector,
        HandlerData,
    )


# ============================================================
# FieldOrigin enum
# ============================================================


class FieldOrigin(str, Enum):
    """One member per unique ``(file × structural-surface)`` a visible
    connector field can originate from.

    ``SERIALIZER_COMPUTED`` is intentionally excluded from v1 (spec §7 Q3):
    computed fields have no physical YAML entry and no downstream consumer
    asks for them via the walker today.
    """

    CONNECTION_GENERAL = "connection.general_configurations"
    CONNECTION_PROFILE = "connection.profiles"
    CAPABILITIES_GENERAL = "capabilities.general_configurations"
    CONFIGURATIONS_GENERAL = "configurations.general_configurations"
    CONFIGURATIONS_CAPABILITY = "configurations.configurations[<cap>]"

    @property
    def file_label(self) -> str:
        """Human-readable YAML-file label for this origin.

        Used by validators to build error messages that mention the
        physical file the field came from (e.g. ``connection.yaml``).
        Centralised here so the mapping stays consistent across
        validators — there is exactly one file per origin.
        """
        return _ORIGIN_FILE_LABELS[self]


_ORIGIN_FILE_LABELS: Dict["FieldOrigin", str] = {}


def _init_origin_file_labels() -> None:
    """Populate :data:`_ORIGIN_FILE_LABELS`.

    Kept as a post-definition initialiser so the enum class body stays
    readable and the map is guaranteed to cover every member.
    """
    _ORIGIN_FILE_LABELS.update(
        {
            FieldOrigin.CONNECTION_GENERAL: "connection.yaml",
            FieldOrigin.CONNECTION_PROFILE: "connection.yaml",
            FieldOrigin.CAPABILITIES_GENERAL: "capabilities.yaml",
            FieldOrigin.CONFIGURATIONS_GENERAL: "configurations.yaml",
            FieldOrigin.CONFIGURATIONS_CAPABILITY: "configurations.yaml",
        }
    )
    # Sanity check — every enum member must map to a file label. If a
    # new origin is added without a label the ``file_label`` accessor
    # would KeyError at runtime; better to fail loudly at import time.
    missing = set(FieldOrigin) - set(_ORIGIN_FILE_LABELS)
    if missing:
        raise RuntimeError(
            f"FieldOrigin file_label mapping missing entries for: {missing}"
        )


_init_origin_file_labels()


# ============================================================
# HandlerVisibleField model
# ============================================================


class HandlerVisibleField(BaseModel):
    """A single connector field, resolved for one specific handler.

    One instance per (handler, physical field-definition location). A
    field id that appears in two YAMLs produces two instances
    (spec §7 Q1: no dedup — the walker returns both, consumers choose).
    """

    field: ConnectorField
    """Full parsed pydantic field body — validators no longer re-walk YAML."""

    raw_id: str
    """ID as authored in the manifest YAML. May be namespaced for grouped
    connectors (e.g. ``xsoar-splunkpy-v2_integrationLogLevel``)."""

    runtime_name: str
    """ID after serializer.yaml field_mappings rename. Equal to ``raw_id``
    when no serializer or no mapping for this id."""

    is_serialized: bool
    """True iff serializer.yaml renamed ``raw_id`` -> ``runtime_name``."""

    source_file: Path
    """Absolute :class:`Path` to the physical YAML file that defines this
    field. Never a bare filename — see spec §3 bug-4 fix."""

    origin: FieldOrigin
    """Which structural surface the field came from (see :class:`FieldOrigin`)."""

    capability_id: Optional[str] = None
    """Populated only when ``origin == CONFIGURATIONS_CAPABILITY``.
    For grouped sub-cap entries this is the SUB-cap id as written in
    ``configurations.yaml`` (e.g. ``log-collection_akamai-waf-siem``),
    NOT the parent cap."""

    parent_capability_id: Optional[str] = None
    """When ``capability_id`` is a sub-cap and its parent is known, the
    parent capability id. None for standard connectors where entries are
    keyed by bare capability ids."""

    profile_id: Optional[str] = None
    """Populated only when ``origin == CONNECTION_PROFILE``. The profile
    id the handler auth-binds to."""

    field_group_scope: Optional[str] = None
    """For any origin in ``{CONNECTION_GENERAL, CAPABILITIES_GENERAL,
    CONFIGURATIONS_GENERAL}``: a human-readable scope hint derived from the
    enclosing field group's ``view_group`` id (grouped) or the join of its
    ``required_for_capabilities`` (standard). Free-form; consumers use it
    for error-message location hints."""

    raw_dict: Optional[Dict[str, Any]] = None
    """The original YAML dict for this field. Escape hatch for legacy
    validators that inspect fidelity the pydantic model does
    not necessarily round-trip losslessly (e.g. checkbox_group inner items
    in CO143). New validators MUST prefer the ``field`` attribute."""

    class Config:
        arbitrary_types_allowed = True

    @property
    def xsoar_config_type(self) -> Optional[str]:
        """Return the ``field.metadata.xsoar.config_type`` string (i.e. 'backend'), or
        ``None`` if any part of the chain is missing / wrong type.

        Reads from :attr:`raw_dict` (the original YAML dict) so we see
        the value the author actually wrote.
        """
        raw = self.raw_dict
        if not isinstance(raw, dict):
            return None
        metadata = raw.get("metadata")
        if not isinstance(metadata, dict):
            return None
        xsoar = metadata.get("xsoar")
        if not isinstance(xsoar, dict):
            return None
        val = xsoar.get("config_type")
        return val if isinstance(val, str) else None

    @property
    def dynamic_field_name(self) -> Optional[str]:
        """Return the ``field.metadata.dynamic_values.params.dynamicField``
        string, or ``None`` if any part of the chain is missing / wrong type.

        Reads from :attr:`raw_dict` (the original YAML dict) — same
        rationale as :attr:`xsoar_config_type`: we surface exactly what
        the author wrote. Consumers: any validator inspecting the
        dynamic-values binding of a select field (e.g. CO130's
        fetch-issues required-field shape checks: ``incidentType``
        binds ``dynamicField: incident-type``, ``incomingMapperId``
        binds ``mapper-incoming``, ``mappingId`` binds ``classifier``).
        """
        raw = self.raw_dict
        if not isinstance(raw, dict):
            return None
        metadata = raw.get("metadata")
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

    @property
    def field_type(self) -> Optional[str]:
        """Return the field's ``field_type`` string as authored in the
        YAML (e.g. ``"select"``, ``"input"``, ``"checkbox"``), or
        ``None`` when missing / wrong type.

        Reads from :attr:`raw_dict` so we surface exactly what the
        author wrote. Consumers: any validator that filters by field
        type (CO137 duration, CO143 select/multi_select).
        """
        raw = self.raw_dict
        if not isinstance(raw, dict):
            return None
        val = raw.get("field_type")
        return val if isinstance(val, str) else None

    @property
    def options(self) -> Dict[str, Any]:
        """Return the field's ``options`` dict as authored in the YAML,
        or an empty dict when missing / wrong type.

        Convenience over ``raw_dict.get("options")`` — the empty-dict
        fallback lets consumers write ``vf.options.get("clearable")``
        without pre-checking. Consumers: any validator inspecting
        select-field option shape (CO143 clearable / searchable /
        values).
        """
        raw = self.raw_dict
        if not isinstance(raw, dict):
            return {}
        opts = raw.get("options")
        return opts if isinstance(opts, dict) else {}

    @property
    def location_hint(self) -> str:
        """Used inside author-facing error
        messages so the author knows WHERE in the YAML file the offending
        field sits — the ``source_file`` alone (e.g. ``connection.yaml``)
        is not enough on real content, where a single YAML file has
        many field-emitting sections.

        Concretely:

        - ``CONNECTION_PROFILE`` → ``profile '<id>'`` — points at the
          exact ``profiles[<id>]`` block, so grouped connectors with
          many auth profiles per handler get an unambiguous location.
        - ``CONFIGURATIONS_CAPABILITY`` → ``capability '<id>'`` —
          points at ``configurations.yaml.configurations[<cap>]``,
          again disambiguating between multiple per-capability entries
          in one file.
        - Any ``general_configurations`` origin →
          ``general_configurations`` — the field lives in the file's
          shared/top-level configurations block.

        Consumers embed this in a message like:
        ``"...field 'foo' in 'connection.yaml' (profile 'basic.default') ..."``.
        Centralised on the model so every validator emits the same
        vocabulary and authors see consistent phrasing.
        """
        if self.origin == FieldOrigin.CONNECTION_PROFILE:
            return f"profile '{self.profile_id}'" if self.profile_id else "profile"
        if self.origin == FieldOrigin.CONFIGURATIONS_CAPABILITY:
            return (
                f"capability '{self.capability_id}'"
                if self.capability_id
                else "capability"
            )
        return "general_configurations"


# ============================================================
# Internal helpers
# ============================================================


def _serializer_rename_map(handler: "HandlerData") -> Dict[str, str]:
    """``{connector_field_id: runtime_name}`` derived from
    ``handler.serializer.field_mappings``.

    Empty dict when the handler has no serializer or when no mapping
    provides a ``field_name``. Structurally identical to CO138's
    ``_serializer_rename_map`` (which we're centralising here).
    """
    mapping: Dict[str, str] = {}
    ser = handler.serializer
    if ser is None:
        return mapping
    for fm in ser.field_mappings or []:
        if fm.field_name:
            mapping[fm.id] = fm.field_name
    return mapping


def _resolve_source_file(related_file: Any) -> Optional[Path]:
    """Return the on-disk :class:`Path` of a connector-related file when
    it exists, else ``None``.

    ``ConnectorYAMLRelatedFile.file_path`` is always populated (even when
    the file does not exist on disk), so we must gate on ``.exist``.
    """
    if related_file is None:
        return None
    if not getattr(related_file, "exist", False):
        return None
    path = getattr(related_file, "file_path", None)
    if path is None:
        return None
    return Path(path)


def _field_to_raw_dict(field: ConnectorField) -> Dict[str, Any]:
    """Pydantic → dict conversion for the ``raw_dict`` sidecar.

    Used when we're walking already-parsed pydantic models (connection
    profiles, ``connection.general_configurations``) and don't have the
    original YAML dict on hand. For the two YAML-driven walkers
    (``_walk_capabilities_general``, ``_walk_configurations_general``,
    ``_walk_configurations_capability``) the walker prefers the actual
    raw YAML dict.
    """
    return field.dict(exclude_none=False, by_alias=False)


def _field_group_scope(group: Any) -> Optional[str]:
    """Human-readable scope hint for a ``general_configurations`` group.

    Falls back through ``view_group`` (grouped) -> a joined
    ``required_for_capabilities`` (standard). Returns ``None`` for shared
    groups with no scoping marker.
    """
    if isinstance(group, dict):
        view_group = group.get("view_group")
        required_for_caps = group.get("required_for_capabilities")
    else:
        view_group = getattr(group, "view_group", None)
        required_for_caps = getattr(group, "required_for_capabilities", None)
    if isinstance(view_group, str) and view_group:
        return view_group
    if isinstance(required_for_caps, list) and required_for_caps:
        return ",".join(str(c) for c in required_for_caps)
    return None


def _iter_raw_field_groups(groups: Any) -> Iterator[Dict[str, Any]]:
    """Yield each raw YAML field-group dict from a raw
    ``general_configurations.configurations`` list.

    Silently skips non-dict entries — matches the defensive parsing style
    used across CO138 / CO141 / CO145.
    """
    if not isinstance(groups, list):
        return
    for group in groups:
        if isinstance(group, dict):
            yield group


def _iter_raw_fields(group: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Yield each raw YAML field dict inside a raw field-group dict."""
    fields = group.get("fields")
    if not isinstance(fields, list):
        return
    for field in fields:
        if isinstance(field, dict):
            yield field


def _build_field_from_raw(raw_field: Dict[str, Any]) -> Optional[ConnectorField]:
    """Parse a raw YAML field dict into a :class:`ConnectorField`.

    Delegates to :meth:`ConnectorParser._parse_field` — the canonical
    field parser the connector parser uses when building
    ``ConnectorConnectionData`` / ``CapabilityData`` sub-models. Calling
    it here (instead of re-implementing) guarantees the walker's
    raw-YAML-to-pydantic transform is byte-identical to the parser's
    for every corner of :class:`ConnectorField` (options, validations,
    behavior, checkbox_group nested items, …).

    Returns ``None`` when the dict is missing a valid ``id`` — the walker
    then skips this field silently (garbage-in tolerance).
    """
    field_id = raw_field.get("id")
    if not isinstance(field_id, str) or not field_id:
        return None
    try:
        return ConnectorParser._parse_field(raw_field)
    except Exception:
        # Defensive fallback: hand-build a minimal ConnectorField so that
        # downstream code sees a valid pydantic instance even if the raw
        # dict contains keys the model rejects. This preserves the
        # walker's "never crash on malformed content" contract.
        return ConnectorField(id=field_id)


def _emit_field(
    *,
    field: ConnectorField,
    raw_field: Optional[Dict[str, Any]],
    origin: FieldOrigin,
    source_file: Path,
    serializer_rename: Dict[str, str],
    capability_id: Optional[str] = None,
    parent_capability_id: Optional[str] = None,
    profile_id: Optional[str] = None,
    field_group_scope: Optional[str] = None,
) -> HandlerVisibleField:
    """Build a single :class:`HandlerVisibleField` from a parsed field and
    optional raw dict, applying the per-handler serializer rename.

    Centralised so every walker helper shares identical rename/raw_dict
    semantics; no origin has bespoke behaviour for those two fields.
    """
    raw_id = field.id
    runtime_name = serializer_rename.get(raw_id, raw_id)
    is_serialized = runtime_name != raw_id
    raw_dict = raw_field if raw_field is not None else _field_to_raw_dict(field)
    return HandlerVisibleField(
        field=field,
        raw_id=raw_id,
        runtime_name=runtime_name,
        is_serialized=is_serialized,
        source_file=source_file,
        origin=origin,
        capability_id=capability_id,
        parent_capability_id=parent_capability_id,
        profile_id=profile_id,
        field_group_scope=field_group_scope,
        raw_dict=raw_dict,
    )


# ============================================================
# Origin-specific walkers
# ============================================================


def _walk_connection_general(
    connector: "Connector",
    handler: "HandlerData",
    serializer_rename: Dict[str, str],
) -> Iterator[HandlerVisibleField]:
    """Yield ``CONNECTION_GENERAL`` fields visible to ``handler``.

    Walks the raw YAML at ``connection_file.file_content
    ["general_configurations"]`` so the ``raw_dict`` sidecar stays
    authentic and test fixtures that seed ``connection.yaml`` via
    ``file_content`` alone (without also refreshing the parsed
    :attr:`Connector.connection` pydantic sub-model) still get accurate
    walker output. Applies
    :func:`general_configurations_field_group_visible_for_handler` per
    field group (bug-1 fix — view_group leak).
    """
    source_file = _resolve_source_file(connector.connection_file)
    if source_file is None:
        return
    raw = connector.connection_file.file_content
    if not isinstance(raw, dict):
        return
    general = raw.get("general_configurations")
    if not isinstance(general, dict):
        return
    for group in _iter_raw_field_groups(general.get("configurations")):
        if not general_configurations_field_group_visible_for_handler(
            group, connector, handler
        ):
            continue
        scope = _field_group_scope(group)
        for raw_field in _iter_raw_fields(group):
            parsed = _build_field_from_raw(raw_field)
            if parsed is None:
                continue
            yield _emit_field(
                field=parsed,
                raw_field=raw_field,
                origin=FieldOrigin.CONNECTION_GENERAL,
                source_file=source_file,
                serializer_rename=serializer_rename,
                field_group_scope=scope,
            )


def _walk_connection_profiles(
    connector: "Connector",
    handler: "HandlerData",
    serializer_rename: Dict[str, str],
) -> Iterator[HandlerVisibleField]:
    """Yield ``CONNECTION_PROFILE`` fields — one per field inside every
    profile the handler auth-binds to.

    Walks the raw YAML at ``connection_file.file_content["profiles"]`` so
    the ``raw_dict`` sidecar stays authentic and test fixtures that seed
    ``connection.yaml`` via ``file_content`` alone (without also
    refreshing the parsed :attr:`Connector.connection` pydantic
    sub-model) still get accurate walker output. Profiles are scoped by
    handler auth binding
    (``handler.capabilities[].auth_options[].id ↔ profile.id``), NOT by
    the general_configurations view_group predicate.
    """
    source_file = _resolve_source_file(connector.connection_file)
    if source_file is None:
        return
    raw = connector.connection_file.file_content
    if not isinstance(raw, dict):
        return
    profiles = raw.get("profiles")
    if not isinstance(profiles, list):
        return

    auth_ids: Set[str] = {
        ao.id for hc in handler.capabilities for ao in hc.auth_options
    }
    if not auth_ids:
        return

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or profile_id not in auth_ids:
            continue
        for group in _iter_raw_field_groups(profile.get("configurations")):
            # NOTE: profile configuration groups do NOT participate in the
            # general_configurations view_group predicate — auth binding
            # (handler↔profile) is the scoping mechanism here. Do not
            # apply :func:`general_configurations_field_group_visible_for_handler`.
            for raw_field in _iter_raw_fields(group):
                parsed = _build_field_from_raw(raw_field)
                if parsed is None:
                    continue
                yield _emit_field(
                    field=parsed,
                    raw_field=raw_field,
                    origin=FieldOrigin.CONNECTION_PROFILE,
                    source_file=source_file,
                    serializer_rename=serializer_rename,
                    profile_id=profile_id,
                )


def _walk_capabilities_general(
    connector: "Connector",
    handler: "HandlerData",
    serializer_rename: Dict[str, str],
) -> Iterator[HandlerVisibleField]:
    """Yield ``CAPABILITIES_GENERAL`` fields visible to ``handler``.

    Walks the raw YAML at ``capabilities_file.file_content
    ["general_configurations"]`` so the ``raw_dict`` sidecar and the
    field group's raw view_group / required_for_capabilities markers
    stay authentic. Applies the visibility predicate per group.
    """
    source_file = _resolve_source_file(connector.capabilities_file)
    if source_file is None:
        return
    raw = connector.capabilities_file.file_content
    if not isinstance(raw, dict):
        return
    general = raw.get("general_configurations")
    if not isinstance(general, dict):
        return
    for group in _iter_raw_field_groups(general.get("configurations")):
        if not general_configurations_field_group_visible_for_handler(
            group, connector, handler
        ):
            continue
        scope = _field_group_scope(group)
        for raw_field in _iter_raw_fields(group):
            parsed = _build_field_from_raw(raw_field)
            if parsed is None:
                continue
            yield _emit_field(
                field=parsed,
                raw_field=raw_field,
                origin=FieldOrigin.CAPABILITIES_GENERAL,
                source_file=source_file,
                serializer_rename=serializer_rename,
                field_group_scope=scope,
            )


def _walk_configurations_general(
    connector: "Connector",
    handler: "HandlerData",
    serializer_rename: Dict[str, str],
) -> Iterator[HandlerVisibleField]:
    """Yield ``CONFIGURATIONS_GENERAL`` fields visible to ``handler``.

    Same shape as :func:`_walk_capabilities_general` but reads from
    ``configurations_file.file_content["general_configurations"]``.
    """
    source_file = _resolve_source_file(connector.configurations_file)
    if source_file is None:
        return
    raw = connector.configurations_file.file_content
    if not isinstance(raw, dict):
        return
    general = raw.get("general_configurations")
    if not isinstance(general, dict):
        return
    for group in _iter_raw_field_groups(general.get("configurations")):
        if not general_configurations_field_group_visible_for_handler(
            group, connector, handler
        ):
            continue
        scope = _field_group_scope(group)
        for raw_field in _iter_raw_fields(group):
            parsed = _build_field_from_raw(raw_field)
            if parsed is None:
                continue
            yield _emit_field(
                field=parsed,
                raw_field=raw_field,
                origin=FieldOrigin.CONFIGURATIONS_GENERAL,
                source_file=source_file,
                serializer_rename=serializer_rename,
                field_group_scope=scope,
            )


def _walk_configurations_capability(
    connector: "Connector",
    handler: "HandlerData",
    serializer_rename: Dict[str, str],
) -> Iterator[HandlerVisibleField]:
    """Yield ``CONFIGURATIONS_CAPABILITY`` fields — the bug-3 fix.

    Walks ``configurations_file.file_content["configurations"]`` DIRECTLY,
    matching each entry's raw ``id`` against ``handler.capability_ids``
    (which stores both parent-cap and sub-cap ids exactly as authored per
    the ``HandlerData.capability_ids`` docstring). This is the pattern
    CO130 / CO132 / CO145 currently reimplement standalone; centralising
    it here means the fix propagates to every consumer at once, and
    grouped-connector sub-cap entries stop silently disappearing from the
    walker output.

    ``parent_capability_id`` is populated for entries whose id matches a
    known sub-capability under one of the connector's parent capabilities.
    Standard connectors have no sub-capabilities so this is always
    ``None`` there.
    """
    source_file = _resolve_source_file(connector.configurations_file)
    if source_file is None:
        return
    raw = connector.configurations_file.file_content
    if not isinstance(raw, dict):
        return
    entries = raw.get("configurations")
    if not isinstance(entries, list):
        return

    handler_cap_ids = handler.capability_ids  # frozenset[str]

    # Build sub-cap-id -> parent-cap-id lookup so we can populate
    # parent_capability_id on grouped sub-cap entries.
    sub_to_parent: Dict[str, str] = {}
    for cap in connector.capabilities or []:
        for sc in cap.sub_capabilities or []:
            sub_to_parent[sc.id] = cap.id

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or entry_id not in handler_cap_ids:
            continue
        parent_cap_id = sub_to_parent.get(entry_id)
        for group in _iter_raw_field_groups(entry.get("configurations")):
            # NOTE: inside a per-capability entry the enclosing entity IS
            # the scoping (handler subscribes to this cap id); the
            # general_configurations view_group / required_for_capabilities
            # predicate MUST NOT be applied here (spec: predicate is
            # general_configurations-only).
            for raw_field in _iter_raw_fields(group):
                parsed = _build_field_from_raw(raw_field)
                if parsed is None:
                    continue
                yield _emit_field(
                    field=parsed,
                    raw_field=raw_field,
                    origin=FieldOrigin.CONFIGURATIONS_CAPABILITY,
                    source_file=source_file,
                    serializer_rename=serializer_rename,
                    capability_id=entry_id,
                    parent_capability_id=parent_cap_id,
                )


# ============================================================
# Public aggregator
# ============================================================


def walk_visible_fields(
    connector: "Connector",
    handler: "HandlerData",
) -> List[HandlerVisibleField]:
    """All fields visible to ``handler`` on ``connector``, in deterministic
    walker order.

    Order: ``CONNECTION_GENERAL`` -> ``CONNECTION_PROFILE`` ->
    ``CAPABILITIES_GENERAL`` -> ``CONFIGURATIONS_GENERAL`` ->
    ``CONFIGURATIONS_CAPABILITY``.

    No dedup (spec §7 Q1) — one entry per physical field-definition
    location. If a field id appears in two YAMLs, two entries are
    returned.

    Missing files (``connection.yaml`` / ``capabilities.yaml`` /
    ``configurations.yaml``) are handled gracefully — the walker skips
    that origin and continues with the others.

    **Not included:** serializer ``computed_fields``. Those are
    server-side output rules (see :class:`SerializerData.computed_fields`)
    and are not user-visible connector fields, so they fall outside this
    walker's contract by design (spec §7 Q3). Consumers that need to
    reason about them should read ``handler.serializer.computed_fields``
    directly — it's already a first-class parsed list on the model
    (``List[ComputedFieldRule]``). Adding a ``SERIALIZER_COMPUTED`` origin
    would force a nonsensical ``source_file`` value (computed fields have
    no per-field physical YAML location) and would blur the
    "which YAML file owns this?" invariant that per-file
    ``.connector-ignore`` routing relies on.
    """
    serializer_rename = _serializer_rename_map(handler)
    results: List[HandlerVisibleField] = []
    results.extend(_walk_connection_general(connector, handler, serializer_rename))
    results.extend(_walk_connection_profiles(connector, handler, serializer_rename))
    results.extend(_walk_capabilities_general(connector, handler, serializer_rename))
    results.extend(_walk_configurations_general(connector, handler, serializer_rename))
    results.extend(_walk_configurations_capability(connector, handler, serializer_rename))
    return results


__all__ = [
    "FieldOrigin",
    "HandlerVisibleField",
    "walk_visible_fields",
]

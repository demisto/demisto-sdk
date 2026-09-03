"""CO145 - NoImpliedFetchCheckbox.

Per §3.4 note 5 / §3.7 of the standard connector guide, the "implied
fetch checkbox" for a declared collection capability MUST NOT be
emitted as a user-visible field on the connector. Choosing the
capability IS the opt-in - the fetch flag itself is delivered to the
integration via ``serializer.yaml`` ``computed_fields`` (see CO130 /
CO171 for the positive rule).

Forbidden emissions (as user fields):

- ``isFetch``            (fetch-issues)
- ``feed``               (threat-intelligence-and-enrichment)
- ``isFetchEvents``      (log-collection)
- ``isFetchAssets``      (fetch-assets-and-vulnerabilities)
- ``isFetchCredentials`` (fetch-secrets)

Source-of-truth design (why this validator does NOT use
``handler.resolved_params``):

``ConnectorParser._build_resolved_params`` builds its per-capability
slice by walking ``self.capabilities`` and matching by parent
capability id (``if cap.id in handler_cap_ids`` at
``_collect_handler_fields`` step 4). But grouped connectors namespace
their ``configurations.yaml`` ``configurations[].id`` by
SUB-capability id (e.g. ``log-collection_akamai-waf-siem``, not the
bare ``log-collection`` parent). The parser then constructs
``per_cap_configs`` keyed by whatever raw id appears in
``configurations.yaml`` (sub-cap ids), then merges into
``self.capabilities`` under the PARENT id
(``per_cap_configs[cap["id"]]`` where ``cap["id"]`` is the parent).
The sub-cap entries are silently dropped from ``self.capabilities``,
so their fields never land in ``handler.resolved_params``. Result:
a validator that only reads ``resolved_params`` is blind to
forbidden checkboxes in grouped-connector sub-capability
``configurations[]`` blocks - exactly the akamai
``log-collection_akamai-waf-siem: isFetchEvents`` case CO145 is
meant to catch.

CO130 / CO136 dodge this by reading
``connector.configurations_file.file_content`` directly via
``find_capability_config_entry``. CO145 does the same, so a future
fix to the parser is a no-op for this validator (it will keep
finding forbidden fields either way).

We walk THREE sources for defense-in-depth:

1. ``connection.yaml`` - top-level ``general_configurations`` and
   any ``profiles[]`` bound to the handler via
   ``handler.capabilities[].auth_options[].id``.
2. ``capabilities.yaml`` - top-level ``general_configurations``.
3. ``configurations.yaml`` - top-level ``general_configurations``
   AND per-capability ``configurations[]`` entries whose ``id``
   matches ``handler.capabilities[].id`` (bare or namespaced).

Serializer ``computed_fields`` outputs are **not** walked - they
live on ``handler.serializer.computed_fields`` and are
structurally separate from the raw ``fields[]`` blocks. The
legitimate ``computed_fields``-driven ``isFetch: true`` (CO130 /
CO171 shape, e.g. akamai xsoar-guardicore-v2) is NOT flagged.

We match on the **runtime name**: the raw YAML ``id`` after
``serializer.yaml`` ``field_mappings`` rename. A grouped-connector
namespaced checkbox that gets renamed back to a forbidden id
(e.g. ``xsoar-akamai-waf-siem_isFetchEvents`` -> ``isFetchEvents``)
still fails, because the integration would still receive a
user-controllable value.

Granularity: one ``ValidationResult`` per (handler, forbidden field)
finding. ``path`` is set to the concrete on-disk YAML that owns the
finding, so the standard ``[file:<...>]`` ignore chain in
``.connector-ignore`` targets the right file. A connector that
legitimately needs one specific checkbox (e.g. ``akamai`` keeping
``isFetchEvents`` on ``log-collection_akamai-waf-siem``) can silence
CO145 for that file only:

    [file:configurations.yaml]
    ignore=CO145

Non-XSOAR handlers are skipped (mirrors CO120 / CO130 / CO136).
The forbidden-checkbox contract is XSOAR-migration-specific
(§3.7); non-XSOAR handlers are not policed by CO145.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, Iterator, List, Optional, Set, Tuple

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

# The 5 forbidden user-checkbox ids, keyed by the capability that
# implies each. The capability id is included only for the error
# message; the validator itself never inspects the connector's
# declared capabilities.
FORBIDDEN_FETCH_CHECKBOXES: Dict[str, str] = {
    "isFetch": "fetch-issues",
    "feed": "threat-intelligence-and-enrichment",
    "isFetchEvents": "log-collection",
    "isFetchAssets": "fetch-assets-and-vulnerabilities",
    "isFetchCredentials": "fetch-secrets",
}
FORBIDDEN_FETCH_CHECKBOX_NAMES: FrozenSet[str] = frozenset(
    FORBIDDEN_FETCH_CHECKBOXES.keys()
)


class NoImpliedFetchCheckboxValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO145"
    description = (
        "Forbid emitting the implied fetch checkbox for a declared "
        "collection capability as a user-visible field. The 5 "
        "forbidden ids are isFetch / feed / isFetchEvents / "
        "isFetchAssets / isFetchCredentials. Choosing the capability "
        "IS the opt-in; the backend flag itself must be emitted via "
        "serializer.yaml computed_fields (CO130 / CO171)."
    )
    rationale = (
        "In UCP the collection capabilities are declarative - picking "
        "the capability wires the fetch job in the backend. Also "
        "exposing the legacy fetch-flag checkbox to the user creates "
        "two independent switches for the same behavior, which is "
        "both confusing and a source of drift (the checkbox and the "
        "capability can disagree). The serializer computed_fields "
        "shape is the only supported channel for delivering the "
        "backend fetch flag; the user checkbox must be omitted."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "forbidden implied-fetch checkbox '{field_id}' (capability "
        "'{capability_id}') is emitted as a user-visible field in "
        "'{source_file}'{location_hint}. Remove the field entry - "
        "the backend flag must be delivered via serializer.yaml "
        "`computed_fields` gated on the capability (see CO130 / "
        "CO171)."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # A finding may originate from any of connection.yaml,
    # capabilities.yaml, or configurations.yaml. Listing all three
    # keeps the ``.connector-ignore`` preflight
    # (``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    # ``_resolve_ignore_file_keys``) able to short-circuit whichever
    # per-file suppression the author wrote - same rationale
    # documented on CO130.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_CAPABILITIES,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            file_paths = self._source_file_paths(connector)
            for handler in connector.xsoar_handlers:
                results.extend(self._check_handler(connector, handler, file_paths))

        return results

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _source_file_paths(connector: Connector) -> Dict[str, Optional[Path]]:
        """Map the three source-file literal keys to concrete on-disk
        ``Path`` values so per-finding ``path`` can route through the
        standard ``.connector-ignore`` chain."""
        return {
            "connection.yaml": connector.connection_file.file_path,
            "capabilities.yaml": connector.capabilities_file.file_path,
            "configurations.yaml": connector.configurations_file.file_path,
        }

    # ------------------------------------------------------------------
    # Serializer rename resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _serializer_rename_map(handler: HandlerData) -> Dict[str, str]:
        """Return ``{connector_id: runtime_name}`` from
        ``handler.serializer.field_mappings``. Empty when no
        serializer or no ``field_mappings``.

        Mirrors CO130's ``_serializer_rename_map`` behavior. A
        grouped connector namespaces its field ids per view_group
        (``xsoar-akamai-waf-siem_isFetchEvents``) and renames them
        back to the canonical runtime name (``isFetchEvents``) via a
        serializer entry:

            field_mappings:
              - id: xsoar-akamai-waf-siem_isFetchEvents
                field_name: isFetchEvents
        """
        mapping: Dict[str, str] = {}
        ser = handler.serializer
        if ser is None:
            return mapping
        for fm in ser.field_mappings or []:
            if fm.field_name:
                mapping[fm.id] = fm.field_name
        return mapping

    # ------------------------------------------------------------------
    # Raw YAML walkers - one per source file
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_field_dicts_from_field_groups(
        groups: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Yield each raw field dict from ``configurations[*].fields[*]``
        shape. Defensive against malformed YAML (non-list, non-dict)."""
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

    def _iter_connection_yaml_fields(
        self, connector: Connector, handler: HandlerData
    ) -> Iterator[Tuple[Dict[str, Any], str]]:
        """Yield ``(field_dict, location_hint)`` for every field entry in
        ``connection.yaml`` visible to ``handler``:

        - top-level ``general_configurations.configurations[*].fields[*]``,
          hint ``"general_configurations"``.
        - ``profiles[*].configurations[*].fields[*]`` for each profile
          whose ``id`` is bound to the handler via
          ``handler.capabilities[].auth_options[].id``. Hint
          ``"profile '<profile_id>'"``.
        """
        raw = connector.connection_file.file_content
        if not isinstance(raw, dict):
            return

        general = raw.get("general_configurations")
        if isinstance(general, dict):
            for field in self._iter_field_dicts_from_field_groups(
                general.get("configurations")
            ):
                yield field, "general_configurations"

        # Profiles bound to this handler.
        auth_ids: Set[str] = {
            ao.id for hc in handler.capabilities for ao in hc.auth_options
        }
        profiles = raw.get("profiles")
        if not isinstance(profiles, list):
            return
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            profile_id = profile.get("id")
            if profile_id not in auth_ids:
                continue
            for field in self._iter_field_dicts_from_field_groups(
                profile.get("configurations")
            ):
                yield field, f"profile '{profile_id}'"

    def _iter_capabilities_yaml_fields(
        self, connector: Connector
    ) -> Iterator[Tuple[Dict[str, Any], str]]:
        """Yield ``(field_dict, "general_configurations")`` for every
        field entry in ``capabilities.yaml``'s top-level
        ``general_configurations``. This surface is shared across
        every handler (no per-handler scoping) so iteration is
        connector-scoped; deduplication per handler is handled by the
        caller."""
        raw = connector.capabilities_file.file_content
        if not isinstance(raw, dict):
            return
        general = raw.get("general_configurations")
        if not isinstance(general, dict):
            return
        for field in self._iter_field_dicts_from_field_groups(
            general.get("configurations")
        ):
            yield field, "general_configurations"

    def _iter_configurations_yaml_fields(
        self, connector: Connector, handler: HandlerData
    ) -> Iterator[Tuple[Dict[str, Any], str]]:
        """Yield ``(field_dict, location_hint)`` for every field entry in
        ``configurations.yaml`` visible to ``handler``:

        - top-level ``general_configurations.configurations[*].fields[*]``,
          hint ``"general_configurations"``.
        - each per-capability entry
          ``configurations[*]`` whose ``id`` is in
          ``handler.capabilities[].id``. Hint ``"capability '<cap_id>'"``.

        Deliberately reads the raw dict (``configurations_file.file_content``)
        rather than ``self.capabilities`` on the connector object,
        because the parser drops sub-capability-keyed configurations
        entries when merging (see module docstring). This walker
        matches on whatever raw id the author wrote - parent or
        sub-capability id.
        """
        raw = connector.configurations_file.file_content
        if not isinstance(raw, dict):
            return

        general = raw.get("general_configurations")
        if isinstance(general, dict):
            for field in self._iter_field_dicts_from_field_groups(
                general.get("configurations")
            ):
                yield field, "general_configurations"

        handler_cap_ids: Set[str] = {hc.id for hc in handler.capabilities}
        entries = raw.get("configurations")
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            if entry_id not in handler_cap_ids:
                continue
            for field in self._iter_field_dicts_from_field_groups(
                entry.get("configurations")
            ):
                yield field, f"capability '{entry_id}'"

    # ------------------------------------------------------------------
    # Per-handler check
    # ------------------------------------------------------------------

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
        file_paths: Dict[str, Optional[Path]],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, forbidden field)
        finding.

        We assemble a per-handler iterator that yields
        ``(field_dict, source_file, location_hint)`` triples across all
        three source files, then apply the serializer rename to get
        the runtime name and check it against the forbidden set.

        Findings are deduplicated by runtime name per handler: the
        same forbidden id can appear more than once (e.g. general
        configs + a per-cap entry), but the author fixes it once at
        the source. First-seen wins for the source_file / hint that
        gets reported; iteration order is
        connection.yaml -> capabilities.yaml -> configurations.yaml.
        """
        rename_map = self._serializer_rename_map(handler)

        # Yield tuples of (field_dict, source_file, location_hint).
        def _iter_all() -> Iterator[Tuple[Dict[str, Any], str, str]]:
            for field, hint in self._iter_connection_yaml_fields(connector, handler):
                yield field, "connection.yaml", hint
            for field, hint in self._iter_capabilities_yaml_fields(connector):
                yield field, "capabilities.yaml", hint
            for field, hint in self._iter_configurations_yaml_fields(
                connector, handler
            ):
                yield field, "configurations.yaml", hint

        results: List[ValidationResult] = []
        seen: Set[str] = set()

        for field, source_file, location_hint in _iter_all():
            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_name = rename_map.get(raw_id, raw_id)
            if runtime_name not in FORBIDDEN_FETCH_CHECKBOX_NAMES:
                continue
            if runtime_name in seen:
                continue
            seen.add(runtime_name)

            capability_id = FORBIDDEN_FETCH_CHECKBOXES[runtime_name]
            path = file_paths.get(source_file)

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        capability_id=capability_id,
                        source_file=source_file,
                        location_hint=(f" ({location_hint})" if location_hint else ""),
                    ),
                    content_object=connector,
                    path=path,
                )
            )

        return results

"""CO141 - IsMirroringOmittedValidator.

Per §3.2 / §3.7 of the standard connector guide, mirroring is
**out of scope on the Platform**. The two mirroring params
(``outgoingMapperId``, ``defaultMapperOut``) MUST NOT be emitted
as user-visible YAML field entries anywhere in the XSOAR-visible
surface of a connector.

Structurally identical to CO145 (`NoImpliedFetchCheckboxValidator`)
— same raw-YAML walkers, same serializer-rename resolution, same
per-finding granularity, same routing to per-source-file ``path``.
The only difference is the forbidden-set constant.

Design rationale (mirrors CO145's docstring):

- **Walks raw YAML files directly**, not ``handler.resolved_params``.
  ``ConnectorParser._parse_capabilities_with_configs`` merges
  per-capability ``configurations[]`` entries by PARENT capability
  id, so grouped-connector sub-cap entries never reach
  ``resolved_params``. Direct read matches the author's YAML shape
  and is immune to that parser quirk.

- **Serializer ``computed_fields`` outputs are structurally
  excluded** (walkers only look at ``fields[]`` blocks). So if any
  legitimate use case ever emits a mirroring-adjacent value via
  computed_fields (unlikely — mirroring is Platform-out-of-scope),
  it would not be flagged here.

- **Match key is the post-serializer runtime name** (via
  ``serializer.yaml`` ``field_mappings`` rename), so grouped
  connectors that namespace the field id (e.g.
  ``xsoar-foo_outgoingMapperId`` → ``outgoingMapperId``) still
  fail. Because the integration receives the runtime name.

- **Ignore key routes per source file** — a connector that legit
  needs to keep mirroring on for backward-compat (unlikely, given
  §3.2) can silence per file via
  ``[file:<...>] ignore=CO141`` in ``.connector-ignore``.

Non-XSOAR handlers are skipped (mirrors CO145 / CO120 / CO130 /
CO136 — XSOAR migration contract only).
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

# The 2 forbidden mirroring param ids. Kept as a bare set (not a
# {id: reason} mapping like CO145's dict) because the "why" is the
# same for both - mirroring is out of scope on Platform.
FORBIDDEN_MIRRORING_PARAMS: FrozenSet[str] = frozenset(
    {"outgoingMapperId", "defaultMapperOut"}
)


class IsMirroringOmittedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO141"
    description = (
        "Forbid emitting mirroring params (`outgoingMapperId`, "
        "`defaultMapperOut`) as user-visible YAML field entries in "
        "the XSOAR-visible surface of a connector. Mirroring is out "
        "of scope on the Platform (§3.2)."
    )
    rationale = (
        "The XSOAR Platform does not support outgoing mirroring - "
        "the runtime has no consumer for these params, so exposing "
        "them to the user is misleading (the setting has no effect) "
        "and pollutes the instance-creation form. Any legacy "
        "integration YML that still declares these params must be "
        "stripped from the connector's user-visible surface at "
        "migration time."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "forbidden mirroring param '{field_id}' is emitted as a "
        "user-visible field in '{source_file}'{location_hint}. "
        "Remove the field entry - mirroring is out of scope on "
        "Platform (§3.2)."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # Same rationale as CO145: a finding may originate from any of
    # the three YAML files, so listing all three in
    # ``related_file_type`` keeps the ``.connector-ignore`` preflight
    # (``ConnectorsValidator.should_run`` -> ``is_error_ignored`` ->
    # ``_resolve_ignore_file_keys``) able to short-circuit whichever
    # per-file suppression the author wrote.
    related_file_type = [
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_CAPABILITIES,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
    ]

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
    # Helpers (structurally identical to CO145; kept duplicated rather
    # than lifting to a shared module to avoid a churn-prone edit that
    # would touch every walker at once. If a third negative-set
    # validator lands, we can hoist ``_iter_*_fields`` +
    # ``_serializer_rename_map`` into a shared helper module.)
    # ------------------------------------------------------------------

    @staticmethod
    def _source_file_paths(connector: Connector) -> Dict[str, Optional[Path]]:
        return {
            "connection.yaml": connector.connection_file.file_path,
            "capabilities.yaml": connector.capabilities_file.file_path,
            "configurations.yaml": connector.configurations_file.file_path,
        }

    @staticmethod
    def _serializer_rename_map(handler: HandlerData) -> Dict[str, str]:
        """Return ``{connector_id: runtime_name}`` from
        ``handler.serializer.field_mappings``. Empty when no
        serializer or no ``field_mappings``.
        """
        mapping: Dict[str, str] = {}
        ser = handler.serializer
        if ser is None:
            return mapping
        for fm in ser.field_mappings or []:
            if fm.field_name:
                mapping[fm.id] = fm.field_name
        return mapping

    @staticmethod
    def _iter_field_dicts_from_field_groups(
        groups: Any,
    ) -> Iterator[Dict[str, Any]]:
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
        raw = connector.connection_file.file_content
        if not isinstance(raw, dict):
            return

        general = raw.get("general_configurations")
        if isinstance(general, dict):
            for field in self._iter_field_dicts_from_field_groups(
                general.get("configurations")
            ):
                yield field, "general_configurations"

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

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
        file_paths: Dict[str, Optional[Path]],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, forbidden field)
        finding. Deduplicated by runtime name per handler."""
        rename_map = self._serializer_rename_map(handler)

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
            if runtime_name not in FORBIDDEN_MIRRORING_PARAMS:
                continue
            if runtime_name in seen:
                continue
            seen.add(runtime_name)

            path = file_paths.get(source_file)

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        source_file=source_file,
                        location_hint=(f" ({location_hint})" if location_hint else ""),
                    ),
                    content_object=connector,
                    path=path,
                )
            )

        return results

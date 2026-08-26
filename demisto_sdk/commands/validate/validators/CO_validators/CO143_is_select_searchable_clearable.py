"""CO143 - IsSelectSearchableClearableValidator.

Per §3.7 field rule 9 of the standard connector guide, every
``select`` / ``multi_select`` field exposed to XSOAR handlers MUST:

1. Set ``options.clearable: true`` unconditionally. The user must
   always be able to un-pick a picked value.
2. Set ``options.searchable: true`` when the field's
   ``options.values`` contains **more than 5** items OR when the
   field's values are resolved dynamically at runtime (via
   ``options.dynamic_values.dynamicField`` — or the legacy
   ``options.dynamicField`` form). Dynamic-value fields have no
   authoring-time count, so we conservatively assume "may exceed 5"
   and require ``searchable: true``.

Static enumerations with ≤5 items are the only case where
``searchable`` may be omitted — those are ergonomic to scan
directly.

Structurally a raw-YAML walker (like CO141 / CO145). Walks the
connector's ``connection.yaml`` (general_configurations +
handler-referenced profiles) + ``capabilities.yaml``
(general_configurations) + ``configurations.yaml``
(general_configurations + per-capability entries for the handler's
declared capabilities). Fields whose ``field_type`` is anything
other than ``select`` / ``multi_select`` are skipped.

Runtime-name resolution goes through the handler's
``serializer.yaml`` ``field_mappings`` rename map (raw connector id
→ runtime name) so grouped-connector namespaced ids report as the
runtime name the integration actually sees.

Per-finding granularity: one ``ValidationResult`` per
(handler, runtime_name, defect) where ``defect`` ∈ {``clearable``,
``searchable``}. Dedupe key = (runtime_name, defect) per handler so
the same field appearing in multiple source files fires once for
each defect.

Non-XSOAR handlers are skipped (mirrors CO141 / CO145 policy).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

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

# Field types that participate in CO143. Anything else is skipped.
SELECT_FIELD_TYPES = frozenset({"select", "multi_select"})

# Static-values threshold above which searchable is required. Dynamic
# values are treated as "may exceed this" (count unknown at authoring
# time) and always require searchable too.
SEARCHABLE_MIN_ITEMS = 5


class IsSelectSearchableClearableValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO143"
    description = (
        "Every `select` / `multi_select` field visible to XSOAR "
        "handlers must set `options.clearable: true` unconditionally "
        "and `options.searchable: true` when `options.values` has "
        "more than 5 items or when values are resolved dynamically "
        "(dynamicField) — dynamic values have unknown authoring-time "
        "count, so we conservatively assume they exceed the "
        "threshold."
    )
    rationale = (
        "The `clearable` flag guarantees the user can always un-pick "
        "a value; without it, once a value is selected the picker "
        "traps the user in that choice. The `searchable` flag only "
        "adds value when the picker has enough options to warrant a "
        "search box — small enumerations (≤5 static items) are "
        "ergonomic to scan directly. Dynamic-value fields resolve "
        "their options at runtime with no upper bound, so we treat "
        "them as always-searchable to protect the UX. Enforcing "
        "both invariants keeps the configuration UI predictable "
        "across every connector."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': select "
        "field '{field_id}' in '{source_file}'{location_hint} is "
        "missing required 'options.{defect}: true' "
        "(values_count={values_count}). Add "
        "'options.{defect}: true'."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # A finding may originate from any of the three YAML files, so
    # listing all three keeps the per-file ``.connector-ignore``
    # preflight resolution able to short-circuit whichever
    # per-source-file suppression the author wrote.
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
    # Helpers (structurally identical to CO141; kept duplicated per
    # the codebase's chosen policy - see CO141 lines 122-126.)
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

    # ------------------------------------------------------------------
    # CO143-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_dynamic_field(options: Any) -> bool:
        """Detect a dynamicField-driven field. Values are resolved at
        runtime, so authoring-time count is unknown."""
        if not isinstance(options, dict):
            return False
        dyn_values = options.get("dynamic_values")
        if isinstance(dyn_values, dict) and dyn_values.get("dynamicField"):
            return True
        # Legacy shape used by older connectors.
        if options.get("dynamicField"):
            return True
        return False

    @staticmethod
    def _values_count(options: Any) -> int:
        """Return the item count of ``options.values``. Dicts count by
        top-level keys, lists count by length, anything else = 0."""
        if not isinstance(options, dict):
            return 0
        values = options.get("values")
        if isinstance(values, dict):
            return len(values)
        if isinstance(values, list):
            return len(values)
        return 0

    @staticmethod
    def _flag_true(options: Any, key: str) -> bool:
        """True iff ``options[key]`` is exactly ``True``."""
        if not isinstance(options, dict):
            return False
        return options.get(key) is True

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
        file_paths: Dict[str, Optional[Path]],
    ) -> List[ValidationResult]:
        """Emit one ``ValidationResult`` per (handler, runtime_name,
        defect) finding. Deduplicated per handler."""
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
        seen: Set[Tuple[str, str]] = set()

        for field, source_file, location_hint in _iter_all():
            field_type = field.get("field_type")
            if field_type not in SELECT_FIELD_TYPES:
                continue

            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_name = rename_map.get(raw_id, raw_id)

            options = field.get("options")
            is_dynamic = self._has_dynamic_field(options)
            values_count = self._values_count(options)
            # Message hint - "dynamic" for dynamicField fields so
            # authors understand why searchable is required despite
            # no static values list.
            values_count_str = "dynamic" if is_dynamic else str(values_count)

            # Defect 1: clearable is always required.
            if not self._flag_true(options, "clearable"):
                key = (runtime_name, "clearable")
                if key not in seen:
                    seen.add(key)
                    results.append(
                        self._build_result(
                            connector=connector,
                            handler=handler,
                            runtime_name=runtime_name,
                            source_file=source_file,
                            location_hint=location_hint,
                            defect="clearable",
                            values_count_str=values_count_str,
                            file_paths=file_paths,
                        )
                    )

            # Defect 2: searchable required when values may exceed the
            # threshold. Dynamic-value fields always qualify (count
            # unknown); static fields qualify only when >5 items.
            searchable_required = is_dynamic or values_count > SEARCHABLE_MIN_ITEMS
            if searchable_required and not self._flag_true(options, "searchable"):
                key = (runtime_name, "searchable")
                if key not in seen:
                    seen.add(key)
                    results.append(
                        self._build_result(
                            connector=connector,
                            handler=handler,
                            runtime_name=runtime_name,
                            source_file=source_file,
                            location_hint=location_hint,
                            defect="searchable",
                            values_count_str=values_count_str,
                            file_paths=file_paths,
                        )
                    )

        return results

    def _build_result(
        self,
        connector: Connector,
        handler: HandlerData,
        runtime_name: str,
        source_file: str,
        location_hint: str,
        defect: str,
        values_count_str: str,
        file_paths: Dict[str, Optional[Path]],
    ) -> ValidationResult:
        return ValidationResult(
            validator=self,
            message=self.error_message.format(
                connector_id=connector.object_id,
                handler_id=handler.id,
                field_id=runtime_name,
                source_file=source_file,
                location_hint=(f" ({location_hint})" if location_hint else ""),
                defect=defect,
                values_count=values_count_str,
            ),
            content_object=connector,
            path=file_paths.get(source_file),
        )

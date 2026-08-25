"""CO138 - IsParamConfigTypeValidValidator.

Per the standard connector guide, only a small **whitelist** of
platform-canonical params may carry the
``metadata.xsoar.config_type: "backend"`` marker. Every OTHER
user-visible field in the connector's XSOAR-visible surface MUST
NOT set ``config_type: backend``.

The whitelist (6 canonical field ids):

- ``engine`` (per connection profile)
- ``engineGroup`` (per connection profile)
- ``mappingId`` (fetch-issues classifier)
- ``incomingMapperId`` (fetch-issues incoming mapper)
- ``defaultIgnore`` (automation-and-remediation)
- ``integrationLogLevel`` (general_configurations)

``outgoingMapperId`` is intentionally excluded because CO141 (and
§3.2) forbid it entirely as a user-visible field on Platform - it
should never be present in the first place, so there's nothing to
mark as backend.

Two-directional check (per handler):

1. **Whitelist-side:** For each whitelisted field that IS present
   in the XSOAR-visible surface (matched by RUNTIME name, so
   grouped-connector namespaced ids like ``xsoar-akamai_engine``
   matched via ``serializer.yaml`` ``field_mappings`` rename to
   ``engine``), assert ``metadata.xsoar.config_type == "backend"``.
   A whitelisted field without the marker is a violation because
   the BE contract requires the field's stored-value shape to
   route through the backend-only channel.

2. **Anti-whitelist side:** For every OTHER field with
   ``metadata.xsoar.config_type == "backend"``, flag it - the
   marker is reserved for the 6 canonical ids only. This catches
   typos (``integratoinLogLevel``), copy-paste drift (someone
   lifted the block for a custom field), and legitimate custom
   fields that shouldn't be marked backend.

Structural sibling of CO145 / CO141: reuses the raw-YAML walker
pattern (walks the three connector YAML files' ``file_content``
directly, matches on the post-serializer runtime name). Non-XSOAR
handlers skipped.

Per-finding granularity: one ``ValidationResult`` per
(handler, field, defect). Deduplicated by (runtime_name, defect)
per handler.
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

# ============================================================
# CO138 constants
# ============================================================

# The 6 field ids that MAY carry ``metadata.xsoar.config_type:
# "backend"``. All matches use the post-serializer RUNTIME name.
#
# ``outgoingMapperId`` is intentionally NOT included - CO141 /
# §3.2 forbid it as a user-visible field on Platform. If it does
# appear, CO141 will flag it; CO138's anti-whitelist branch will
# also flag it (correctly), but the first fix is per CO141.
WHITELISTED_BACKEND_PARAMS: FrozenSet[str] = frozenset(
    {
        "engine",
        "engineGroup",
        "mappingId",
        "incomingMapperId",
        "defaultIgnore",
        "integrationLogLevel",
    }
)

# The literal string the BE contract expects.
BACKEND_CONFIG_TYPE = "backend"

# Defect kinds used to dedupe per-handler findings.
_DEFECT_MISSING_BACKEND = "missing_backend"
_DEFECT_UNEXPECTED_BACKEND = "unexpected_backend"


# ============================================================
# CO138 validator
# ============================================================
class IsParamConfigTypeValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO138"
    description = (
        "Validates that the `metadata.xsoar.config_type: \"backend\"` "
        "marker is set on EXACTLY the 6 whitelisted canonical field "
        "ids (engine, engineGroup, mappingId, incomingMapperId, "
        "defaultIgnore, integrationLogLevel) and on no other field. "
        "Matched by post-serializer runtime name so grouped-connector "
        "namespaced ids resolve correctly."
    )
    rationale = (
        "The `config_type: backend` marker tells the FE this field's "
        "value is populated/updated by the BE (not the user directly), "
        "which drives form rendering, validation, and stored-value "
        "handling. Marking a non-canonical field as backend causes "
        "silent value-shape drift; missing the marker on a canonical "
        "field causes the FE to try to save the user's raw value into "
        "a BE-managed slot. Both are BE-contract regressions."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "field '{field_id}' in '{source_file}'{location_hint} "
        "{problem}."
    )
    related_field = "configurations"
    is_auto_fixable = False
    # Same rationale as CO145 / CO141: a finding may originate from
    # any of the three YAML files, so listing all three keeps the
    # per-file ignore preflight able to short-circuit.
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
    # Walkers (structurally identical to CO141 / CO145 - three raw-YAML
    # sweeps returning `(field_dict, source_file, location_hint)`)
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
        """``{connector_id: runtime_name}`` from
        ``handler.serializer.field_mappings``. Empty when no
        serializer.
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
    # Per-handler two-directional check
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_config_type(field: Dict[str, Any]) -> Optional[str]:
        """Return the ``field.metadata.xsoar.config_type`` string,
        or ``None`` if any part of the chain is missing / wrong type.
        Silent about type mismatches - a malformed value is not
        ``"backend"`` and therefore won't false-fail the whitelist
        check.
        """
        metadata = field.get("metadata")
        if not isinstance(metadata, dict):
            return None
        xsoar = metadata.get("xsoar")
        if not isinstance(xsoar, dict):
            return None
        val = xsoar.get("config_type")
        if isinstance(val, str):
            return val
        return None

    def _check_handler(
        self,
        connector: Connector,
        handler: HandlerData,
        file_paths: Dict[str, Optional[Path]],
    ) -> List[ValidationResult]:
        rename_map = self._serializer_rename_map(handler)

        def _iter_all() -> Iterator[Tuple[Dict[str, Any], str, str]]:
            for field, hint in self._iter_connection_yaml_fields(
                connector, handler
            ):
                yield field, "connection.yaml", hint
            for field, hint in self._iter_capabilities_yaml_fields(connector):
                yield field, "capabilities.yaml", hint
            for field, hint in self._iter_configurations_yaml_fields(
                connector, handler
            ):
                yield field, "configurations.yaml", hint

        results: List[ValidationResult] = []
        # Dedupe key = (runtime_name, defect). A field appearing in
        # two source files with the same defect (unlikely but possible
        # via profile+general duplication) only fires once per
        # handler.
        seen: Set[Tuple[str, str]] = set()

        for field, source_file, location_hint in _iter_all():
            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_name = rename_map.get(raw_id, raw_id)
            actual = self._extract_config_type(field)
            is_backend = actual == BACKEND_CONFIG_TYPE
            is_whitelisted = runtime_name in WHITELISTED_BACKEND_PARAMS

            defect: Optional[str] = None
            problem: Optional[str] = None
            if is_whitelisted and not is_backend:
                defect = _DEFECT_MISSING_BACKEND
                if actual is None:
                    problem = (
                        f"is missing `metadata.xsoar.config_type: "
                        f"\"{BACKEND_CONFIG_TYPE}\"` - this canonical "
                        f"field is BE-managed and MUST carry the "
                        f"backend marker"
                    )
                else:
                    problem = (
                        f"has `metadata.xsoar.config_type: "
                        f"\"{actual}\"` - canonical field MUST be "
                        f"`\"{BACKEND_CONFIG_TYPE}\"`"
                    )
            elif not is_whitelisted and is_backend:
                defect = _DEFECT_UNEXPECTED_BACKEND
                problem = (
                    f"has `metadata.xsoar.config_type: "
                    f"\"{BACKEND_CONFIG_TYPE}\"` but is NOT one of the "
                    f"whitelisted canonical fields "
                    f"({', '.join(sorted(WHITELISTED_BACKEND_PARAMS))}). "
                    f"Remove the marker or rename the field"
                )

            if defect is None:
                continue
            if (runtime_name, defect) in seen:
                continue
            seen.add((runtime_name, defect))

            path = file_paths.get(source_file)
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        field_id=runtime_name,
                        source_file=source_file,
                        location_hint=(
                            f" ({location_hint})" if location_hint else ""
                        ),
                        problem=problem,
                    ),
                    content_object=connector,
                    path=path,
                )
            )

        return results

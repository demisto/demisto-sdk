"""CO152 - IsLongRunningPortGatedValidator.

The ``longRunningPort`` field is meaningful only when a long-
running server integration is active AND the user hasn't picked a
remote execution target (engine / engineGroup) — a
remotely-executed integration doesn't own the local port. If a
handler emits ``longRunningPort`` as a user-visible field,
``triggers.yaml`` MUST contain a trigger that hides the port
unless BOTH:

1. The long-running signal is on. Two shapes are legitimate:

   - **Shape 1 (user checkbox)** — a
     ``longRunning: checkbox`` field is emitted user-visibly.
     The gate condition targets ``id: longRunning`` with
     ``operator: eq, value: true``.
   - **Shape 2 (serializer emit)** — the handler's
     ``serializer.yaml`` ``computed_fields`` emits
     ``longRunning: true`` gated on a capability condition. The
     gate condition targets ``type: capability`` with
     ``options.capability_id`` equal to that computed rule's
     capability and ``options.value == "on"``.

2. Neither ``engine`` nor ``engineGroup`` is currently selected —
   both must be empty. These checks are *conditional* on the
   fields existing in the handler's visible surface:

   - Both present → AND children include both ``is_empty``
     checks.
   - Only one present → AND child includes that one check only.
   - Neither present → NO engine/engineGroup children; the
     conditions collapse to just the shape-1 or shape-2 signal.

Discovery
---------
1. Walk each XSOAR handler's visible surface (connection.yaml +
   capabilities.yaml + configurations.yaml, same walkers as
   CO141/CO143/CO145) for ``longRunningPort`` fields matched by
   post-serializer runtime name.
2. Determine the shape: check serializer ``computed_fields`` for
   a ``longRunning: true`` emission (shape 2); else check the
   handler's visible surface for a user-visible ``longRunning``
   checkbox (shape 1); else ambiguous.
3. Determine engine/engineGroup presence via runtime-name walk
   of the same surface.
4. Locate a trigger whose ``effects[].id`` matches the raw port
   id with ``hidden: false`` and whose ``conditions`` is an
   ``operator: AND`` block whose ``children`` match the expected
   set exactly (order-insensitive).

Skip conditions
---------------
- No ``longRunningPort`` field found for any XSOAR handler →
  skip.
- ``triggers.yaml`` missing while a ``longRunningPort`` field is
  present → hard fail.

Per-finding granularity
-----------------------
One ``ValidationResult`` per
``(handler.id, raw_long_running_port_id, defect)``. Defects:

- ``missing-longRunning-signal`` — neither serializer emit nor
  checkbox field.
- ``missing-trigger`` — no trigger targets the port field.
- ``wrong-conditions`` — trigger exists but AND-of-N shape
  drifts from the expected set.

Path routing: ``triggers.yaml`` for trigger-related defects;
``configurations.yaml`` for the ``missing-longRunning-signal``
case (nothing gates against).

Non-XSOAR handlers are skipped.

Note on real-world coverage
---------------------------
``longRunningPort`` has zero occurrences in unified-connectors-
content today. CO152 short-circuits vacuously on every current
connector; it's a forward-looking guard for future
long-running-server integrations.
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

CANONICAL_PORT_RUNTIME_NAME = "longRunningPort"
CANONICAL_LONG_RUNNING_RUNTIME_NAME = "longRunning"
CANONICAL_ENGINE_RUNTIME_NAME = "engine"
CANONICAL_ENGINE_GROUP_RUNTIME_NAME = "engineGroup"


class IsLongRunningPortGatedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO152"
    description = (
        "If `longRunningPort` is emitted as a user-visible field, "
        "`triggers.yaml` must contain a trigger that hides it "
        "unless BOTH the long-running signal is on (either the "
        "user-visible `longRunning` checkbox is true OR the "
        "serializer emits `longRunning: true` gated on a capability) "
        "AND no engine / engineGroup is currently selected. "
        "Engine children are conditional on the corresponding field "
        "being present in the handler's visible surface."
    )
    rationale = (
        "`longRunningPort` is only meaningful when a long-running "
        "server integration owns the local port. A remotely-executed "
        "integration (engine / engineGroup selected) doesn't own the "
        "port, so the field is dead UI in that case. The gating "
        "trigger makes the invariant explicit in the manifest."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "longRunningPort field '{raw_port_id}' must be gated by a "
        "trigger with conditions {expected_shape_summary} (defect: "
        "{defect})."
    )
    error_message_no_signal = (
        "Connector '{connector_id}' handler '{handler_id}': "
        "longRunningPort field '{raw_port_id}' has no long-running "
        "signal to gate on — neither a user-visible `longRunning` "
        "checkbox in the handler's surface nor a "
        "`longRunning: true` emission in the handler's "
        "serializer.yaml `computed_fields`. Add one of the two so "
        "there's a signal for the gating trigger to key on."
    )
    related_field = "triggers"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.CONNECTOR_TRIGGERS,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
        RelatedFileType.CONNECTOR_CONNECTION,
        RelatedFileType.CONNECTOR_HANDLER,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            results.extend(self._check_connector(connector))

        return results

    # ------------------------------------------------------------------
    # Per-connector check
    # ------------------------------------------------------------------

    def _check_connector(self, connector: Connector) -> List[ValidationResult]:
        # First scan every XSOAR handler for longRunningPort fields.
        # A handler may see the port via multiple source files; we
        # dedupe by raw id per handler.
        findings: List[Tuple[HandlerData, str]] = []
        seen: Set[Tuple[str, str]] = set()  # (handler.id, raw_id)

        for handler in connector.xsoar_handlers:
            rename_map = self._serializer_rename_map(handler)
            for field, _source_file, _hint in self._iter_all_fields(
                connector, handler
            ):
                raw_id = field.get("id")
                if not isinstance(raw_id, str):
                    continue
                runtime_name = rename_map.get(raw_id, raw_id)
                if runtime_name != CANONICAL_PORT_RUNTIME_NAME:
                    continue
                key = (handler.id, raw_id)
                if key in seen:
                    continue
                seen.add(key)
                findings.append((handler, raw_id))

        if not findings:
            return []

        triggers_by_target = self._triggers_indexed_by_target(connector)
        triggers_yaml_present = isinstance(
            connector.triggers_file.file_content, (dict, list)
        )
        triggers_path = connector.triggers_file.file_path
        configurations_path = connector.configurations_file.file_path

        results: List[ValidationResult] = []
        for handler, raw_port_id in findings:
            rename_map = self._serializer_rename_map(handler)
            # Determine the shape.
            capability_id = self._serializer_long_running_capability(handler)
            has_checkbox = self._handler_has_visible_long_running_checkbox(
                connector, handler, rename_map
            )
            if capability_id is not None:
                shape = "shape2"
            elif has_checkbox:
                shape = "shape1"
            else:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message_no_signal.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            raw_port_id=raw_port_id,
                        ),
                        content_object=connector,
                        path=configurations_path,
                    )
                )
                continue

            # Determine engine / engineGroup presence via runtime name.
            has_engine = self._handler_has_visible_field(
                connector, handler, rename_map, CANONICAL_ENGINE_RUNTIME_NAME
            )
            has_engine_group = self._handler_has_visible_field(
                connector,
                handler,
                rename_map,
                CANONICAL_ENGINE_GROUP_RUNTIME_NAME,
            )
            # For engine children we compare raw ids since triggers use
            # raw ids. Resolve raw ids that map to the runtime engine /
            # engineGroup via the rename map (inverse).
            engine_raw_id = self._raw_id_for_runtime(
                rename_map, CANONICAL_ENGINE_RUNTIME_NAME, has_engine
            )
            engine_group_raw_id = self._raw_id_for_runtime(
                rename_map,
                CANONICAL_ENGINE_GROUP_RUNTIME_NAME,
                has_engine_group,
            )

            expected_summary = self._expected_shape_summary(
                shape, capability_id, has_engine, has_engine_group
            )

            if not triggers_yaml_present:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            raw_port_id=raw_port_id,
                            expected_shape_summary=expected_summary,
                            defect="missing-trigger",
                        ),
                        content_object=connector,
                        path=triggers_path,
                    )
                )
                continue

            candidates = triggers_by_target.get(raw_port_id, [])
            if not candidates:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_id=handler.id,
                            raw_port_id=raw_port_id,
                            expected_shape_summary=expected_summary,
                            defect="missing-trigger",
                        ),
                        content_object=connector,
                        path=triggers_path,
                    )
                )
                continue

            if any(
                self._trigger_matches(
                    trigger,
                    raw_port_id,
                    shape,
                    capability_id,
                    engine_raw_id,
                    engine_group_raw_id,
                )
                for trigger in candidates
            ):
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        raw_port_id=raw_port_id,
                        expected_shape_summary=expected_summary,
                        defect="wrong-conditions",
                    ),
                    content_object=connector,
                    path=triggers_path,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Shape / presence detection
    # ------------------------------------------------------------------

    @staticmethod
    def _serializer_long_running_capability(
        handler: HandlerData,
    ) -> Optional[str]:
        """If the handler's serializer computed_fields emits
        ``longRunning: true`` gated on a capability condition,
        return that capability id. Else None."""
        ser = handler.serializer
        if ser is None:
            return None
        for rule in ser.computed_fields or []:
            outputs = rule.output or []
            emits_long_running = any(
                (out.id == CANONICAL_LONG_RUNNING_RUNTIME_NAME)
                and (out.value in (True, "true", "True"))
                for out in outputs
            )
            if not emits_long_running:
                continue
            # Look for a capability condition in any of the OR groups.
            for group in rule.any_of or []:
                for cond in group.conditions or []:
                    if cond.type != "capability":
                        continue
                    options = cond.options or {}
                    cap_id = options.get("capability_id")
                    if isinstance(cap_id, str):
                        return cap_id
            return None
        return None

    def _handler_has_visible_long_running_checkbox(
        self,
        connector: Connector,
        handler: HandlerData,
        rename_map: Dict[str, str],
    ) -> bool:
        """Return True if a user-visible ``longRunning`` checkbox is
        emitted somewhere in the handler's XSOAR-visible surface."""
        for field, _source_file, _hint in self._iter_all_fields(
            connector, handler
        ):
            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_name = rename_map.get(raw_id, raw_id)
            if runtime_name != CANONICAL_LONG_RUNNING_RUNTIME_NAME:
                continue
            # Accept any field_type - the plan focuses on presence;
            # checkbox is canonical but any user-visible field is a
            # valid signal to gate against.
            return True
        return False

    def _handler_has_visible_field(
        self,
        connector: Connector,
        handler: HandlerData,
        rename_map: Dict[str, str],
        runtime_name_target: str,
    ) -> bool:
        for field, _source_file, _hint in self._iter_all_fields(
            connector, handler
        ):
            raw_id = field.get("id")
            if not isinstance(raw_id, str):
                continue
            runtime_name = rename_map.get(raw_id, raw_id)
            if runtime_name == runtime_name_target:
                return True
        return False

    @staticmethod
    def _raw_id_for_runtime(
        rename_map: Dict[str, str], runtime_name: str, present: bool
    ) -> Optional[str]:
        """Return the raw id that maps to ``runtime_name`` in the
        serializer rename map. If nothing maps (i.e. the field uses
        the bare canonical id with no rename), return the runtime
        name itself when ``present`` is True, else None."""
        if not present:
            return None
        for raw_id, name in rename_map.items():
            if name == runtime_name:
                return raw_id
        # No rename entry — the bare runtime name is also the raw id.
        return runtime_name

    # ------------------------------------------------------------------
    # Trigger analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _triggers_indexed_by_target(
        connector: Connector,
    ) -> Dict[str, List[Dict[str, Any]]]:
        raw = connector.triggers_file.file_content
        entries: List[Any] = []
        if isinstance(raw, list):
            entries = raw
        elif isinstance(raw, dict):
            candidate = raw.get("triggers")
            if isinstance(candidate, list):
                entries = candidate

        indexed: Dict[str, List[Dict[str, Any]]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            effects = entry.get("effects")
            if not isinstance(effects, list):
                continue
            for effect in effects:
                if not isinstance(effect, dict):
                    continue
                target_id = effect.get("id")
                if not isinstance(target_id, str):
                    continue
                indexed.setdefault(target_id, []).append(entry)
        return indexed

    def _trigger_matches(
        self,
        trigger: Dict[str, Any],
        raw_port_id: str,
        shape: str,
        capability_id: Optional[str],
        engine_raw_id: Optional[str],
        engine_group_raw_id: Optional[str],
    ) -> bool:
        """Return True iff the trigger:

        1. has an effect on ``raw_port_id`` with ``hidden: false``,
        2. has conditions that match the expected AND-of-N shape.
        """
        effects = trigger.get("effects", [])
        if not isinstance(effects, list):
            return False
        port_hidden_false = False
        for effect in effects:
            if not isinstance(effect, dict):
                continue
            if effect.get("id") != raw_port_id:
                continue
            action = effect.get("action")
            if isinstance(action, dict) and action.get("hidden") is False:
                port_hidden_false = True
                break
        if not port_hidden_false:
            return False

        conditions = trigger.get("conditions")
        if not isinstance(conditions, dict):
            return False
        # Accept a bare single-child collapsed shape too — if only the
        # signal child is required (no engine / engineGroup / etc.),
        # authors may skip the AND wrapper. Normalize to the child list.
        children = self._and_children(conditions)
        if children is None:
            return False

        # Signal child.
        signal_ok = any(
            self._matches_signal_child(child, shape, capability_id)
            for child in children
        )
        if not signal_ok:
            return False

        # Engine / engineGroup children: required iff the corresponding
        # raw id is not None, forbidden otherwise.
        engine_present_in_conditions = any(
            self._matches_is_empty_child(child, engine_raw_id)
            for child in children
            if engine_raw_id is not None
        )
        engine_group_present_in_conditions = any(
            self._matches_is_empty_child(child, engine_group_raw_id)
            for child in children
            if engine_group_raw_id is not None
        )
        if engine_raw_id is not None and not engine_present_in_conditions:
            return False
        if engine_group_raw_id is not None and not engine_group_present_in_conditions:
            return False

        # Reject extraneous children (drift). Count expected children:
        # 1 signal + optional engine + optional engineGroup.
        expected_child_count = 1
        if engine_raw_id is not None:
            expected_child_count += 1
        if engine_group_raw_id is not None:
            expected_child_count += 1
        # Filter out children that could be either the signal or the
        # engine check for counting.
        recognized_children = 0
        for child in children:
            if self._matches_signal_child(child, shape, capability_id):
                recognized_children += 1
                continue
            if engine_raw_id is not None and self._matches_is_empty_child(
                child, engine_raw_id
            ):
                recognized_children += 1
                continue
            if engine_group_raw_id is not None and self._matches_is_empty_child(
                child, engine_group_raw_id
            ):
                recognized_children += 1
                continue
        return (
            recognized_children == expected_child_count
            and len(children) == expected_child_count
        )

    @staticmethod
    def _and_children(conditions: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Return the list of AND children when ``conditions`` is an
        AND block. Also accepts a bare single condition (no wrapper)
        as a 1-element list — that lets shape-1 / shape-2 collapse
        to a bare condition when no engine children are required."""
        children = conditions.get("children")
        if isinstance(children, list):
            operator = conditions.get("operator")
            # Only accept AND wrappers here — mixed OR shape isn't
            # equivalent to our required conjunction.
            if isinstance(operator, str) and operator.upper() == "AND":
                return [c for c in children if isinstance(c, dict)]
            if operator is None:
                # Ambiguous wrapper; be lenient and treat as AND.
                return [c for c in children if isinstance(c, dict)]
            return None
        # Bare condition acceptable as a single-element list.
        if "id" in conditions or "type" in conditions:
            return [conditions]
        return None

    @staticmethod
    def _matches_signal_child(
        child: Dict[str, Any], shape: str, capability_id: Optional[str]
    ) -> bool:
        """Signal-child match:

        - shape1: ``id: longRunning, operator: eq, value: true``
          (`behavior: value` optional).
        - shape2: ``type: capability, options.capability_id ==
          capability_id, options.value in {"on", true}``.
        """
        if shape == "shape1":
            if child.get("id") != CANONICAL_LONG_RUNNING_RUNTIME_NAME:
                return False
            if child.get("operator") != "eq":
                return False
            return child.get("value") in (True, "true", "True")
        if shape == "shape2":
            if child.get("type") != "capability":
                return False
            options = child.get("options")
            if not isinstance(options, dict):
                return False
            if capability_id is not None and options.get("capability_id") != capability_id:
                return False
            return options.get("value") in ("on", True, "true", "True")
        return False

    @staticmethod
    def _matches_is_empty_child(
        child: Dict[str, Any], expected_id: Optional[str]
    ) -> bool:
        """Match ``id: <expected_id>, operator: is_empty``. Empty when
        expected_id is None (no such child should exist)."""
        if expected_id is None:
            return False
        if child.get("id") != expected_id:
            return False
        return child.get("operator") == "is_empty"

    # ------------------------------------------------------------------
    # Expected-shape summary for error messages
    # ------------------------------------------------------------------

    @staticmethod
    def _expected_shape_summary(
        shape: str,
        capability_id: Optional[str],
        has_engine: bool,
        has_engine_group: bool,
    ) -> str:
        parts: List[str] = []
        if shape == "shape1":
            parts.append("longRunning=true")
        elif shape == "shape2":
            parts.append(
                f"capability='{capability_id}'=on" if capability_id else "capability=on"
            )
        if has_engine:
            parts.append("engine=empty")
        if has_engine_group:
            parts.append("engineGroup=empty")
        return "AND[" + ", ".join(parts) + "]"

    # ------------------------------------------------------------------
    # Field discovery (walker helpers - structurally identical to CO141)
    # ------------------------------------------------------------------

    @staticmethod
    def _serializer_rename_map(handler: HandlerData) -> Dict[str, str]:
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

    def _iter_all_fields(
        self, connector: Connector, handler: HandlerData
    ) -> Iterator[Tuple[Dict[str, Any], str, str]]:
        for field, hint in self._iter_connection_yaml_fields(connector, handler):
            yield field, "connection.yaml", hint
        for field, hint in self._iter_capabilities_yaml_fields(connector):
            yield field, "capabilities.yaml", hint
        for field, hint in self._iter_configurations_yaml_fields(connector, handler):
            yield field, "configurations.yaml", hint

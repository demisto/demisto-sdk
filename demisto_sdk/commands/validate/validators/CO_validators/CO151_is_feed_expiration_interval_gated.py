"""CO151 - IsFeedExpirationIntervalGatedValidator.

Per the connector guide, the ``feedExpirationInterval`` field (a
duration-typed input on feed integrations) is meaningful only when
the sibling ``feedExpirationPolicy`` field selects the
interval-based option. If a handler emits
``feedExpirationInterval`` as a user-visible field,
``triggers.yaml`` MUST contain a trigger that hides the interval
field unless the policy field selects the interval option.

Field-id resolution
-------------------
Bare canonical pair: ``feedExpirationInterval`` /
``feedExpirationPolicy``. Grouped connectors may namespace both ids
(e.g. ``xsoar-misp-feed_feedExpirationInterval`` +
``xsoar-misp-feed_feedExpirationPolicy``).

Discovery:

1. Walk the connector's ``connection.yaml`` /
   ``capabilities.yaml`` / ``configurations.yaml`` raw YAML and
   collect every field whose **runtime name** (post-serializer
   rename) is ``feedExpirationInterval``. Record the **raw id**
   (pre-rename).
2. Derive the sibling raw id via suffix substitution:
   ``<X>feedExpirationInterval`` →
   ``<X>feedExpirationPolicy``. Confirm the policy field exists in
   the same connector — if not, emit a
   ``missing-policy-sibling`` finding.
3. Search ``triggers.yaml`` for a trigger whose effects target the
   raw interval id and whose conditions gate on the raw policy id
   with a value that selects the interval option. Accept the
   canonical ``operator: eq, value: interval`` with
   ``hidden: false`` OR the equivalent negated shape
   ``operator: neq, value: interval`` with ``hidden: true``.

Trigger value tolerance
-----------------------
Real-world content (see `abuse.ch/triggers.yaml`) uses
``value: "Time Interval"`` in place of the canonical
``value: interval``. Because ``feedExpirationPolicy`` is a select
whose UI display labels may vary, we accept **any value whose
lower-cased trimmed form contains "interval"** — this matches
``interval`` (canonical), ``Time Interval`` (real-world), and
``Interval`` variants without falsely matching unrelated options
like ``never``.

Skip conditions
---------------
- No ``feedExpirationInterval`` field found anywhere → skip
  (nothing to gate).
- ``triggers.yaml`` missing while a
  ``feedExpirationInterval`` field is present → hard fail.

Per-finding granularity
-----------------------
One ``ValidationResult`` per ``(raw_interval_field_id, defect)``:

- ``missing-policy-sibling`` — no matching policy field.
- ``missing-trigger`` — no trigger targets the interval field.
- ``wrong-condition`` — trigger exists but condition doesn't gate
  correctly on policy == interval.

Path routing: ``triggers.yaml`` for trigger-related defects,
``configurations.yaml`` for ``missing-policy-sibling``.

Non-XSOAR handlers are skipped — only XSOAR handler surfaces are
walked (mirrors CO141 / CO145 policy).
"""

from __future__ import annotations

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

CANONICAL_INTERVAL_RUNTIME_NAME = "feedExpirationInterval"
CANONICAL_POLICY_RUNTIME_NAME = "feedExpirationPolicy"
CANONICAL_INTERVAL_SUFFIX = "feedExpirationInterval"
CANONICAL_POLICY_SUFFIX = "feedExpirationPolicy"


class IsFeedExpirationIntervalGatedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO151"
    description = (
        "If `feedExpirationInterval` is emitted as a user-visible "
        "field, `triggers.yaml` must contain a trigger that hides "
        "it unless the sibling `feedExpirationPolicy` field selects "
        "the interval option. Discovery resolves runtime names via "
        "`serializer.yaml` `field_mappings` to handle grouped-"
        "connector namespaced ids."
    )
    rationale = (
        "`feedExpirationInterval` (a duration) is only meaningful "
        "when the feed expiration policy is set to the "
        "interval-based option; otherwise it's dead UI that "
        "confuses the user. The gating trigger makes the "
        "conditional-visibility invariant explicit in the manifest "
        "instead of relying on undocumented BE behavior."
    )
    error_message = (
        "Connector '{connector_id}': feedExpirationInterval field "
        "'{raw_interval_id}' must be gated by a trigger that hides "
        "it unless feedExpirationPolicy '{raw_policy_id}' selects "
        "the interval option (defect: {defect}). Expected a trigger "
        "with effects[].id='{raw_interval_id}' + action.hidden=false "
        "and conditions gating on id='{raw_policy_id}' with "
        "operator=eq, value=interval (or the equivalent "
        "operator=neq, hidden=true form)."
    )
    error_message_no_policy = (
        "Connector '{connector_id}': feedExpirationInterval field "
        "'{raw_interval_id}' has no matching feedExpirationPolicy "
        "sibling (expected raw id '{raw_policy_id}'). The interval "
        "field is meaningless without its policy sibling — add the "
        "policy field or remove the interval field."
    )
    related_field = "triggers"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.CONNECTOR_TRIGGERS,
        RelatedFileType.CONNECTOR_CONFIGURATIONS,
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
        """Walk every XSOAR handler, collect raw ids for
        ``feedExpirationInterval`` fields, then verify the sibling
        policy field and gating trigger for each."""
        # (raw_interval_id, raw_policy_id) pairs discovered across all
        # XSOAR handlers. Deduplicated because the same field id can
        # be walked via multiple handlers/files.
        pairs: Set[Tuple[str, str]] = set()
        # Track all raw field ids present anywhere (any runtime name)
        # so we can detect the missing-policy-sibling case without
        # walking again.
        all_raw_ids: Set[str] = set()

        for handler in connector.xsoar_handlers:
            rename_map = self._serializer_rename_map(handler)
            for field, _source_file, _hint in self._iter_all_fields(connector, handler):
                raw_id = field.get("id")
                if not isinstance(raw_id, str):
                    continue
                all_raw_ids.add(raw_id)
                runtime_name = rename_map.get(raw_id, raw_id)
                if runtime_name != CANONICAL_INTERVAL_RUNTIME_NAME:
                    continue
                # Derive sibling policy raw id from the interval raw id
                # by suffix substitution. Real examples:
                #   feedExpirationInterval               -> feedExpirationPolicy
                #   xsoar-misp-feed_feedExpirationInterval ->
                #     xsoar-misp-feed_feedExpirationPolicy
                if raw_id.endswith(CANONICAL_INTERVAL_SUFFIX):
                    prefix = raw_id[: -len(CANONICAL_INTERVAL_SUFFIX)]
                    raw_policy_id = prefix + CANONICAL_POLICY_SUFFIX
                else:
                    # Runtime name matched but raw id doesn't end with
                    # the canonical suffix — shouldn't normally happen
                    # (serializer only renames matching ids). Fall
                    # back to the canonical policy id so the finding
                    # is still emitted with meaningful text.
                    raw_policy_id = CANONICAL_POLICY_RUNTIME_NAME
                pairs.add((raw_id, raw_policy_id))

        if not pairs:
            return []

        # A single triggers.yaml walked once, effects indexed by
        # target id. Empty when the file is missing/unparsed.
        triggers_by_target = self._triggers_indexed_by_target(connector)
        triggers_yaml_present = isinstance(
            connector.triggers_file.file_content, (dict, list)
        )

        triggers_path = connector.triggers_file.file_path
        configurations_path = connector.configurations_file.file_path

        results: List[ValidationResult] = []
        for raw_interval_id, raw_policy_id in sorted(pairs):
            # missing-policy-sibling
            if raw_policy_id not in all_raw_ids:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message_no_policy.format(
                            connector_id=connector.object_id,
                            raw_interval_id=raw_interval_id,
                            raw_policy_id=raw_policy_id,
                        ),
                        content_object=connector,
                        path=configurations_path,
                    )
                )
                # Even if policy is missing we still want to signal
                # the gating gap when triggers.yaml is absent — but
                # emitting two findings for the same field is noisy;
                # policy-first is enough because the fix (add the
                # policy) is a prerequisite for the trigger anyway.
                continue

            # Missing triggers.yaml file while interval present -> hard
            # missing-trigger fail.
            if not triggers_yaml_present:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            raw_interval_id=raw_interval_id,
                            raw_policy_id=raw_policy_id,
                            defect="missing-trigger",
                        ),
                        content_object=connector,
                        path=triggers_path,
                    )
                )
                continue

            triggers = triggers_by_target.get(raw_interval_id, [])
            if not triggers:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            raw_interval_id=raw_interval_id,
                            raw_policy_id=raw_policy_id,
                            defect="missing-trigger",
                        ),
                        content_object=connector,
                        path=triggers_path,
                    )
                )
                continue

            # Any trigger whose conditions gate correctly wins.
            if any(
                self._trigger_gates_on_interval(trigger, raw_interval_id, raw_policy_id)
                for trigger in triggers
            ):
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        raw_interval_id=raw_interval_id,
                        raw_policy_id=raw_policy_id,
                        defect="wrong-condition",
                    ),
                    content_object=connector,
                    path=triggers_path,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Trigger analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _triggers_indexed_by_target(
        connector: Connector,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return ``{effect_target_id: [trigger_dicts]}`` from
        ``triggers.yaml``. A trigger with multiple effect ids is
        indexed once per id.
        """
        raw = connector.triggers_file.file_content
        # triggers.yaml may be a list at top level or a dict with a
        # ``triggers`` key — accept both shapes.
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

    @staticmethod
    def _matches_interval_value(value: Any) -> bool:
        """Case-insensitive substring match on 'interval' — accepts
        canonical ``interval`` and real-world ``Time Interval``."""
        return isinstance(value, str) and "interval" in value.strip().lower()

    def _trigger_gates_on_interval(
        self,
        trigger: Dict[str, Any],
        raw_interval_id: str,
        raw_policy_id: str,
    ) -> bool:
        """Return True iff the trigger effects target the interval
        field AND the conditions gate on the policy field with a
        value that resolves to the interval option.

        Accepts either:
        - ``operator: eq, value: <interval-ish>`` paired with an
          effect ``hidden: false`` on the interval id.
        - ``operator: neq, value: <interval-ish>`` paired with an
          effect ``hidden: true`` on the interval id.
        """
        effects = trigger.get("effects", [])
        if not isinstance(effects, list):
            return False

        # Locate our effect on the interval field, capture its hidden
        # flag. Any effect matching interval id counts.
        interval_hidden: Optional[bool] = None
        for effect in effects:
            if not isinstance(effect, dict):
                continue
            if effect.get("id") != raw_interval_id:
                continue
            action = effect.get("action")
            if isinstance(action, dict):
                hidden = action.get("hidden")
                if isinstance(hidden, bool):
                    interval_hidden = hidden
                    break

        if interval_hidden is None:
            return False

        conditions = trigger.get("conditions")
        # conditions may be a single dict (direct condition) or a dict
        # wrapping ``children`` (AND/OR grouping). CO151 only needs one
        # condition on the policy id — accept either shape.
        candidates = self._flatten_conditions(conditions)
        for cond in candidates:
            if cond.get("id") != raw_policy_id:
                continue
            operator = cond.get("operator")
            value = cond.get("value")
            if operator == "eq" and interval_hidden is False:
                if self._matches_interval_value(value):
                    return True
            if operator == "neq" and interval_hidden is True:
                if self._matches_interval_value(value):
                    return True
        return False

    @staticmethod
    def _flatten_conditions(conditions: Any) -> List[Dict[str, Any]]:
        """Yield the flat list of condition dicts embedded in a
        ``conditions`` block — accepts single dict, grouped
        ``{operator: AND/OR, children: [...]}`` or list."""
        out: List[Dict[str, Any]] = []
        if isinstance(conditions, dict):
            children = conditions.get("children")
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        out.append(child)
            elif "id" in conditions:
                out.append(conditions)
        elif isinstance(conditions, list):
            for entry in conditions:
                if isinstance(entry, dict):
                    out.append(entry)
        return out

    # ------------------------------------------------------------------
    # Field discovery (walkers structurally identical to CO141 - kept
    # duplicated per codebase policy, see CO141 lines 122-126.)
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

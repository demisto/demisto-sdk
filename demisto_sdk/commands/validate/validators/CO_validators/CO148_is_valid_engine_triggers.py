"""CO148 - triggers.yaml must contain the 3 canonical engine triggers
for every profile-set that emits engine fields.

For each raw ``<prefix>engine_mode`` field id present in the
connector's ``connection.yaml``, ``triggers.yaml`` MUST expose all
three triggers below (§3.7 engine triggers):

    1. Hide `<prefix>engine` when `<prefix>engine_mode != "engine"`
       - conditions: { id: <prefix>engine_mode, behavior: value,
                       operator: neq, value: engine }
       - effects:    [{ id: <prefix>engine, action: { hidden: true } }]

    2. Hide `<prefix>engineGroup` when
       `<prefix>engine_mode != "engineGroup"`
       - conditions: { id: <prefix>engine_mode, behavior: value,
                       operator: neq, value: engineGroup }
       - effects:    [{ id: <prefix>engineGroup, action: { hidden: true } }]

    3. Unlock `<prefix>proxy` (`read_only: false`) once EITHER
       `<prefix>engine` OR `<prefix>engineGroup` is non-empty. Static
       default keeps proxy read_only when engine_mode == no_engine.
       - conditions:
           operator: OR
           children:
             - { id: <prefix>engine,      behavior: value,
                 operator: is_not_empty }
             - { id: <prefix>engineGroup, behavior: value,
                 operator: is_not_empty }
       - effects: [{ id: <prefix>proxy, action: { read_only: false } }]

**Discovery of prefixes:** scan every raw field id in
``connection.yaml`` (profiles + general_configurations) matching
``(.*)engine_mode$``. Bare ``engine_mode`` → prefix ``""`` (standard
connector). Grouped-connector namespaced ids like
``plain_jira_v3_engine_mode`` → prefix ``"plain_jira_v3_"``. NOTE: The
serializer field-mappings are NOT used here — triggers.yaml uses the
same RAW ids as connection.yaml (not the canonical post-serializer
ids), so we match against raw ids directly.

**Skip cases:**
    - Connector emits no ``*engine_mode`` field anywhere (Appendix G
      integrations etc.) → skip. CO125/CO126 also skip these.
    - Connector has no ``connection.yaml`` → skip.

**Hard-fail cases:**
    - Missing ``triggers.yaml`` while at least one engine_mode prefix
      is declared.
    - Any of the 3 canonical triggers is missing/malformed for any
      declared prefix.

All findings aggregate into 1 ``ValidationResult`` per connector; path
pinned to ``triggers.yaml``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


# ============================================================
# Constants
# ============================================================
ENGINE_MODE_SUFFIX = "engine_mode"
ENGINE_SUFFIX = "engine"
ENGINE_GROUP_SUFFIX = "engineGroup"
PROXY_SUFFIX = "proxy"

VALUE_ENGINE = "engine"
VALUE_ENGINE_GROUP = "engineGroup"

BEHAVIOR_VALUE = "value"
OPERATOR_NEQ = "neq"
OPERATOR_OR = "OR"
OPERATOR_IS_NOT_EMPTY = "is_not_empty"


# ============================================================
# Discover engine_mode prefixes from connection.yaml
# ============================================================
def _iter_all_connection_field_ids(connector: Connector) -> Iterable[str]:
    """Yield every raw field id declared under ``connection.yaml``.

    Covers BOTH shapes:
      - Standard: ``connection.general_configurations.configurations[].fields[]``
      - Grouped:  ``connection.profiles[].configurations[].fields[]``

    Uses the Connector pydantic model (already parsed) so we get the
    raw ids as-written.
    """
    connection = connector.connection
    if connection is None:
        return
    gc = connection.general_configurations
    if gc is not None:
        for fg in gc.configurations or []:
            for f in fg.fields or []:
                if isinstance(f.id, str):
                    yield f.id
    for profile in connection.profiles or []:
        for fg in profile.configurations or []:
            for f in fg.fields or []:
                if isinstance(f.id, str):
                    yield f.id


def _engine_mode_prefixes(connector: Connector) -> Set[str]:
    """Return the set of raw ``<prefix>`` strings such that
    ``<prefix>engine_mode`` is a field id declared in connection.yaml.
    Bare ``engine_mode`` yields prefix ``""``.
    """
    prefixes: Set[str] = set()
    for fid in _iter_all_connection_field_ids(connector):
        if fid == ENGINE_MODE_SUFFIX:
            prefixes.add("")
        elif fid.endswith("_" + ENGINE_MODE_SUFFIX):
            # Strip the "engine_mode" suffix while keeping the trailing "_"
            # so the prefix concatenates cleanly.
            prefixes.add(fid[: -len(ENGINE_MODE_SUFFIX)])
    return prefixes


# ============================================================
# triggers.yaml parsing
# ============================================================
def _iter_triggers(connector: Connector) -> List[Dict[str, Any]]:
    """Return raw triggers.yaml `triggers[]` entries as dicts (empty
    list if the file is missing or the block is missing/mis-typed)."""
    triggers_file = connector.triggers_file
    if not triggers_file.exist:
        return []
    raw = triggers_file.file_content
    if not isinstance(raw, dict):
        return []
    items = raw.get("triggers")
    if not isinstance(items, list):
        return []
    return [t for t in items if isinstance(t, dict)]


def _has_triggers_file(connector: Connector) -> bool:
    return connector.triggers_file.exist


# ============================================================
# Trigger shape matchers
# ============================================================
def _first_effect(trigger: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    effects = trigger.get("effects")
    if isinstance(effects, list) and effects and isinstance(effects[0], dict):
        return effects[0]
    return None


def _effect_action(effect: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if effect is None:
        return {}
    action = effect.get("action")
    return action if isinstance(action, dict) else {}


def _matches_hide_when_mode_neq(
    trigger: Dict[str, Any],
    prefix: str,
    expected_mode_value: str,
    expected_effect_id: str,
) -> bool:
    """True iff trigger matches: hide `<prefix><suffix>` when
    `<prefix>engine_mode != <expected_mode_value>`."""
    conditions = trigger.get("conditions")
    if not isinstance(conditions, dict):
        return False
    if conditions.get("id") != f"{prefix}{ENGINE_MODE_SUFFIX}":
        return False
    if conditions.get("behavior") != BEHAVIOR_VALUE:
        return False
    if conditions.get("operator") != OPERATOR_NEQ:
        return False
    if conditions.get("value") != expected_mode_value:
        return False
    effect = _first_effect(trigger)
    if effect is None:
        return False
    if effect.get("id") != expected_effect_id:
        return False
    return _effect_action(effect).get("hidden") is True


def _matches_unlock_proxy(trigger: Dict[str, Any], prefix: str) -> bool:
    """True iff trigger matches: unlock `<prefix>proxy` (read_only:false)
    when `<prefix>engine` OR `<prefix>engineGroup` is non-empty."""
    conditions = trigger.get("conditions")
    if not isinstance(conditions, dict):
        return False
    if conditions.get("operator") != OPERATOR_OR:
        return False
    children = conditions.get("children")
    if not isinstance(children, list) or len(children) != 2:
        return False
    want_ids = {f"{prefix}{ENGINE_SUFFIX}", f"{prefix}{ENGINE_GROUP_SUFFIX}"}
    seen_ids: Set[str] = set()
    for child in children:
        if not isinstance(child, dict):
            return False
        if child.get("behavior") != BEHAVIOR_VALUE:
            return False
        if child.get("operator") != OPERATOR_IS_NOT_EMPTY:
            return False
        cid = child.get("id")
        if not isinstance(cid, str) or cid not in want_ids:
            return False
        seen_ids.add(cid)
    if seen_ids != want_ids:
        return False
    effect = _first_effect(trigger)
    if effect is None:
        return False
    if effect.get("id") != f"{prefix}{PROXY_SUFFIX}":
        return False
    return _effect_action(effect).get("read_only") is False


# ============================================================
# CO148 validator
# ============================================================
class IsValidEngineTriggersValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO148"
    description = (
        "Validates that for every `<prefix>engine_mode` field declared "
        "in `connection.yaml`, the `triggers.yaml` file contains the "
        "three canonical engine triggers: (1) hide `<prefix>engine` "
        "when `engine_mode != 'engine'`, (2) hide `<prefix>engineGroup` "
        "when `engine_mode != 'engineGroup'`, (3) unlock "
        "`<prefix>proxy` (read_only: false) when either engine or "
        "engineGroup is non-empty."
    )
    rationale = (
        "The engine picker (`engine_mode`, `engine`, `engineGroup`) is "
        "presented as a radio with three options, but the UI can only "
        "render one dropdown at a time. The three engine triggers "
        "enforce that behavior on the frontend — without them the user "
        "sees stale/irrelevant fields, and the proxy remains locked "
        "even after selecting an engine. In grouped connectors each "
        "profile has its own prefixed set of these fields, so each "
        "profile needs its own set of triggers."
    )
    error_message = (
        "Connector '{connector_id}': triggers.yaml engine-trigger "
        "wiring is incorrect: {issues}"
    )
    related_field = "triggers"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_TRIGGERS]

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
                    path=connector.triggers_file.file_path,
                )
            )
        return results

    def _check_connector(self, connector: Connector) -> List[str]:
        # Skip if connection.yaml is missing.
        if connector.connection is None:
            return []

        prefixes = _engine_mode_prefixes(connector)
        # Skip if no engine_mode fields at all (Appendix G etc.).
        if not prefixes:
            return []

        # Hard-fail if triggers.yaml is absent.
        if not _has_triggers_file(connector):
            return [
                f"triggers.yaml is missing but connection.yaml declares "
                f"{len(prefixes)} engine_mode field(s) "
                f"({sorted(prefixes)!r}); each set requires 3 canonical "
                f"engine triggers"
            ]

        triggers = _iter_triggers(connector)

        issues: List[str] = []
        for prefix in sorted(prefixes):
            label = f"prefix {prefix!r}" if prefix else "bare (standard)"
            found_hide_engine = any(
                _matches_hide_when_mode_neq(
                    t,
                    prefix=prefix,
                    expected_mode_value=VALUE_ENGINE,
                    expected_effect_id=f"{prefix}{ENGINE_SUFFIX}",
                )
                for t in triggers
            )
            if not found_hide_engine:
                issues.append(
                    f"{label}: missing 'hide engine when engine_mode != "
                    f"engine' trigger (expected conditions.id="
                    f"'{prefix}{ENGINE_MODE_SUFFIX}' with operator=neq "
                    f"value=engine, effect on id='{prefix}"
                    f"{ENGINE_SUFFIX}' action.hidden=true)"
                )

            found_hide_engine_group = any(
                _matches_hide_when_mode_neq(
                    t,
                    prefix=prefix,
                    expected_mode_value=VALUE_ENGINE_GROUP,
                    expected_effect_id=f"{prefix}{ENGINE_GROUP_SUFFIX}",
                )
                for t in triggers
            )
            if not found_hide_engine_group:
                issues.append(
                    f"{label}: missing 'hide engineGroup when engine_mode "
                    f"!= engineGroup' trigger (expected conditions.id="
                    f"'{prefix}{ENGINE_MODE_SUFFIX}' with operator=neq "
                    f"value=engineGroup, effect on id='{prefix}"
                    f"{ENGINE_GROUP_SUFFIX}' action.hidden=true)"
                )

            found_unlock_proxy = any(
                _matches_unlock_proxy(t, prefix=prefix) for t in triggers
            )
            if not found_unlock_proxy:
                issues.append(
                    f"{label}: missing 'unlock proxy when engine or "
                    f"engineGroup is selected' trigger (expected "
                    f"conditions.operator=OR with children "
                    f"'{prefix}{ENGINE_SUFFIX}' + '{prefix}"
                    f"{ENGINE_GROUP_SUFFIX}' both is_not_empty, effect "
                    f"on id='{prefix}{PROXY_SUFFIX}' "
                    f"action.read_only=false)"
                )

        return issues

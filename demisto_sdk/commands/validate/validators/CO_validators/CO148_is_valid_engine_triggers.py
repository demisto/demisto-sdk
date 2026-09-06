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

    3. Unlock the connector's proxy field (``read_only: false``) once
       EITHER ``<prefix>engine`` OR ``<prefix>engineGroup`` is
       non-empty. Static default keeps the proxy field read_only when
       ``engine_mode == no_engine``. The proxy field id may be any of
       the CO120 aliases — ``<prefix>proxy``, ``<prefix>useproxy``, or
       ``<prefix>use_proxy`` (whichever the connector actually declares
       as a raw field id).
       - conditions:
           operator: OR
           children:
             - { id: <prefix>engine,      behavior: value,
                 operator: is_not_empty }
             - { id: <prefix>engineGroup, behavior: value,
                 operator: is_not_empty }
       - effects: [{ id: <prefix>{proxy|useproxy|use_proxy},
                     action: { read_only: false } }]

       IMPORTANT: The unlock-proxy trigger (#3) is REQUIRED only when
       the connector actually declares a proxy field for the given
       prefix (in ``connection.yaml``, ``capabilities.yaml``, or any
       capability's ``configurations`` block). Not every integration
       exposes a proxy field — CO120 governs when a proxy field is
       required. Emitting a trigger whose ``effects[].id`` points at a
       non-existent field is a cross-file OPA violation. Therefore
       CO148 checks the unlock-proxy trigger only when it has evidence
       the proxy field exists for that prefix, and it validates the
       trigger targets a raw id from the CO120 alias set.

**Discovery is per-handler (profile-scoped):** the parser attaches to
every XSOAR handler a ``resolved_params`` list — the raw connector
field ids that specific handler actually consumes for its bound
profile / integration. Each ``ResolvedParamMapping`` carries both the
raw ``connector_param_name`` (as written in ``connection.yaml`` /
``capabilities.yaml`` / ``configurations.yaml``) and the runtime
``content_param_name`` (post-serializer). Because handlers are bound
to profiles via ``auth_options[].id``, each handler's
``resolved_params`` is already scoped to a single integration/profile,
so proxy fields consumed by handler A cannot leak into the engine
picker owned by handler B.

For every XSOAR handler H:

1. Discover all ``<prefix>engine_mode`` field ids H consumes — these
   are the engine-picker prefixes handler H is responsible for.
2. For each such prefix P, look for a matching
   ``<P>{proxy|useproxy|use_proxy}`` field id in H's own
   ``resolved_params``. If present, the unlock-proxy trigger for
   prefix P is REQUIRED. If absent, it MUST NOT be added (the Go OPA
   cross-file rule would reject an effect targeting a nonexistent
   field id).
3. Hide-engine and hide-engineGroup are ALWAYS required for every
   prefix that surfaces via any handler, since CO125/CO126 guarantee
   ``<P>engine`` / ``<P>engineGroup`` exist wherever
   ``<P>engine_mode`` does.

This per-handler scoping is critical for grouped connectors that
bundle multiple integrations under one connector. Example:
``cisco-security`` has a ``plain.amp`` profile that declares a bare
``engine_mode`` (targeting the AMP integration, which does not expose
a proxy field) AND a completely separate ``plain.ampv2`` profile that
declares a bare ``proxy`` (targeting the AMPv2 integration). The two
profiles use the same "" (bare) prefix but are wired to different
integrations, so a bare unlock-proxy trigger would target the wrong
integration and violate cross-file OPA. Handler-scoped discovery
prevents this false positive.

NOTE: The serializer field-mappings are NOT used to compare against
triggers.yaml — triggers.yaml uses the same RAW ids as connection.yaml
(not the canonical post-serializer ids). We only inspect the runtime
``content_param_name`` to detect that a field is a proxy alias, and
then use the raw ``connector_param_name`` for id matching.

**Skip cases:**
    - Connector emits no ``*engine_mode`` field anywhere (Appendix G
      integrations etc.) → skip. CO125/CO126 also skip these.
    - Connector has no ``connection.yaml`` → skip.
    - A given handler does not consume a proxy-alias field with the
      same prefix as one of its engine_mode fields → skip only the
      unlock-proxy check for that (handler, prefix) pair.

**Hard-fail cases:**
    - Missing ``triggers.yaml`` while at least one engine_mode prefix
      is declared by any XSOAR handler.
    - Either hide trigger is missing/malformed for any prefix
      consumed by any XSOAR handler.
    - The unlock-proxy trigger is missing/malformed for a (handler,
      prefix) pair where that handler exposes BOTH the engine_mode
      field and a proxy-alias field with the matching prefix.

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

# CO120 proxy aliases — MUST stay in sync with
# CO120_is_proxy_and_insecure_exists.PROXY_ALIASES.
PROXY_ALIASES: frozenset = frozenset({"proxy", "useproxy", "use_proxy"})

VALUE_ENGINE = "engine"
VALUE_ENGINE_GROUP = "engineGroup"

BEHAVIOR_VALUE = "value"
OPERATOR_NEQ = "neq"
OPERATOR_OR = "OR"
OPERATOR_IS_NOT_EMPTY = "is_not_empty"


# ============================================================
# Discover engine_mode prefixes and matching proxy ids from
# XSOAR handlers' resolved_params (profile-scoped).
# ============================================================
def _prefix_of_engine_mode_id(fid: str) -> Optional[str]:
    """If ``fid`` is a raw ``<prefix>engine_mode`` field id, return the
    ``<prefix>`` string (empty for bare ``engine_mode``). Otherwise
    return None.
    """
    if fid == ENGINE_MODE_SUFFIX:
        return ""
    if fid.endswith("_" + ENGINE_MODE_SUFFIX):
        # Strip the "engine_mode" suffix while keeping the trailing "_"
        # so the prefix concatenates cleanly.
        return fid[: -len(ENGINE_MODE_SUFFIX)]
    return None


def _handler_field_ids(handler: Any) -> Set[str]:
    """Return the set of raw connector field ids this handler consumes,
    filtered to strings only.
    """
    ids: Set[str] = set()
    for rp in handler.resolved_params or []:
        cid = rp.connector_param_name
        if isinstance(cid, str) and cid:
            ids.add(cid)
    return ids


def _handler_proxy_alias_ids(handler: Any) -> Set[str]:
    """Return the set of raw connector field ids this handler consumes
    whose runtime ``content_param_name`` is a CO120 proxy alias
    (``proxy`` / ``useproxy`` / ``use_proxy``).
    """
    ids: Set[str] = set()
    for rp in handler.resolved_params or []:
        cid = rp.connector_param_name
        if rp.content_param_name in PROXY_ALIASES and isinstance(cid, str) and cid:
            ids.add(cid)
    return ids


def _prefix_proxy_map(connector: Connector) -> Dict[str, Set[str]]:
    """Return a mapping ``prefix -> set of proxy-alias raw ids`` derived
    from XSOAR handler ``resolved_params``.

    For every XSOAR handler H and every ``<prefix>engine_mode`` field
    that H consumes, look at the proxy-alias raw ids H also consumes
    and keep only those whose id matches ``<prefix>{alias}`` for one of
    the CO120 aliases. This scopes proxy fields per-profile: a proxy
    field consumed by handler A cannot leak into the engine picker
    owned by handler B, even if both use the same prefix, because the
    two handlers correspond to different profiles/integrations.

    Prefixes that map to an empty set indicate the handler declares an
    engine picker but does not consume any matching proxy field for
    that prefix — the unlock-proxy trigger MUST NOT be required (and
    MUST NOT be added) for such prefixes.

    Prefixes that appear only via ``_engine_mode_prefixes_from_handlers``
    but not in this map at all also indicate "no matching proxy field
    for that prefix on any handler"; callers should treat missing keys
    as an empty set.
    """
    mapping: Dict[str, Set[str]] = {}
    for handler in connector.handlers or []:
        if not handler.is_xsoar:
            continue
        field_ids = _handler_field_ids(handler)
        proxy_ids = _handler_proxy_alias_ids(handler)
        # Find every engine_mode prefix this handler consumes.
        handler_prefixes: Set[str] = set()
        for fid in field_ids:
            prefix = _prefix_of_engine_mode_id(fid)
            if prefix is not None:
                handler_prefixes.add(prefix)
        # For each such prefix, collect proxy ids from THIS handler
        # that match the same prefix. Prefixes with no matching proxy
        # id on this handler still surface (with an empty set) so we
        # know the engine picker exists but the unlock-proxy trigger
        # is not required for this handler.
        for prefix in handler_prefixes:
            bucket = mapping.setdefault(prefix, set())
            for pid in proxy_ids:
                if any(pid == f"{prefix}{alias}" for alias in PROXY_ALIASES):
                    bucket.add(pid)
    return mapping


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


def _matches_unlock_proxy(
    trigger: Dict[str, Any],
    prefix: str,
    acceptable_proxy_ids: Set[str],
) -> bool:
    """True iff trigger matches: unlock a proxy field (read_only:false)
    when ``<prefix>engine`` OR ``<prefix>engineGroup`` is non-empty.

    ``acceptable_proxy_ids`` is the set of raw field ids the trigger's
    ``effects[0].id`` may target (i.e. the set of proxy-alias raw ids
    every XSOAR handler on the connector actually exposes). See
    :func:`_acceptable_proxy_trigger_ids`.
    """
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
    effect_id = effect.get("id")
    if not isinstance(effect_id, str) or effect_id not in acceptable_proxy_ids:
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
        # Skip if connection.yaml is missing (nothing to validate).
        if connector.connection is None:
            return []

        # Build prefix -> proxy-ids mapping from XSOAR handler
        # resolved_params. Prefixes only appear here if some XSOAR
        # handler actually consumes a matching engine_mode field, so
        # this naturally scopes the check to handler-visible pickers.
        prefix_to_proxy_ids = _prefix_proxy_map(connector)
        prefixes = set(prefix_to_proxy_ids.keys())

        # Skip if no XSOAR handler consumes any engine_mode field
        # (Appendix G integrations, non-XSOAR-only connectors, etc.).
        if not prefixes:
            return []

        # Hard-fail if triggers.yaml is absent.
        if not _has_triggers_file(connector):
            return [
                f"triggers.yaml is missing but XSOAR handlers consume "
                f"{len(prefixes)} engine_mode field(s) "
                f"({sorted(prefixes)!r}); each set requires the "
                f"canonical engine triggers"
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

            # Unlock-proxy is required only when at least one XSOAR
            # handler consumes BOTH the engine_mode field and a
            # matching proxy-alias field (i.e. same prefix, both from
            # the same profile/integration). If no matching proxy id
            # was collected for this prefix, the handler exposes no
            # proxy field for this profile and adding a trigger
            # targeting a non-existent field id would violate the Go
            # OPA cross-file rule.
            prefix_proxy_ids = prefix_to_proxy_ids.get(prefix) or set()
            if prefix_proxy_ids:
                found_unlock_proxy = any(
                    _matches_unlock_proxy(
                        t,
                        prefix=prefix,
                        acceptable_proxy_ids=prefix_proxy_ids,
                    )
                    for t in triggers
                )
                if not found_unlock_proxy:
                    issues.append(
                        f"{label}: missing 'unlock proxy when engine "
                        f"or engineGroup is selected' trigger "
                        f"(expected conditions.operator=OR with "
                        f"children '{prefix}{ENGINE_SUFFIX}' + "
                        f"'{prefix}{ENGINE_GROUP_SUFFIX}' both "
                        f"is_not_empty, effect on id in "
                        f"{sorted(prefix_proxy_ids)!r} "
                        f"action.read_only=false)"
                    )

        return issues

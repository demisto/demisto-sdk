"""CO149 - fetch capabilities on the same integration must be mutually
exclusive via triggers.yaml.

For any integration (handler) that contributes ≥2 fetch capabilities to
the connector, the ``triggers.yaml`` file MUST contain the
``n × (n-1)`` canonical mutual-exclusion triggers, one per ordered pair
``(<Fi>, <Fj>)`` where i ≠ j (§3.4 note 6, §3.5).

Each mutex trigger has the shape::

    conditions:
      id: <Fi>
      behavior: selected
      operator: eq
      value: true
    effects:
    - id: <Fj>
      action:
        read_only: true
      message: Select only one fetch option.

**How we discover fetch capabilities** (data-driven — no hard-coded
capability-id whitelist):

Each ``handler.serializer.computed_fields[]`` rule emits an XSOAR-side
computed flag (via ``output``) gated by capability/field conditions
(via ``any_of[].conditions[]``). We treat a rule as a "fetch rule"
when any ``output.id`` is one of the five fetch flags:

    - isFetch                (fetch-issues)
    - feed                   (threat-intelligence-and-enrichment)
    - isFetchEvents          (log-collection)
    - isFetchAssets          (fetch-assets-and-vulnerabilities)
    - isFetchCredentials     (fetch-secrets)

...and that flag's ``value`` is truthy (``True`` / ``"true"`` /
``"on"``). For every fetch rule on a handler we harvest the
capability ids from ``any_of[].conditions[]`` whose ``type ==
"capability"``. Those capability ids are the fetch (sub-)capabilities
bound to THIS integration.

**Integration grouping** — handler identity IS the integration. We
group fetch capability ids by ``handler.id``, so:

    - **Standard connectors** typically have one handler → all fetch
      capabilities share that one handler-key.
    - **Grouped connectors** have one handler per integration →
      each handler's fetch capabilities are naturally scoped.

**Skip cases**:
    - No handler emits ≥2 fetch capability ids → the connector needs
      no mutex triggers → pass.

**Hard-fail cases**:
    - Missing ``triggers.yaml`` while at least one integration
      requires mutex triggers.
    - Any of the ``n × (n-1)`` required mutex triggers is missing or
      malformed for any integration (wrong shape, wrong action, wrong
      message, missing/extra keys).

All findings aggregate into a single ``ValidationResult`` per
connector; path pinned to ``triggers.yaml``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    ComputedFieldRule,
    Connector,
    HandlerData,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


# ============================================================
# Constants
# ============================================================

# The five "fetch flag" ids the platform recognises as marking a
# capability as a fetch loop. Keyed by flag id → human-readable
# capability-family label (used for error messages only).
FETCH_FLAG_IDS: Set[str] = {
    "isFetch",
    "feed",
    "isFetchEvents",
    "isFetchAssets",
    "isFetchCredentials",
}

MUTEX_MESSAGE = "Select only one fetch option."

BEHAVIOR_SELECTED = "selected"
OPERATOR_EQ = "eq"
CAPABILITY_CONDITION_TYPE = "capability"


# ============================================================
# Serializer walking helpers
# ============================================================
def _is_fetch_flag_truthy(value: Any) -> bool:
    """A computed_fields `output.value` is considered "flag set"
    when it is truthy in the YAML-native sense. Serializer.yaml
    typically emits booleans (``True``), but we defensively accept
    the string forms ``"true"``/``"on"`` (case-insensitive) too."""
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in ("true", "on"):
        return True
    return False


def _rule_emits_fetch_flag(rule: ComputedFieldRule) -> bool:
    """True iff ``rule.output`` contains at least one entry whose
    ``id`` is a known fetch flag AND whose ``value`` is truthy."""
    for out in rule.output or []:
        if out.id in FETCH_FLAG_IDS and _is_fetch_flag_truthy(out.value):
            return True
    return False


def _rule_gating_capability_ids(rule: ComputedFieldRule) -> Set[str]:
    """Collect every capability id referenced by this rule's
    ``any_of[].conditions[]`` (``type == "capability"``). These are
    the capabilities that gate the fetch flag on this handler.

    We deliberately ignore ``value`` on the capability condition — the
    rule structure itself is what CO130/CO132/CO133/CO134 enforces.
    CO149 only cares WHICH capability ids are wired to a fetch flag.
    """
    ids: Set[str] = set()
    for group in rule.any_of or []:
        for cond in group.conditions or []:
            if cond.type != CAPABILITY_CONDITION_TYPE:
                continue
            opts = cond.options or {}
            cap_id = opts.get("capability_id")
            if isinstance(cap_id, str) and cap_id:
                ids.add(cap_id)
    return ids


def _handler_fetch_capability_ids(handler: HandlerData) -> Set[str]:
    """Union of gating-capability ids across every fetch-emitting
    rule on this handler's serializer."""
    serializer = handler.serializer
    if serializer is None:
        return set()
    ids: Set[str] = set()
    for rule in serializer.computed_fields or []:
        if not _rule_emits_fetch_flag(rule):
            continue
        ids.update(_rule_gating_capability_ids(rule))
    return ids


def _group_fetch_caps_by_handler(
    connector: Connector,
) -> Dict[str, List[str]]:
    """Return ``{handler_id: [fetch_capability_id, ...]}`` covering
    every handler on the connector whose serializer wires any fetch
    flag to at least one capability. Result is deterministically
    sorted per key. Callers filter to buckets with ≥2 entries."""
    buckets: Dict[str, Set[str]] = {}
    for handler in connector.handlers or []:
        cap_ids = _handler_fetch_capability_ids(handler)
        if not cap_ids:
            continue
        buckets[handler.id] = cap_ids
    return {handler_id: sorted(ids) for handler_id, ids in buckets.items()}


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


# ============================================================
# Trigger shape matcher
# ============================================================
def _first_effect(trigger: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    effects = trigger.get("effects")
    if isinstance(effects, list) and effects and isinstance(effects[0], dict):
        return effects[0]
    return None


def _matches_mutex_trigger(
    trigger: Dict[str, Any],
    condition_id: str,
    effect_id: str,
) -> bool:
    """True iff ``trigger`` is exactly the canonical mutex trigger:
    ``condition_id`` selected → lock ``effect_id`` with
    ``{read_only: true}`` and message
    ``"Select only one fetch option."``.

    Strict shape:
      - conditions: {id, behavior: selected, operator: eq, value: true}
      - single-effect list with:
          id == effect_id
          action == exactly {read_only: True}
          message == "Select only one fetch option."
    """
    conditions = trigger.get("conditions")
    if not isinstance(conditions, dict):
        return False
    if conditions.get("id") != condition_id:
        return False
    if conditions.get("behavior") != BEHAVIOR_SELECTED:
        return False
    if conditions.get("operator") != OPERATOR_EQ:
        return False
    if conditions.get("value") is not True:
        return False

    effect = _first_effect(trigger)
    if effect is None:
        return False
    if effect.get("id") != effect_id:
        return False
    if effect.get("message") != MUTEX_MESSAGE:
        return False
    action = effect.get("action")
    if not isinstance(action, dict):
        return False
    # Strict action shape: exactly {read_only: True}.
    if set(action.keys()) != {"read_only"} or action.get("read_only") is not True:
        return False
    return True


# ============================================================
# CO149 validator
# ============================================================
class IsFetchMutexTriggersValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO149"
    description = (
        "For every integration (handler) that contributes 2 or more "
        "fetch capabilities — discovered by walking each handler's "
        "serializer.yaml `computed_fields` for the 5 canonical fetch "
        "flag ids (`isFetch`, `feed`, `isFetchEvents`, `isFetchAssets`, "
        "`isFetchCredentials`) — `triggers.yaml` must contain the "
        "`n × (n-1)` canonical mutex triggers, one per ordered "
        "capability pair `(Fi, Fj)`."
    )
    rationale = (
        "Each fetch capability configures its own polling loop and "
        "consumes provider quota. The platform allows only one fetch "
        "loop per integration instance at a time, so the UI must "
        "prevent users from selecting two fetch capabilities on the "
        "same integration. The mutex triggers deliver that guardrail. "
        "Discovery is data-driven from serializer computed_fields — "
        "the same signal the runtime uses to decide which fetch flag "
        "to emit — so this validator stays correct as new fetch "
        "capability families are introduced."
    )
    error_message = "{connector_id}: {details}"
    fix_message = ""
    related_field = "triggers"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[Connector],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for connector in content_items:
            issues = self._check_connector(connector)
            if not issues:
                continue
            triggers_path = connector.triggers_file.file_path
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        details="; ".join(issues),
                    ),
                    content_object=connector,
                    path=triggers_path,
                )
            )
        return results

    def _check_connector(self, connector: Connector) -> List[str]:
        """Return the list of human-readable issue strings for this
        connector (empty list = pass)."""
        handler_map = _group_fetch_caps_by_handler(connector)
        # Only handlers with ≥2 fetch capabilities require triggers.
        multi_fetch = {hid: caps for hid, caps in handler_map.items() if len(caps) >= 2}
        if not multi_fetch:
            return []

        # Hard-fail once if triggers.yaml is missing outright, rather
        # than emitting an error per missing trigger.
        if not connector.triggers_file.exist:
            handler_ids = sorted(multi_fetch.keys())
            return [
                "triggers.yaml is missing but the following handler(s) "
                f"require fetch mutex triggers: {handler_ids}"
            ]

        triggers = _iter_triggers(connector)
        issues: List[str] = []
        for handler_id in sorted(multi_fetch.keys()):
            fetch_caps = multi_fetch[handler_id]
            for i, cond_id in enumerate(fetch_caps):
                for j, effect_id in enumerate(fetch_caps):
                    if i == j:
                        continue
                    if not any(
                        _matches_mutex_trigger(t, cond_id, effect_id) for t in triggers
                    ):
                        issues.append(
                            f"handler '{handler_id}': missing canonical mutex "
                            f"trigger '{cond_id}' → lock '{effect_id}' "
                            f"(read_only: true, message: '{MUTEX_MESSAGE}')"
                        )
        return issues

"""CO150 - a selected fetch capability must auto-enable and lock the
handler's ``automation-and-remediation`` sub-capability via a single
canonical trigger.

For each handler whose ``serializer.computed_fields`` emits one or
more of the 5 fetch flags (see CO149), ``triggers.yaml`` MUST expose
ONE canonical auto-enable trigger with the shape::

    conditions:
      operator: OR
      children:
        - id: <fetch_cap_id_1>
          behavior: selected
          operator: eq
          value: true
        - id: <fetch_cap_id_2>
          behavior: selected
          operator: eq
          value: true
        ... (one child per fetch cap on this handler)
    effects:
      - id: <automation_cap_id>
        action:
          read_only: true
          enabled: true
        message: A selected capability enables this setting. Clear the active dependency to disable it

**Discovery** (data-driven, matches CO149):
    - Walk ``handler.serializer.computed_fields`` for the 5 fetch flag
      ids (``isFetch``, ``feed``, ``isFetchEvents``, ``isFetchAssets``,
      ``isFetchCredentials``) with a truthy value; harvest gating
      ``capability_id`` from ``any_of[].conditions[type=="capability"]``.
    - Derive the automation cap id by SUFFIX-substitution:
        - bare ``fetch-issues`` → ``automation-and-remediation``
        - namespaced ``fetch-issues_akamai-waf-siem`` →
          ``automation-and-remediation_akamai-waf-siem``
      All fetch caps on a handler MUST share the same suffix so they
      map to the same automation cap.

**Skip cases**:
    - Handler emits no fetch caps → skip.
    - Handler has fetch caps but doesn't declare the corresponding
      ``automation-and-remediation`` sub-capability (per
      ``connector.capabilities``) → skip (nothing to lock).

**Hard-fail cases**:
    - Missing ``triggers.yaml`` while at least one handler needs an
      auto-enable trigger.
    - The canonical auto-enable trigger is missing OR malformed for a
      handler that requires it. Strict shape:
        * conditions: dict with ``operator == "OR"`` and
          ``children`` = list of dicts, one per fetch cap of THIS
          handler, matching ``{id, behavior: selected, operator: eq,
          value: true}`` (extra children fail; missing children fail).
        * effects: single-entry list with
          ``id == <automation_cap_id>``,
          ``action == {read_only: true, enabled: true}`` (exact keys),
          ``message == <canonical>``.

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

# Same fetch flags CO149 recognises. Kept in sync manually.
FETCH_FLAG_IDS: Set[str] = {
    "isFetch",
    "feed",
    "isFetchEvents",
    "isFetchAssets",
    "isFetchCredentials",
}

# Fetch capability base ids we recognise for suffix splitting. Same
# 5-tuple used by the platform; ordering matters only for prefix
# matching (longest first would matter if any base was a prefix of
# another — none of these are).
FETCH_BASE_IDS = (
    "fetch-issues",
    "threat-intelligence-and-enrichment",
    "log-collection",
    "fetch-assets-and-vulnerabilities",
    "fetch-secrets",
)

AUTOMATION_BASE_ID = "automation-and-remediation"

AUTO_ENABLE_MESSAGE = (
    "A selected capability enables this setting. "
    "Clear the active dependency to disable it"
)

BEHAVIOR_SELECTED = "selected"
OPERATOR_EQ = "eq"
OPERATOR_OR = "OR"
CAPABILITY_CONDITION_TYPE = "capability"


# ============================================================
# Serializer walking helpers
# ============================================================
def _is_fetch_flag_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in ("true", "on"):
        return True
    return False


def _rule_emits_fetch_flag(rule: ComputedFieldRule) -> bool:
    for out in rule.output or []:
        if out.id in FETCH_FLAG_IDS and _is_fetch_flag_truthy(out.value):
            return True
    return False


def _rule_gating_capability_ids(rule: ComputedFieldRule) -> Set[str]:
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
    serializer = handler.serializer
    if serializer is None:
        return set()
    ids: Set[str] = set()
    for rule in serializer.computed_fields or []:
        if not _rule_emits_fetch_flag(rule):
            continue
        ids.update(_rule_gating_capability_ids(rule))
    return ids


# ============================================================
# Suffix / automation-cap derivation
# ============================================================
def _fetch_cap_suffix(cap_id: str) -> Optional[str]:
    """Return the ``<suffix>`` portion (leading ``_`` stripped) of a
    fetch cap id, or ``""`` for a bare fetch id, or ``None`` if
    ``cap_id`` is not a known fetch cap.

    Examples:
      - ``fetch-issues``                             → ``""``
      - ``fetch-issues_akamai-waf-siem``             → ``"akamai-waf-siem"``
      - ``fetch-assets-and-vulnerabilities_qualys``  → ``"qualys"``
      - ``random-cap``                               → ``None``
    """
    if not isinstance(cap_id, str):
        return None
    for base in FETCH_BASE_IDS:
        if cap_id == base:
            return ""
        prefix = f"{base}_"
        if cap_id.startswith(prefix):
            return cap_id[len(prefix) :]
    return None


def _automation_cap_for_suffix(suffix: str) -> str:
    """Compose the automation-and-remediation cap id for a given
    suffix (``""`` = standard connector; non-empty = grouped)."""
    if suffix == "":
        return AUTOMATION_BASE_ID
    return f"{AUTOMATION_BASE_ID}_{suffix}"


def _connector_capability_ids(connector: Connector) -> Set[str]:
    """Union of every capability id declared in
    ``connector.capabilities`` (top-level ids only — sub-capability
    ids are already namespaced at the top level for grouped
    connectors per §3.7).
    """
    ids: Set[str] = set()
    for cap in connector.capabilities or []:
        cap_id = getattr(cap, "id", None)
        if isinstance(cap_id, str):
            ids.add(cap_id)
    return ids


# ============================================================
# Handler requirement extraction
# ============================================================
def _handler_requirement(
    handler: HandlerData,
    connector_cap_ids: Set[str],
) -> Optional[Dict[str, Any]]:
    """Return a dict describing what this handler REQUIRES from
    triggers.yaml, or ``None`` when the handler has nothing to
    enforce.

    Shape:
        {
            "fetch_cap_ids": sorted[str, ...],   # non-empty
            "automation_cap_id": str,
            "suffix": str,
        }

    Skip conditions:
      - No fetch caps discovered on this handler.
      - Fetch caps disagree on suffix (defensive; shouldn't happen for
        well-formed connectors) → skipped so we don't emit a confusing
        cross-integration trigger.
      - The derived automation cap id is not declared in
        ``connector.capabilities`` → skip (nothing to lock).
    """
    fetch_cap_ids = _handler_fetch_capability_ids(handler)
    if not fetch_cap_ids:
        return None

    suffixes = {_fetch_cap_suffix(cid) for cid in fetch_cap_ids}
    # Drop the None sentinel; if any fetch cap couldn't be parsed we
    # still can't safely derive one automation id.
    if None in suffixes or len(suffixes) != 1:
        return None
    (suffix,) = suffixes  # type: ignore[misc]
    assert isinstance(suffix, str)  # for type-checkers

    automation_cap_id = _automation_cap_for_suffix(suffix)
    if automation_cap_id not in connector_cap_ids:
        return None

    return {
        "fetch_cap_ids": sorted(fetch_cap_ids),
        "automation_cap_id": automation_cap_id,
        "suffix": suffix,
    }


# ============================================================
# triggers.yaml parsing + shape matcher
# ============================================================
def _iter_triggers(connector: Connector) -> List[Dict[str, Any]]:
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


def _first_effect(trigger: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    effects = trigger.get("effects")
    if isinstance(effects, list) and effects and isinstance(effects[0], dict):
        return effects[0]
    return None


def _matches_auto_enable_trigger(
    trigger: Dict[str, Any],
    fetch_cap_ids: List[str],
    automation_cap_id: str,
) -> bool:
    """True iff the trigger is exactly the canonical auto-enable
    trigger for THIS handler.

    Strict shape requirements:
      - conditions: dict with operator == "OR" and a ``children``
        list whose ids EQUAL ``fetch_cap_ids`` (as a set). Each child
        must be exactly {id, behavior: selected, operator: eq,
        value: true}.
      - effects: single-effect list with:
          id == automation_cap_id
          action == exactly {read_only: True, enabled: True}
          message == AUTO_ENABLE_MESSAGE
    """
    conditions = trigger.get("conditions")
    if not isinstance(conditions, dict):
        return False
    if conditions.get("operator") != OPERATOR_OR:
        return False
    children = conditions.get("children")
    if not isinstance(children, list) or len(children) != len(fetch_cap_ids):
        return False

    want_ids = set(fetch_cap_ids)
    seen_ids: Set[str] = set()
    for child in children:
        if not isinstance(child, dict):
            return False
        cid = child.get("id")
        if not isinstance(cid, str) or cid not in want_ids:
            return False
        if child.get("behavior") != BEHAVIOR_SELECTED:
            return False
        if child.get("operator") != OPERATOR_EQ:
            return False
        if child.get("value") is not True:
            return False
        seen_ids.add(cid)
    if seen_ids != want_ids:
        return False

    effect = _first_effect(trigger)
    if effect is None:
        return False
    if effect.get("id") != automation_cap_id:
        return False
    if effect.get("message") != AUTO_ENABLE_MESSAGE:
        return False
    action = effect.get("action")
    if not isinstance(action, dict):
        return False
    if set(action.keys()) != {"read_only", "enabled"}:
        return False
    if action.get("read_only") is not True or action.get("enabled") is not True:
        return False
    return True


# ============================================================
# CO150 validator
# ============================================================
class IsCollectionAutoEnablesAutomationValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO150"
    description = (
        "For each handler whose serializer.yaml emits a fetch flag "
        "(one of `isFetch`, `feed`, `isFetchEvents`, `isFetchAssets`, "
        "`isFetchCredentials`), `triggers.yaml` must contain the "
        "canonical auto-enable trigger: OR across all the handler's "
        "fetch cap ids → lock the handler's "
        "`automation-and-remediation` sub-capability with "
        "`{read_only: true, enabled: true}` and the canonical message."
    )
    rationale = (
        "Every fetch loop needs a companion automation-and-remediation "
        "sub-capability to actually run response actions. Manually "
        "flipping the automation switch after enabling a fetch is "
        "error-prone, so the platform binds them via a trigger that "
        "auto-enables and locks the automation cap while ANY fetch cap "
        "is selected. Discovery is data-driven from serializer "
        "computed_fields (same as CO149) — this stays correct as new "
        "fetch capability families are added."
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
        connector_cap_ids = _connector_capability_ids(connector)
        requirements = []
        for handler in connector.handlers or []:
            req = _handler_requirement(handler, connector_cap_ids)
            if req is None:
                continue
            requirements.append((handler.id, req))

        if not requirements:
            return []

        if not connector.triggers_file.exist:
            handler_ids = sorted(hid for hid, _ in requirements)
            return [
                "triggers.yaml is missing but the following handler(s) "
                f"require an auto-enable trigger: {handler_ids}"
            ]

        triggers = _iter_triggers(connector)
        issues: List[str] = []
        for handler_id, req in sorted(requirements, key=lambda x: x[0]):
            fetch_cap_ids = req["fetch_cap_ids"]
            automation_cap_id = req["automation_cap_id"]
            if not any(
                _matches_auto_enable_trigger(t, fetch_cap_ids, automation_cap_id)
                for t in triggers
            ):
                issues.append(
                    f"handler '{handler_id}': missing canonical auto-enable "
                    f"trigger — OR({fetch_cap_ids}) selected → lock "
                    f"'{automation_cap_id}' "
                    f"(action: {{read_only: true, enabled: true}}, "
                    f"message: '{AUTO_ENABLE_MESSAGE}')"
                )
        return issues

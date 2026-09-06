"""CO172 - reverse direction: every fetch-flag emission in the serializer
must be gated on a sub-capability THIS handler subscribes to, AND that
sub-capability's base id must map to that flag per the canonical
mapping.

For each XSOAR handler's ``serializer.yaml`` ``computed_fields`` rules,
if a rule emits one of the 5 fetch flags with a truthy value, then at
least one of its ``type: capability`` conditions MUST target a
``capability_id`` such that:

  (a) ``capability_id`` appears in ``handler.capabilities[].id``
      (this handler actually subscribes to that sub-capability), AND
  (b) ``_capability_base_id(capability_id)`` maps to the emitted
      flag id per ``FLAG_BY_CAP_BASE``.

Subsumes the negative rule from the retired CO173 for free: since
``automation-and-remediation`` is not in ``FLAG_BY_CAP_BASE``, any fetch
flag gated on an automation cap fails clause (b).

Skip cases:
    - Non-xsoar handler.
    - Handler has no serializer, or serializer emits no fetch flags.
Hard-fail cases:
    - A fetch-flag rule has no capability gate at all.
    - A fetch-flag rule is gated on a cap this handler doesn't subscribe
      to.
    - A fetch-flag rule is gated on a cap whose base id doesn't map to
      the emitted flag.

Per-handler aggregated result; path points at the offending
``serializer.yaml``.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    ComputedFieldRule,
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

FLAG_BY_CAP_BASE: Dict[str, str] = {
    "fetch-issues": "isFetch",
    "log-collection": "isFetchEvents",
    "fetch-assets-and-vulnerabilities": "isFetchAssets",
    "fetch-secrets": "isFetchCredentials",
    "threat-intelligence-and-enrichment": "feed",
}
FETCH_FLAG_IDS: Set[str] = set(FLAG_BY_CAP_BASE.values())

CAPABILITY_CONDITION_TYPE = "capability"
TRUTHY_VALUES = {True, "true", "on"}


def _capability_base_id(cap_id: str) -> str:
    return cap_id.split("_", 1)[0] if cap_id else ""


def _rule_emitted_fetch_flag(rule: ComputedFieldRule) -> Optional[str]:
    """If ``rule`` outputs one of the 5 fetch flags with a truthy value,
    return that flag id; otherwise ``None``. Non-fetch outputs are ignored.
    """
    for out in rule.output or []:
        if out and out.id in FETCH_FLAG_IDS and out.value in TRUTHY_VALUES:
            return out.id
    return None


def _capability_gates(rule: ComputedFieldRule) -> List[str]:
    """Return every ``capability_id`` referenced by a ``type: capability``
    condition on ``rule`` (may be empty)."""
    ids: List[str] = []
    for group in rule.any_of or []:
        for cond in group.conditions or []:
            if not cond or cond.type != CAPABILITY_CONDITION_TYPE:
                continue
            options = cond.options or {}
            cap_id = options.get("capability_id")
            if isinstance(cap_id, str) and cap_id:
                ids.append(cap_id)
    return ids


class IsFetchFlagGatedOnOwnSubCapabilityValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO172"
    description = (
        "Every fetch-flag emission (isFetch, isFetchEvents, isFetchAssets, "
        "isFetchCredentials, feed) in an XSOAR handler's serializer.yaml "
        "must be gated on a `type: capability` condition targeting a "
        "sub-capability THIS handler subscribes to, AND whose base id maps "
        "to that emitted flag per the canonical mapping. Subsumes the "
        "retired CO173 (automation-and-remediation must never emit a fetch "
        "flag), since automation-and-remediation is not in the mapping."
    )
    rationale = (
        "A fetch flag turns on the corresponding fetch loop at runtime. If "
        "the flag is gated on a capability this handler doesn't subscribe "
        "to, or on the wrong capability family, the flag either fires when "
        "it shouldn't or fails to gate correctly. This check is the reverse "
        "direction of CO171 and closes the loop between serializer output "
        "and handler capability subscription."
    )
    error_message = (
        "Handler '{handler_id}' has invalid fetch-flag gating in "
        "serializer.yaml: {problems}."
    )
    related_field = "serializer.computed_fields"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Reverse-direction check per XSOAR handler.

        Aggregates all reverse-direction problems on the same handler into
        one result; path points at the handler's serializer.yaml.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.xsoar_handlers:
                problems = self._check_handler(handler)
                if not problems:
                    continue

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            handler_id=handler.id,
                            problems="; ".join(problems),
                        ),
                        content_object=connector,
                        path=self._serializer_path(handler),
                    )
                )

        return results

    @staticmethod
    def _check_handler(handler: HandlerData) -> List[str]:
        """Return per-problem strings for `handler`. Empty list = pass."""
        if handler.serializer is None:
            return []  # nothing to check; CO171 flags the missing file

        rules = handler.serializer.computed_fields or []
        subscribed_cap_ids: Set[str] = {
            cap.id for cap in (handler.capabilities or []) if cap and cap.id
        }

        problems: List[str] = []
        for rule in rules:
            flag_id = _rule_emitted_fetch_flag(rule)
            if flag_id is None:
                continue  # non-fetch rule; not our concern

            expected_base = None
            for base, flag in FLAG_BY_CAP_BASE.items():
                if flag == flag_id:
                    expected_base = base
                    break

            gates = _capability_gates(rule)
            if not gates:
                problems.append(
                    f"rule emitting '{flag_id}' has no `type: capability` gate"
                )
                continue

            # A rule is valid iff AT LEAST ONE of its capability gates:
            #   - is subscribed by this handler, AND
            #   - has a base id matching the flag's expected family.
            if any(
                gate in subscribed_cap_ids
                and _capability_base_id(gate) == expected_base
                for gate in gates
            ):
                continue

            # Build the most useful message we can.
            bad_gates = sorted(set(gates))
            problems.append(
                f"rule emitting '{flag_id}' gated on {bad_gates!r} - "
                f"none are both subscribed by this handler "
                f"AND of family '{expected_base}'"
            )

        return problems

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[object]:
        """Best-effort path to the handler's ``serializer.yaml``."""
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"

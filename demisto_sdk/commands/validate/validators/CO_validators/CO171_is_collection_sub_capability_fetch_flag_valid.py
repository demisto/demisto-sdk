"""CO171 - forward direction: every subscribed collection sub-capability
must have a matching fetch-flag emission in the handler's serializer.

For each XSOAR handler, for every capability it subscribes to whose base
id is one of the 5 collection sub-capabilities, the handler's
``serializer.yaml`` MUST contain a ``computed_fields`` rule that:

  (a) exists (serializer + computed_fields present),
  (b) emits the correctly-mapped flag id per ``FLAG_BY_CAP_BASE`` with
      a truthy value (``True`` / ``"true"`` / ``"on"``),
  (c) gated on a ``type: capability`` condition whose
      ``options.capability_id`` matches THIS subscribed capability id
      exactly AND whose ``options.value == "on"``.

CO172 handles the reverse direction (a flag emitted must point at a
sub-capability this handler actually subscribes to per the mapping).

Skip cases:
    - Non-xsoar handler.
    - Handler subscribes to no collection sub-capability.
Hard-fail cases:
    - Missing serializer.
    - No matching computed_fields rule for a subscribed collection cap.

Per-handler aggregated result; path points at the offending
``serializer.yaml`` (or the handler.yaml when the serializer file is
absent).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

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

# Base collection sub-capability -> the fetch flag it must emit.
FLAG_BY_CAP_BASE: Dict[str, str] = {
    "fetch-issues": "isFetch",
    "log-collection": "isFetchEvents",
    "fetch-assets-and-vulnerabilities": "isFetchAssets",
    "fetch-secrets": "isFetchCredentials",
    "threat-intelligence-and-enrichment": "feed",
}

CAPABILITY_CONDITION_TYPE = "capability"
EXPECTED_CONDITION_VALUE = "on"
TRUTHY_VALUES = {True, "true", "on"}


def _capability_base_id(cap_id: str) -> str:
    """Strip the group suffix off a namespaced capability id
    (e.g. ``fetch-issues_akamai-waf-siem`` -> ``fetch-issues``)."""
    return cap_id.split("_", 1)[0] if cap_id else ""


def _rule_emits_flag_for(
    rule: ComputedFieldRule,
    flag_id: str,
    capability_id: str,
) -> bool:
    """True iff ``rule`` outputs ``flag_id`` truthy AND is gated on a
    ``type: capability`` condition with ``capability_id == capability_id``
    and ``value == "on"``.
    """
    emits_flag = any(
        out and out.id == flag_id and out.value in TRUTHY_VALUES
        for out in (rule.output or [])
    )
    if not emits_flag:
        return False

    for group in rule.any_of or []:
        for cond in group.conditions or []:
            if not cond or cond.type != CAPABILITY_CONDITION_TYPE:
                continue
            options = cond.options or {}
            if (
                options.get("capability_id") == capability_id
                and options.get("value") == EXPECTED_CONDITION_VALUE
            ):
                return True
    return False


class IsCollectionSubCapabilityFetchFlagValidValidator(
    ConnectorsValidator[ContentTypes]
):
    error_code = "CO171"
    description = (
        "For every collection sub-capability an XSOAR handler subscribes to "
        "(fetch-issues, log-collection, fetch-assets-and-vulnerabilities, "
        "fetch-secrets, threat-intelligence-and-enrichment), the handler's "
        "serializer.yaml must contain a computed_fields rule emitting the "
        "correctly-mapped flag (isFetch, isFetchEvents, isFetchAssets, "
        "isFetchCredentials, feed respectively) with a truthy value, gated "
        "on a `type: capability` condition targeting the same subscribed "
        "capability id with `value: on`."
    )
    rationale = (
        "The platform decides at runtime which fetch loop to activate based "
        "on serializer-emitted flags. If a handler subscribes to a "
        "collection capability but the serializer never emits the matching "
        "flag, the fetch loop will never start. The gating condition "
        "guarantees the flag is only true when the user actually enables "
        "the sub-capability."
    )
    error_message = (
        "Handler '{handler_id}' has broken collection fetch-flag wiring: " "{problems}."
    )
    related_field = "serializer.computed_fields"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Forward-direction check per XSOAR handler.

        Aggregates all forward-direction problems on the same handler into
        one result; path points at the handler's serializer.yaml (or the
        handler.yaml when the serializer file is absent).
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
        subscribed_collection_caps: List[str] = [
            cap.id
            for cap in (handler.capabilities or [])
            if cap and cap.id and _capability_base_id(cap.id) in FLAG_BY_CAP_BASE
        ]

        if not subscribed_collection_caps:
            return []  # nothing to enforce

        # Missing serializer while subscribed to a collection cap: single
        # fatal problem — no point per-cap-ing it.
        if handler.serializer is None:
            return [
                "serializer.yaml is missing but handler subscribes to "
                f"collection capabilities: {sorted(subscribed_collection_caps)}"
            ]

        rules = handler.serializer.computed_fields or []

        problems: List[str] = []
        for cap_id in subscribed_collection_caps:
            flag_id = FLAG_BY_CAP_BASE[_capability_base_id(cap_id)]
            if not any(_rule_emits_flag_for(r, flag_id, cap_id) for r in rules):
                problems.append(
                    f"subscribed capability '{cap_id}' has no computed_fields "
                    f"rule emitting '{flag_id}: true' gated on "
                    f"capability_id={cap_id!r} value='on'"
                )
        return problems

    @staticmethod
    def _serializer_path(handler: HandlerData) -> Optional[object]:
        """Best-effort path to the handler's ``serializer.yaml``.

        Falls back to the handler.yaml path when only the handler root is
        known; ``None`` when even that is unresolvable.
        """
        handler_yaml = handler.file_path
        if handler_yaml is None:
            return None
        return handler_yaml.parent / "serializer.yaml"

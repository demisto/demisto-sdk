"""CO144 - grouped-only. Config params (per-capability configurations
in ``configurations.yaml`` top-level ``configurations[]`` list) MUST
live on SUB-capability ids, never on bare parent capability ids.

Per guide §3.7 (configurations rules 3 & 4):
    3. In grouped connectors, each ``configurations[]`` entry's ``id``
       is a sub-capability id (e.g. ``automation-and-remediation_qualysv2``),
       never a bare parent capability id (e.g.
       ``automation-and-remediation``).
    4. Every sub-capability declared in ``capabilities.yaml`` MUST have
       a corresponding ``configurations[]`` entry in ``configurations.yaml``
       — even if it declares no configuration fields (in which case
       the entry carries only its ``view_group`` and ``configurations: []``).

CO144 enforces BOTH rules. Findings are aggregated into a single
``ValidationResult`` per connector; the result's ``path`` points at
``configurations.yaml``.

Skip cases (silent):
    - Non-grouped connectors.
    - Connector with no ``configurations.yaml`` AND no sub-capabilities
      (nothing to enforce).

Hard-fail cases (produce a ``ValidationResult``):
    - ``configurations.yaml`` entry ``id`` is a bare parent capability id.
    - ``configurations.yaml`` entry ``id`` is unknown (not in the
      declared sub-cap set AND not a parent cap id).
    - A declared sub-capability has no matching ``configurations[]``
      entry in ``configurations.yaml``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


# ============================================================
# Helpers
# ============================================================
def _collect_capability_id_sets(
    connector: Connector,
) -> Tuple[Set[str], Set[str]]:
    """Return (parent_cap_ids, sub_cap_ids) from
    ``connector.capabilities``."""
    parent_ids: Set[str] = set()
    sub_ids: Set[str] = set()
    for cap in connector.capabilities:
        if isinstance(cap.id, str):
            parent_ids.add(cap.id)
        for sub in cap.sub_capabilities:
            if isinstance(sub.id, str):
                sub_ids.add(sub.id)
    return parent_ids, sub_ids


def _iter_configuration_entries(
    connector: Connector,
) -> List[Dict[str, Any]]:
    """Return the raw ``configurations[]`` entries from
    ``configurations.yaml`` (empty list if the file is absent or the
    block is missing/mis-typed)."""
    conf_file = connector.configurations_file
    if not conf_file.exist:
        return []
    raw = conf_file.file_content
    if not isinstance(raw, dict):
        return []
    entries = raw.get("configurations")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


# ============================================================
# CO144 validator
# ============================================================
class IsConfigOnSubCapabilityValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO144"
    description = (
        "Validates that every `configurations[]` entry in "
        "`configurations.yaml` of a grouped connector uses a "
        "sub-capability id (not a bare parent capability id), and "
        "that every declared sub-capability has a corresponding "
        "`configurations[]` entry (even if empty)."
    )
    rationale = (
        "In grouped connectors, config params and `view_group` bind "
        "to sub-capabilities (each `configurations[]` entry `id` is a "
        "sub-capability id, one per integration tile), never to bare "
        "parent capability ids. This is required for the backend to "
        "route params to the correct integration and for the UI to "
        "render the correct tile. §3.7 configurations rules 3 & 4."
    )
    error_message = (
        "Grouped connector '{connector_id}': `configurations.yaml` "
        "sub-capability wiring is incorrect: {issues}"
    )
    related_field = "configurations"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONFIGURATIONS]

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
                    path=connector.configurations_file.file_path,
                )
            )
        return results

    def _check_connector(self, connector: Connector) -> List[str]:
        """Return aggregated issue strings, empty list if all good."""
        # Grouped-only.
        if not (connector.settings and connector.settings.grouped):
            return []

        parent_ids, sub_ids = _collect_capability_id_sets(connector)
        entries = _iter_configuration_entries(connector)

        # If there's nothing to inspect at all, silent skip. (Other
        # validators cover the "grouped connector missing
        # configurations.yaml" case.)
        if not entries and not sub_ids:
            return []

        issues: List[str] = []
        entry_ids: Set[str] = set()

        # Rule 3: every entry.id must be a sub-cap id (never a bare
        # parent, never unknown).
        for entry in entries:
            eid = entry.get("id")
            if not isinstance(eid, str):
                issues.append(
                    "`configurations[]` entry has a missing or " "non-string `id`"
                )
                continue
            entry_ids.add(eid)
            if eid in sub_ids:
                continue
            if eid in parent_ids:
                issues.append(
                    f"`configurations[]` entry id '{eid}' is a bare "
                    f"parent capability id; in grouped connectors it "
                    f"must be a sub-capability id (one of "
                    f"{sorted(sub_ids)!r})"
                )
                continue
            # Neither sub nor parent.
            issues.append(
                f"`configurations[]` entry id '{eid}' does not match "
                f"any declared sub-capability id (expected one of "
                f"{sorted(sub_ids)!r})"
            )

        # Rule 4: every declared sub-capability must have a matching
        # entry in configurations.yaml (even if empty).
        missing = sub_ids - entry_ids
        if missing:
            issues.append(
                f"declared sub-capabilities have no matching "
                f"`configurations[]` entry in configurations.yaml: "
                f"{sorted(missing)!r} (each sub-capability needs its "
                f"own entry — even an empty one with `configurations: "
                f"[]` — so its `view_group` is emitted)"
            )

        return issues

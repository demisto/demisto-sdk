"""CO136 - `automation-and-remediation` capability must include the
`defaultIgnore` backend-managed checkbox.

Per guide §3.7 rule 4 + Appendix J:
> "`defaultIgnore` lives under the `automation-and-remediation`
> capability's `configurations[]` (a `checkbox`, `config_type: backend`)
> — with no `view_group`. It controls 'Do not use in CLI by default'
> for commands. Omit `defaultIgnore` when there is no automation
> capability."

The validator fires ONLY when at least one XSOAR handler subscribes
to `automation-and-remediation` (bare capability id OR grouped-
namespaced variant like `automation-and-remediation_qualysv2`). For
each such capability id it enforces:

1. **Presence**: `configurations.yaml` MUST have a `configurations[]`
   entry whose `id` matches the capability id, containing a field
   whose runtime (post-serializer) id is `defaultIgnore`.
2. **Field shape** of that `defaultIgnore` field:
   - `field_type: checkbox`
   - `metadata.xsoar.config_type: backend`

Grouped connectors namespace field ids per profile (e.g. qualys uses
`xsoar-qualys_fim_defaultIgnore`). We resolve the runtime id via the
subscribing handler's ``serializer.yaml`` ``field_mappings`` — the
same source CO120 uses — so a namespaced id renamed back to
``defaultIgnore`` passes cleanly.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
    field_dicts_in_capability_entry,
    find_capability_config_entry,
    iter_handler_capability_ids,
)

ContentTypes = Connector

# ============================================================
# CO136 constants
# ============================================================
AUTOMATION_CAPABILITY = "automation-and-remediation"
DEFAULT_IGNORE_ID = "defaultIgnore"
EXPECTED_FIELD_TYPE = "checkbox"
EXPECTED_CONFIG_TYPE = "backend"


# ============================================================
# Helpers
# ============================================================
def _serializer_rename_map(handler: HandlerData) -> Dict[str, str]:
    """Return the ``connector_id -> runtime_name`` map built from
    ``handler.serializer.field_mappings``. Empty when no serializer or
    no ``field_mappings`` entries.

    A grouped connector may declare its ``defaultIgnore`` field as
    ``xsoar-qualys_fim_defaultIgnore`` and rename it back to
    ``defaultIgnore`` via a serializer entry:

        field_mappings:
          - id: xsoar-qualys_fim_defaultIgnore
            field_name: defaultIgnore
    """
    mapping: Dict[str, str] = {}
    ser = handler.serializer
    if ser is None:
        return mapping
    for fm in ser.field_mappings or []:
        if fm.field_name:
            mapping[fm.id] = fm.field_name
    return mapping


def _runtime_id(raw_id: str, rename_map: Dict[str, str]) -> str:
    """Resolve a raw field id via the serializer rename map. Returns
    the original id when no rename is defined (i.e. the raw id IS the
    runtime name)."""
    return rename_map.get(raw_id, raw_id)


def _field_config_type(field: Dict[str, Any]) -> Optional[str]:
    """Return ``metadata.xsoar.config_type`` from a raw field dict, or
    None if the path is missing / malformed."""
    metadata = field.get("metadata")
    if not isinstance(metadata, dict):
        return None
    xsoar = metadata.get("xsoar")
    if not isinstance(xsoar, dict):
        return None
    val = xsoar.get("config_type")
    return val if isinstance(val, str) else None


def _find_default_ignore_field(
    entry: Dict[str, Any], rename_map: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """Return the raw field dict whose runtime id (post-serializer
    rename) equals ``defaultIgnore`` inside the automation capability
    entry, or None if no such field exists."""
    for field in field_dicts_in_capability_entry(entry):
        raw_id = field.get("id")
        if not isinstance(raw_id, str):
            continue
        if _runtime_id(raw_id, rename_map) == DEFAULT_IGNORE_ID:
            return field
    return None


# ============================================================
# CO136 validator
# ============================================================
class IsValidAutomationCapabilityValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO136"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`automation-and-remediation` capability has a corresponding "
        "`defaultIgnore` (checkbox, config_type=backend) field under "
        "the capability's configurations entry in configurations.yaml. "
        "Grouped-connector namespaced ids are canonicalized via the "
        "handler's serializer.yaml field_mappings before matching."
    )
    rationale = (
        "`defaultIgnore` controls 'Do not use in CLI by default' for "
        "the commands surfaced by an XSOAR integration. Only "
        "automation-and-remediation exposes commands; other collection-"
        "only capabilities (fetch-issues, log-collection, etc.) don't "
        "have commands. If the automation capability is chosen but "
        "defaultIgnore isn't emitted (or isn't backend-managed), the "
        "backend cannot honor the 'do not use in CLI by default' opt-"
        "in and the integration's commands leak into the CLI namespace "
        "even when the user wanted them hidden."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handler(s) subscribing "
        "to the 'automation-and-remediation' capability but the "
        "`defaultIgnore` wiring is incomplete: {issues}"
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
        """Return a list of issue strings for the automation capability
        wiring on ``connector``. Empty means all good.

        For each (handler, cap_id) pair we check that the automation
        capability's configurations entry exists AND contains a
        `defaultIgnore` field (post-serializer resolution) with the
        correct field_type + config_type. Each unique cap_id is checked
        at most once even if multiple handlers share it via alternative
        auth options.
        """
        issues: List[str] = []
        checked_cap_ids: Set[str] = set()

        for handler in connector.xsoar_handlers:
            rename_map = _serializer_rename_map(handler)
            for cap_id in iter_handler_capability_ids(handler, AUTOMATION_CAPABILITY):
                if cap_id in checked_cap_ids:
                    continue
                checked_cap_ids.add(cap_id)
                issues.extend(
                    self._check_capability_entry(connector, cap_id, rename_map)
                )
        return issues

    def _check_capability_entry(
        self,
        connector: Connector,
        capability_id: str,
        rename_map: Dict[str, str],
    ) -> List[str]:
        entry = find_capability_config_entry(connector, capability_id)
        if entry is None:
            return [
                f"configurations.yaml has no `configurations[]` entry "
                f"with id '{capability_id}' - the automation capability "
                f"must have its own configurations entry containing "
                f"`defaultIgnore`"
            ]

        field = _find_default_ignore_field(entry, rename_map)
        if field is None:
            return [
                f"capability '{capability_id}' is missing the required "
                f"`defaultIgnore` field (checked runtime ids after "
                f"serializer field_mappings resolution)"
            ]

        issues: List[str] = []

        actual_type = field.get("field_type")
        if actual_type != EXPECTED_FIELD_TYPE:
            issues.append(
                f"capability '{capability_id}' field `defaultIgnore` "
                f"has field_type='{actual_type}' but must be "
                f"'{EXPECTED_FIELD_TYPE}'"
            )

        actual_ct = _field_config_type(field)
        if actual_ct != EXPECTED_CONFIG_TYPE:
            issues.append(
                f"capability '{capability_id}' field `defaultIgnore` "
                f"has metadata.xsoar.config_type='{actual_ct}' but must "
                f"be '{EXPECTED_CONFIG_TYPE}'"
            )

        return issues

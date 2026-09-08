"""CO136 - `automation-and-remediation` capability must include the
`defaultIgnore` backend-managed checkbox.

> "`defaultIgnore` (a `checkbox`, `config_type: backend`) controls
> 'Do not use in CLI by default' for commands. It MUST be declared
> for every handler subscribing to the `automation-and-remediation`
> capability (or a sub-capability whose parent is
> `automation-and-remediation`), and MAY live either under
> `configurations.yaml.general_configurations` or under the
> per-capability `configurations.yaml.configurations[<cap>]` entry —
> both surfaces are user-visible and either satisfies the requirement.
> It is NEVER emitted via ``serializer.yaml`` ``computed_fields``."

The validator fires ONLY when at least one XSOAR handler subscribes
to `automation-and-remediation` (bare capability id OR
grouped-namespaced variant like `automation-and-remediation_qualysv2`,
which is caught by
:meth:`HandlerData.capability_ids_matching`'s prefix-match rule). For
each such subscribing handler it enforces:

1. **Presence**: a field with runtime (post-serializer) id
   ``defaultIgnore`` MUST be visible to the handler from EITHER
   ``configurations.yaml.general_configurations`` OR the per-capability
   ``configurations.yaml.configurations[<cap>]`` entry. Sub-capability
   entries (which for grouped connectors live under the namespaced id)
   are handled by the walker's raw-YAML sweep.
2. **Field shape** of that ``defaultIgnore`` field:
   - ``field_type: checkbox``
   - ``metadata.xsoar.config_type: backend``

Grouped connectors namespace field ids per profile (e.g. qualys uses
``xsoar-qualys_fim_defaultIgnore``). The unified walker
(:mod:`connector_handler_view`) resolves the runtime id via each
handler's ``serializer.yaml`` ``field_mappings``, so a namespaced id
renamed back to ``defaultIgnore`` passes cleanly without any
per-validator serializer bookkeeping.

Per-cap-id deduplication: multiple handlers may subscribe to the
same automation cap id via alternative auth options; the required
field is shared, so we check each unique cap id at most once per
connector. The first subscribing handler drives the visibility
check (per-handler walker output — sufficient because the required
field is a connector-scoped backend knob that behaves identically
for every subscribing handler).
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.objects.connector_handler_view import (
    FieldOrigin,
    HandlerVisibleField,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)
ContentTypes = Connector

# ============================================================
# CO136 constants
# ============================================================
AUTOMATION_CAPABILITY = "automation-and-remediation"
DEFAULT_IGNORE_ID = "defaultIgnore"
EXPECTED_FIELD_TYPE = "checkbox"
EXPECTED_CONFIG_TYPE = "backend"

# ``defaultIgnore`` lives in configurations.yaml only — either under
# ``general_configurations`` or under the per-capability
# ``configurations[<cap>]`` entry. Both surfaces satisfy the
# requirement; connection.yaml and capabilities.yaml surfaces are
# out of scope by design.
_CONFIGURATIONS_YAML_ORIGINS = frozenset(
    {
        FieldOrigin.CONFIGURATIONS_GENERAL,
        FieldOrigin.CONFIGURATIONS_CAPABILITY,
    }
)


# ============================================================
# CO136 validator
# ============================================================
class IsValidAutomationCapabilityValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO136"
    description = (
        "Validates that every XSOAR handler subscribing to the "
        "`automation-and-remediation` capability has a visible "
        "`defaultIgnore` (checkbox, config_type=backend) field in "
        "configurations.yaml - either under `general_configurations` "
        "or under the per-capability configurations entry. Grouped-"
        "connector namespaced ids are canonicalized via the "
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

        For each (handler, cap_id) pair we check that a ``defaultIgnore``
        field (post-serializer resolution) is visible to the handler
        from either configurations.yaml surface, and that its shape
        matches. Each unique cap_id is checked at most once even if
        multiple handlers share it via alternative auth options.
        """
        issues: List[str] = []
        checked_cap_ids: Set[str] = set()

        for handler in connector.xsoar_handlers:
            for cap_id in handler.capability_ids_matching(AUTOMATION_CAPABILITY):
                if cap_id in checked_cap_ids:
                    continue
                checked_cap_ids.add(cap_id)
                issues.extend(
                    self._check_capability_wiring(connector, handler, cap_id)
                )
        return issues

    def _check_capability_wiring(
        self,
        connector: Connector,
        handler: HandlerData,
        capability_id: str,
    ) -> List[str]:
        """Return issue strings for a single (handler, cap_id) pair —
        empty when the ``defaultIgnore`` field is visible to the handler
        with the correct shape.

        The walker unifies "cap entry" + "general_configurations"
        placement, so a single lookup covers both valid surfaces.
        """
        field = self._find_default_ignore_visible_field(connector, handler)
        if field is None:
            return [
                f"handler '{handler.id}' subscribes to capability "
                f"'{capability_id}' but no visible `defaultIgnore` "
                f"field was found in configurations.yaml (checked "
                f"both `general_configurations` and per-capability "
                f"entries, resolving runtime ids via serializer "
                f"field_mappings)"
            ]

        issues: List[str] = []

        actual_type = field.field.field_type
        if actual_type != EXPECTED_FIELD_TYPE:
            issues.append(
                f"capability '{capability_id}' field `defaultIgnore` "
                f"has field_type='{actual_type}' but must be "
                f"'{EXPECTED_FIELD_TYPE}'"
            )

        actual_ct = field.xsoar_config_type
        if actual_ct != EXPECTED_CONFIG_TYPE:
            issues.append(
                f"capability '{capability_id}' field `defaultIgnore` "
                f"has metadata.xsoar.config_type='{actual_ct}' but must "
                f"be '{EXPECTED_CONFIG_TYPE}'"
            )

        return issues

    @staticmethod
    def _find_default_ignore_visible_field(
        connector: Connector,
        handler: HandlerData,
    ) -> Optional[HandlerVisibleField]:
        """Return the first HandlerVisibleField visible to ``handler``
        whose runtime name is ``defaultIgnore`` AND that originates from
        a ``configurations.yaml`` surface (general_configurations OR a
        per-capability entry) — or None if no such field exists.

        Uses the unified walker so serializer renames + grouped sub-cap
        entries are handled centrally.
        """
        for vf in connector.visible_fields_for_handler(handler):
            if vf.origin not in _CONFIGURATIONS_YAML_ORIGINS:
                continue
            if vf.runtime_name == DEFAULT_IGNORE_ID:
                return vf
        return None

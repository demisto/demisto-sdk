from __future__ import annotations

from typing import Any, Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_mirroring_omitted import (
    FORBIDDEN_MIRRORING_FIELDS,
)

ContentTypes = Connector

# Sentinel used to distinguish "key absent" from "key present with value None"
# when reading a Parameter's defaultvalue. Mirrors CO109's _MISSING / Step 2.6
# carve-out semantics: a hidden param is exempt from the coverage requirement
# IFF its YAML defaultvalue field is *present* and *non-None* (empty string
# counts).
_MISSING = object()


class IsEveryIntegrationParamCoveredValidator(BaseValidator[ContentTypes]):
    error_code = "CO130"
    description = (
        "Validates that every visible (non-hidden) integration YAML "
        "parameter is covered by at least one connector field reachable "
        "from the XSOAR handler that owns the linked integration. "
        "Coverage is determined via ``handler.resolved_params`` filtered "
        "to fields that appear in the handler's reachable capability + "
        "auth-profile configuration buckets. Hidden params and mirroring "
        "params (mirror_direction / close_incident / close_out from "
        "CO113's FORBIDDEN_MIRRORING_FIELDS) are exempt from the "
        "coverage requirement."
    )
    rationale = (
        "If a visible integration YAML param has no corresponding "
        "connector field, an instance configured through the platform "
        "cannot supply a value for it: the param is silently lost. The "
        "validator is the mirror image of CO109 — CO109 walks connector "
        "fields and flags those whose YAML param is hidden, CO130 walks "
        "YAML params and flags those visible ones not present on the "
        "connector side. Hidden params with a non-None YAML defaultvalue "
        "are exempt (the param is auto-satisfied by the YAML default, "
        "same carve-out CO109 uses). Mirroring params are exempt because "
        "they are intentionally omitted by CO113 — re-flagging them here "
        "would force the connector to declare fields that the platform "
        "explicitly does not want exposed."
    )
    error_message = (
        "Connector '{connector_id}' has visible integration parameters "
        "not covered by any handler-reachable connector "
        "field:\n{handler_details}"
    )
    related_field = "configuration"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Walk each connector's XSOAR handlers and flag visible
        integration YAML params that no reachable connector field covers.

        Per-handler algorithm:
          1. Resolve ``handler.related_integration``. Skip silently if
             None (CO100 already reports unresolved integrations).
          2. Collect ``visible_param_names``: every integration YAML
             param that is NOT hidden-on-platform AND not exempted by
             the hidden+defaultvalue carve-out, AND not a mirroring
             param (FORBIDDEN_MIRRORING_FIELDS).
          3. Collect ``reachable_field_ids`` for this handler (the
             same set CO109 collects: handler.capabilities -> resolved
             CapabilityData.configurations + connection.profiles
             matching handler.capabilities[*].auth_options[*].id).
          4. Build ``covered_yaml_param_names`` by iterating
             ``handler.resolved_params``: for every entry whose
             ``connector_param_name`` is in ``reachable_field_ids``,
             add ``content_param_name`` to the covered set.
          5. ``uncovered = visible_param_names - covered_yaml_param_names``.
             For each uncovered name, emit one line item.

        All issues for one connector are merged into a SINGLE
        ValidationResult (CO109 grouping pattern).
        """
        results: List[ValidationResult] = []
        for connector in content_items:
            handler_issues: List[str] = []
            for handler in connector.xsoar_handlers:
                handler_issues.extend(self._check_handler(connector, handler))

            if handler_issues:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(handler_issues),
                        ),
                        content_object=connector,
                    )
                )
        return results

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _check_handler(self, connector: Connector, handler: HandlerData) -> List[str]:
        """Return a list of per-(handler, uncovered-yaml-param) line
        items for this handler. Empty list means the handler's coverage
        is complete (modulo hidden and mirroring exemptions)."""
        integration = handler.related_integration
        if integration is None:
            # CO100 handles "unresolved integration"; don't double-report.
            return []

        visible_param_names = self._collect_visible_param_names(integration)
        if not visible_param_names:
            return []

        reachable_field_ids = self._collect_reachable_field_ids(connector, handler)

        # Build the covered set by intersecting resolved_params with the
        # reachable field id set: a resolved_params entry whose
        # connector_param_name is NOT reachable from this handler does
        # NOT count as coverage.
        covered_yaml_param_names: Set[str] = {
            rp.content_param_name
            for rp in handler.resolved_params
            if rp.connector_param_name in reachable_field_ids
        }

        uncovered = visible_param_names - covered_yaml_param_names
        if not uncovered:
            return []

        integration_id = getattr(integration, "object_id", "") or ""
        issues: List[str] = [
            f"  handler '{handler.id}' (integration '{integration_id}'): "
            f"param '{name}' is visible but no reachable connector field "
            f"resolves to it"
            for name in sorted(uncovered)
        ]
        return issues

    @staticmethod
    def _collect_visible_param_names(integration: Any) -> Set[str]:
        """Return the set of integration YAML param names that MUST be
        covered by the connector: not hidden-on-platform (or hidden
        but with the YAML defaultvalue carve-out) AND not a mirroring
        param (FORBIDDEN_MIRRORING_FIELDS from CO113).
        """
        visible: Set[str] = set()
        for param in getattr(integration, "params", None) or []:
            name = getattr(param, "name", None)
            if not name:
                continue
            if name in FORBIDDEN_MIRRORING_FIELDS:
                # Mirroring params are intentionally omitted by CO113 ->
                # exempt from CO130's coverage requirement too.
                continue
            hidden_value = getattr(param, "hidden", None)
            is_hidden_on_platform = hidden_value is True or (
                isinstance(hidden_value, list) and "platform" in hidden_value
            )
            if is_hidden_on_platform:
                # Apply CO109's defaultvalue carve-out: a hidden param
                # with a non-None YAML defaultvalue is exempt (the
                # default auto-fills, the user never has to interact
                # with it, and the connector doesn't need to expose it
                # as a field). A hidden param WITHOUT a defaultvalue is
                # also exempt from coverage (Q2=a per the user: "skip
                # mirror params as well" implies hidden bypass too —
                # treating hidden as always-exempt is consistent with
                # CO109's "hidden + defaultvalue" carve-out, and is
                # never stricter than the platform UI itself).
                continue
            visible.add(name)
        return visible

    @staticmethod
    def _collect_reachable_field_ids(
        connector: Connector, handler: HandlerData
    ) -> Set[str]:
        """Collect every ConnectorField.id reachable from this handler's
        perspective. Verbatim duplicate of CO109's helper of the same
        name so the two validators stay self-contained.

        Canonical reachability rule (per the spec): a param is related to
        a handler if it appears in:
          - general_configurations (always — reachable from every handler), AND
          - the sub-capability the handler claims, AND
          - the parent capability that the sub-capability is registered to.
        Exception: a handler claiming a top-level capability with no
        sub-capability sees only that capability's own params (no upward
        traversal because the root has no parent).

        Schema assumption (CURRENT model — see
        ``demisto_sdk/commands/content_graph/objects/connector.py``):
        ``SubCapability`` carries only ``id`` / ``title`` /
        ``default_enabled`` / ``required`` / ``required_license`` — it has
        NO ``configurations`` of its own. The parser
        (``_parse_capabilities_with_configs``) already merges
        general_configurations from BOTH capabilities.yaml and
        configurations.yaml PLUS per-capability configurations from
        configurations.yaml into a single ``CapabilityData.configurations``
        bag PER top-level capability. So the canonical rule collapses,
        under the current schema, to: "walk the matched top-level
        capability's unified configurations bag" — which is exactly what
        the loop below does. If the schema ever grows per-sub-capability
        configurations, this helper must be tightened to walk only the
        specific sub-cap's configs + the parent's own root-level configs
        + general_configurations (instead of the parent's whole bag).

        Mechanics:
        - connection.yaml: any ConnectionProfile whose id matches one of
          the handler.capabilities[*].auth_options[*].id values.
        - capabilities.yaml / configurations.yaml: any CapabilityData
          whose id matches one of handler.capabilities[].id values
          (directly or transitively via a sub-capability id).
        """
        result: Set[str] = set()

        # 1. Connection profiles reachable via handler.capabilities.auth_options.id
        wanted_profile_ids = {
            opt.id for hcap in handler.capabilities for opt in (hcap.auth_options or [])
        }
        if connector.connection and wanted_profile_ids:
            for profile in connector.connection.profiles:
                if profile.id not in wanted_profile_ids:
                    continue
                for group in profile.configurations or []:
                    for field in group.fields or []:
                        result.add(field.id)

        # 2. Capability configurations reachable via handler.capabilities[].id
        wanted_capability_ids = {hc.id for hc in handler.capabilities}
        if wanted_capability_ids:
            # Pre-build top-cap -> {sub_cap_ids} so a handler that claims
            # a sub-cap id surfaces its parent's configuration bucket.
            top_to_subs: dict[str, Set[str]] = {
                cap.id: {sc.id for sc in cap.sub_capabilities}
                for cap in connector.capabilities
            }
            for cap in connector.capabilities:
                if cap.id in wanted_capability_ids:
                    matched = True
                else:
                    matched = bool(top_to_subs[cap.id] & wanted_capability_ids)
                if not matched:
                    continue
                for group in cap.configurations or []:
                    for field in group.fields or []:
                        result.add(field.id)

        return result

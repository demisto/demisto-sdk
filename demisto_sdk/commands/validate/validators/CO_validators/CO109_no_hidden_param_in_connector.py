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

ContentTypes = Connector

# Sentinel used to distinguish "key absent" from "key present with value None"
# when reading a Parameter's defaultvalue. Mirrors connector_param_mapper.py's
# Step 2.6 carve-out semantics: a hidden param is allowed IFF its YAML
# defaultvalue field is *present* and *non-None* (empty string counts).
_MISSING = object()


class NoHiddenParamInConnectorValidator(BaseValidator[ContentTypes]):
    error_code = "CO109"
    description = (
        "Validates that every XSOAR integration YAML parameter that is "
        "referenced by an XSOAR handler in the connector is NOT hidden on "
        "the Cortex Platform (i.e. neither `hidden: true` nor `hidden` "
        "list containing 'platform' in the integration YAML)."
    )
    rationale = (
        "If a connector field resolves back to an integration YAML param "
        "that is hidden on the platform, the user cannot enter a value for "
        "it through the platform UI — the field is effectively unusable. "
        "This validator mirrors the Step 2.6 hidden-param filter used by "
        "the connectus migration mapper so the validator and the mapper "
        "stay aligned: a hidden param is exempted from failure when the "
        "YAML supplies a non-None defaultvalue (the user never has to "
        "interact with it because the YAML default is applied)."
    )
    error_message = (
        "Connector '{connector_id}' references hidden integration "
        "parameters that the user cannot fill on the platform UI:\n"
        "{handler_details}"
    )
    related_field = "configuration"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Walk each connector's XSOAR handlers and flag references to
        platform-hidden integration YAML params.

        Per-handler algorithm:
          1. Resolve ``handler.related_integration``. Skip silently if None
             (CO100 already reports unresolved integrations).
          2. Read the integration's full configuration list and build:
             - hidden_param_names: names that ARE hidden on the platform
               AND do NOT satisfy the YAML-defaultvalue carve-out.
          3. Collect all connector field ids reachable from this handler:
             - connection.yaml profile configurations for any
               ConnectionProfile whose id appears in
               handler.capabilities[*].auth_options[*].id
             - capabilities.yaml capability configurations for any
               CapabilityData whose id appears in handler.capabilities[].id
             - configurations.yaml general_configurations (always reachable)
          4. For each reachable field id, look it up in
             handler.resolved_params by ``connector_param_name``. If a match
             exists, check ``content_param_name`` against hidden_param_names
             — if hidden, emit one line item per
             ``(handler_id, field_id, yaml_param_name)`` tuple. Fields that
             do not resolve via resolved_params are silently skipped (per
             the Q4 design decision: resolved_params is the single source
             of truth for connector→YAML param resolution).

        All issues for a connector are merged into ONE ValidationResult.
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
        """Return a list of per-(handler, field) line items for hidden refs."""
        integration = handler.related_integration
        if integration is None:
            # CO100 handles "unresolved integration"; don't double-report.
            return []

        hidden_param_names = self._collect_hidden_param_names(integration)
        if not hidden_param_names:
            return []

        # Build resolution lookup once per handler.
        resolution = {
            rp.connector_param_name: rp.content_param_name
            for rp in handler.resolved_params
        }

        # Collect all reachable field ids from this handler's perspective.
        reachable_field_ids = self._collect_reachable_field_ids(connector, handler)

        issues: List[str] = []
        # Deterministic ordering for stable error messages.
        for field_id in sorted(reachable_field_ids):
            yaml_param_name = resolution.get(field_id)
            if yaml_param_name is None:
                # Field can't be resolved to a YAML param — skip per Q4.
                continue
            if yaml_param_name in hidden_param_names:
                issues.append(
                    f"handler '{handler.id}' field '{field_id}' resolves to "
                    f"integration YAML param '{yaml_param_name}' which is "
                    f"hidden on the platform"
                )
        return issues

    @staticmethod
    def _collect_hidden_param_names(integration: Any) -> Set[str]:
        """Return the set of integration YAML param names that are hidden on
        the platform AND do NOT qualify for the YAML-defaultvalue carve-out.

        Mirrors connector_param_mapper.py::_collect_hidden_params semantics.
        """
        hidden: Set[str] = set()
        for param in getattr(integration, "params", None) or []:
            name = getattr(param, "name", None)
            if not name:
                continue
            hidden_value = getattr(param, "hidden", None)
            is_hidden_on_platform = hidden_value is True or (
                isinstance(hidden_value, list) and "platform" in hidden_value
            )
            if not is_hidden_on_platform:
                continue
            # Carve-out: skip if the YAML supplies a non-None defaultvalue.
            # Use the sentinel pattern because Parameter.defaultvalue is
            # Optional[Any] — we treat *explicitly None* as "no default".
            defaultvalue = getattr(param, "defaultvalue", _MISSING)
            if defaultvalue is not _MISSING and defaultvalue is not None:
                continue
            hidden.add(name)
        return hidden

    @staticmethod
    def _collect_reachable_field_ids(
        connector: Connector, handler: HandlerData
    ) -> Set[str]:
        """Collect every ConnectorField.id reachable from this handler's
        perspective.

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
            # Pre-build top-cap -> set(sub_cap_ids) so a handler that claims a
            # sub-capability id pulls in its parent's configurations.
            for cap in connector.capabilities:
                if cap.id in wanted_capability_ids:
                    chosen = cap
                elif any(
                    sub.id in wanted_capability_ids for sub in cap.sub_capabilities
                ):
                    chosen = cap
                else:
                    continue
                for group in chosen.configurations or []:
                    for field in group.fields or []:
                        result.add(field.id)

        return result

from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Alias sets. An integration YML param whose ``name`` is in one of these sets
# means the connector must expose a corresponding user-facing field whose
# runtime (post-serializer) name is also in the set.
INSECURE_ALIASES: Set[str] = {"insecure", "unsecure", "verify", "secure"}
PROXY_ALIASES: Set[str] = {"proxy", "useproxy", "use_proxy"}

_FAMILIES: Tuple[Tuple[str, Set[str]], ...] = (
    ("proxy", PROXY_ALIASES),
    ("insecure", INSECURE_ALIASES),
)


class IsProxyAndInsecureExistsValidator(ConnectorsValidator[ContentTypes]):
    """CO120 - the connector must expose ``proxy`` / ``insecure`` when the
    backing integration does.

    Uses ``handler.resolved_params`` (built by the connector parser) as the
    single source of truth for "which params does this handler expose". Each
    ``ResolvedParamMapping`` already accounts for:

    - top-level ``general_configurations`` in ``connection.yaml`` (standard
      connectors),
    - per-profile ``configurations[]`` under ``profiles[]`` in
      ``connection.yaml`` (grouped connectors, where field ids are
      namespaced e.g. ``plain_jira_v3_proxy``),
    - serializer.yaml ``field_mappings[]`` that rename a namespaced connector
      id back to its runtime name (``proxy`` / ``insecure``).

    So the rule collapses to: for each XSOAR handler whose backing
    integration declares a ``proxy`` / ``insecure`` param, some entry in
    ``handler.resolved_params`` must have a ``content_param_name`` in the
    corresponding alias set.

    Skip / error policy:

    - Non-XSOAR handlers: skipped (mirrors CO114 / CO194).
    - XSOAR handler with ``related_integration is None``: **flagged** as an
      error. An XSOAR handler with no resolvable integration is a real
      migration bug, not something to silently pass. (CO114 flags the same
      situation from a licensing angle; here we flag it from the
      general-params angle so the message tells the author which specific
      family the connector cannot be verified for.)
    - Connector with no ``connection.yaml``: skipped defensively (CO118 /
      other validators catch missing connection.yaml).
    """

    error_code = "CO120"
    description = (
        "Validates that when the backing integration declares a 'proxy' or "
        "'insecure' parameter, the connector exposes a corresponding field "
        "for each XSOAR handler - either directly (id in the alias set) or "
        "via a serializer.yaml field_mappings rename whose content_param_name "
        "resolves to the alias set."
    )
    rationale = (
        "'proxy' and 'insecure' are platform built-in parameters. If the "
        "integration accepts them but the connector does not surface a "
        "corresponding user-configurable field, the customer cannot control "
        "transport behavior the integration was designed for."
    )
    error_message = (
        "Connector '{connector_id}' handler '{handler_id}' (integration "
        "'{integration_id}'): {details}."
    )
    related_field = "resolved_params"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _integration_families(handler: HandlerData) -> Set[str]:
        """Return the set of family names the integration behind ``handler``
        declares in its YML params (subset of {"proxy", "insecure"}).
        Empty when the integration is unresolved or has no params.
        """
        integration = handler.related_integration
        if integration is None:
            return set()
        params = getattr(integration, "params", None) or []
        found: Set[str] = set()
        for param in params:
            name = getattr(param, "name", None)
            if not isinstance(name, str):
                continue
            for family_name, aliases in _FAMILIES:
                if name in aliases:
                    found.add(family_name)
        return found

    @staticmethod
    def _resolved_content_names(handler: HandlerData) -> Set[str]:
        """Set of runtime (post-serializer) parameter names this handler
        actually exposes to the integration. Combines all fields collected
        by the connector parser (connection general_configurations, profile
        configurations for this handler, capabilities/configurations
        sections) with any serializer-driven renames.
        """
        names: Set[str] = set()
        for rp in handler.resolved_params:
            if rp.content_param_name:
                names.add(rp.content_param_name)
        return names

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            if connector.connection is None:
                # Nothing to enforce without connection.yaml.
                continue

            for handler in connector.handlers:
                if not handler.is_xsoar:
                    continue

                results.extend(self._check_handler(connector, handler))

        return results

    def _check_handler(
        self, connector: ContentTypes, handler: HandlerData
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        connection_path = connector.connection_file.file_path
        integration_id_label = handler.xsoar_integration_id or "?"

        if handler.related_integration is None:
            # XSOAR handler with no linked integration is a real bug - flag it.
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        integration_id=integration_id_label,
                        details=(
                            "XSOAR handler has no resolvable backing "
                            "integration (related_integration is None); "
                            "cannot verify proxy/insecure exposure. Ensure "
                            "the graph is built and the integration is "
                            "reachable on marketplacev2/platform"
                        ),
                    ),
                    content_object=connector,
                    path=connection_path,
                )
            )
            return results

        required_families = self._integration_families(handler)
        if not required_families:
            return results  # Integration declares no proxy/insecure param.

        exposed_content_names = self._resolved_content_names(handler)

        for family in sorted(required_families):
            aliases = PROXY_ALIASES if family == "proxy" else INSECURE_ALIASES
            if aliases & exposed_content_names:
                continue  # Handler exposes at least one alias for this family.

            alias_list = sorted(aliases)
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        handler_id=handler.id,
                        integration_id=integration_id_label,
                        details=(
                            f"integration declares a '{family}' param but "
                            f"the handler does not expose a corresponding "
                            f"field (either a direct id in {alias_list}, or "
                            f"a serializer.yaml field_mappings entry whose "
                            f"field_name resolves to one of {alias_list})"
                        ),
                    ),
                    content_object=connector,
                    path=connection_path,
                )
            )

        return results

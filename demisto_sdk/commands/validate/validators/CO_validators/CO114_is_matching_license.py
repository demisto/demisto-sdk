from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.common.constants import ALL_SUPPORTED_MODULES
from demisto_sdk.commands.common.tools import get_content_item_supported_modules
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingLicenseValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO114"
    description = (
        "Validates that each capability/sub-capability's required_license is a "
        "subset of the supported modules of every integration whose handler "
        "subscribes to it. A capability with no required_license is treated as "
        "requiring all modules."
    )
    rationale = (
        "A capability may only require licenses (modules) that the backing "
        "integration actually supports. If a capability requires a module the "
        "integration does not support - or requires all modules while the "
        "integration supports only some - the connector promises functionality "
        "the integration cannot deliver under that license."
    )
    error_message = (
        "Connector '{connector_id}' has capabilities whose required_license is "
        "not supported by the backing integration: {details}."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CAPABILITIES]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            details: List[str] = []

            for capability in connector.capabilities:
                # Check the parent capability itself. Unlike SubCapability, a
                # CapabilityData exposes its licenses via ``config``, not a
                # top-level ``required_license`` field.
                capability_license = (
                    capability.config.required_license if capability.config else []
                )
                details.extend(
                    self._check_entry(
                        connector,
                        entry_id=capability.id,
                        required_license=capability_license,
                    )
                )
                # ...and each of its sub-capabilities. Note the parser already
                # resolves the effective required_license for a sub-capability
                # (its own value, or inherited from the parent capability when
                # the sub-capability declares none), so reading
                # ``sub_capability.required_license`` here honours inheritance.
                for sub_capability in capability.sub_capabilities:
                    details.extend(
                        self._check_entry(
                            connector,
                            entry_id=sub_capability.id,
                            required_license=sub_capability.required_license,
                        )
                    )

            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details="; ".join(details),
                        ),
                        content_object=connector,
                        path=connector.capabilities_file.file_path,
                    )
                )

        return results

    def _check_entry(
        self,
        connector: ContentTypes,
        entry_id: str,
        required_license: List[str],
    ) -> List[str]:
        """Check one capability/sub-capability against its subscribing handlers.

        For every **XSOAR** handler that subscribes to ``entry_id``, the entry's
        effective required licenses must be a subset of the backing integration's
        supported modules (resolved via ``get_content_item_supported_modules``,
        which falls back from the integration's own ``supportedModules`` to the
        parent pack's and finally to the platform defaults).

        An entry with no ``required_license`` is treated as requiring **all**
        modules (``ALL_SUPPORTED_MODULES``): it claims support under every
        license, so the integration must support all of them.

        Handler-scope rules:

        * **Non-XSOAR handlers** (``handler.is_xsoar`` is ``False`` — e.g.
          SaaS identity / data-security / posture handlers whose
          ``metadata.module`` is not ``"xsoar"``) are skipped entirely. They
          have no backing XSOAR integration, so the concept of "the
          integration's supported modules must include this license" does
          not apply to them at all.
        * **XSOAR handlers with no declared** ``xsoar-integration-id``: this
          is a real content bug (every XSOAR handler MUST label its backing
          integration) and is flagged explicitly rather than skipped.
        * **XSOAR handlers whose declared integration did not resolve** in
          the graph is flagged as unverifiable; the most common cause is
          that the integration's ``marketplaces`` do not include
          ``PLATFORM`` (see the connector-flow filter in
          ``ConnectorAwareInitializer._graph_expand_integrations``).
        """
        details: List[str] = []

        # No required_license => the entry claims support under ALL licenses.
        required_set: Set[str] = (
            set(required_license) if required_license else set(ALL_SUPPORTED_MODULES)
        )

        handler_ids = self._subscribing_handler_ids(connector, entry_id)
        if not handler_ids:
            # No handler subscribes to this entry. The "must have a subscriber"
            # rule is handled within UCP itself; here there is nothing to check.
            return details

        for handler_id in handler_ids:
            handler = next((h for h in connector.handlers if h.id == handler_id), None)
            if handler is None:
                continue

            # Non-XSOAR handlers (SaaS identity/data-security/posture etc.)
            # have no backing XSOAR integration -- the license-vs-modules
            # concept does not apply to them, so skip entirely.
            if not handler.is_xsoar:
                continue

            # An XSOAR handler MUST declare its backing integration id; a
            # missing id is a real content bug, not something to skip.
            if not handler.xsoar_integration_id:
                details.append(
                    f"'{entry_id}' cannot be verified: the subscribing XSOAR "
                    f"handler '{handler_id}' does not declare an "
                    f"'xsoar-integration-id' (every XSOAR handler must label "
                    f"its backing integration)"
                )
                continue

            integration = handler.related_integration
            if integration is None:
                details.append(
                    f"'{entry_id}' required_license cannot be verified: the "
                    f"subscribing handler '{handler_id}' references integration "
                    f"'{handler.xsoar_integration_id}' which was not resolved "
                    f"(check the integration exists in the graph and its "
                    f"'marketplaces' include 'PLATFORM')"
                )
                continue

            # Ensure the integration's parent pack is loaded before resolving
            # supported modules. ``get_content_item_supported_modules`` reads
            # the raw ``integration.pack`` attribute for its fallback, but on a
            # graph-resolved integration that attribute is lazily populated -
            # touching the ``in_pack`` property loads it from the relationships
            # so the pack's ``supportedModules`` are actually consulted (instead
            # of silently falling back to the platform defaults).
            _ = getattr(integration, "in_pack", None)

            # get_content_item_supported_modules resolves integration ->
            # pack -> platform defaults, returning ALL platform modules when
            # neither the integration nor its pack declares supportedModules.
            # It returns an empty set only for non-PLATFORM items (which the
            # connector flow filters out); treat that as "supports all" too.
            supported = get_content_item_supported_modules(integration) or set(
                ALL_SUPPORTED_MODULES
            )
            missing = required_set - supported
            if missing:
                details.append(
                    f"'{entry_id}' requires license(s) {sorted(missing)} not "
                    f"supported by integration '{handler.xsoar_integration_id}' "
                    f"(supported modules: {sorted(supported)})"
                )

        return details

    @staticmethod
    def _subscribing_handler_ids(connector: ContentTypes, entry_id: str) -> List[str]:
        """Return the handler ids subscribing to the capability/sub-capability."""
        mapping = connector.capability_handler_map.get(entry_id)
        if not mapping:
            return []
        return list(mapping.handler_ids)

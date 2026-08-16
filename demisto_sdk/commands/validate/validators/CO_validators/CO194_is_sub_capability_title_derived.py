from __future__ import annotations

from typing import Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
    SubCapability,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsSubCapabilityTitleDerivedValidator(ConnectorsValidator[ContentTypes]):
    """Validate that each sub-capability's title matches its backing
    integration's display name — enforced on ALL grouped connectors,
    regardless of git status.

    The complementary structural id derivation lives in CO113, which only
    runs on newly added connectors because sub-capability ids cannot be
    changed after publish. Titles, in contrast, are display-only and safe
    to update at any time, so this rule keeps running for every existing
    grouped connector to catch drift as integration display names change.
    """

    error_code = "CO194"
    description = (
        "Validates that each sub-capability in a grouped connector has a "
        "title equal to the linked integration's display name. Runs on all "
        "grouped connectors, not only newly added ones."
    )
    rationale = (
        "A sub-capability's title is the customer-facing label for the "
        "integration it maps to; keeping it in sync with the integration's "
        "display name prevents the UI from drifting away from what the "
        "underlying integration is actually called. Unlike sub-capability "
        "ids (governed by CO113 for newly added connectors only), titles "
        "are safe to change and therefore enforced everywhere."
    )
    error_message = (
        "Grouped connector '{connector_id}' has sub-capabilities whose "
        "title does not match the backing integration display name: {details}."
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
            # Grouped-only: short-circuit for non-grouped connectors.
            if not (connector.settings and connector.settings.grouped):
                continue

            details: List[str] = []

            for capability in connector.capabilities:
                for sub_capability in capability.sub_capabilities:
                    details.extend(
                        self._check_sub_capability_title(connector, sub_capability)
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

    def _check_sub_capability_title(
        self,
        connector: ContentTypes,
        sub_capability: SubCapability,
    ) -> List[str]:
        """Validate a single sub-capability's title against the linked
        integration's display name.

        Handler-scope rules mirror CO114:

        * **Non-XSOAR handlers** (``handler.is_xsoar`` is ``False``) are
          skipped entirely — they have no backing XSOAR integration whose
          display name we could compare the title against.
        * **XSOAR handlers with no** ``xsoar-integration-id`` are flagged as
          a real content bug (every XSOAR handler MUST label its backing
          integration).
        * **XSOAR handlers whose declared integration did not resolve** are
          reported as unverifiable rather than silently passing, so a
          missing/incomplete graph never produces a false PASS. The most
          common cause is that the integration's ``marketplaces`` do not
          include ``PLATFORM`` (see the connector-flow filter in
          ``ConnectorAwareInitializer._graph_expand_integrations``).

        The "at least one subscribing handler" requirement is intentionally
        NOT enforced here -- that rule is handled within UCP itself. When
        no handler subscribes we simply have nothing to compare the title
        to and skip.
        """
        sub_id = sub_capability.id

        handler = self._subscribing_handler(connector, sub_id)
        if handler is None:
            # No handler subscribes to this sub-capability. UCP already
            # enforces the "must have a subscriber" rule elsewhere.
            return []

        # Non-XSOAR handlers have no backing XSOAR integration display name
        # to compare against - the title-vs-display-name concept does not
        # apply, so skip entirely.
        if not handler.is_xsoar:
            return []

        # An XSOAR handler MUST declare its backing integration id; a
        # missing id is a real content bug, not something to skip.
        if not handler.xsoar_integration_id:
            return [
                f"sub-capability '{sub_id}' cannot be verified: the "
                f"subscribing XSOAR handler '{handler.id}' does not "
                f"declare an 'xsoar-integration-id' (every XSOAR handler "
                f"must label its backing integration)"
            ]

        integration = handler.related_integration
        if integration is None:
            # We have a subscribing handler but the graph didn't resolve
            # the integration - report as unverifiable rather than pass.
            integration_id = handler.xsoar_integration_id
            return [
                f"sub-capability '{sub_id}' title could not be verified: "
                f"the subscribing handler '{handler.id}' references "
                f"integration '{integration_id}' which was not resolved "
                f"(check the integration exists in the graph and its "
                f"'marketplaces' include 'PLATFORM')"
            ]

        display_name = integration.display_name
        if display_name and sub_capability.title != display_name:
            return [
                f"sub-capability '{sub_id}' title must be '{display_name}', "
                f"got '{sub_capability.title}'"
            ]

        return []

    @staticmethod
    def _subscribing_handler(
        connector: ContentTypes, sub_capability_id: str
    ) -> Optional[HandlerData]:
        """Return the first handler subscribing to the given sub-capability.

        Uses the connector's ``capability_handler_map`` (keyed by both
        capability and sub-capability ids). Returns ``None`` when no
        handler subscribes to the sub-capability.
        """
        mapping = connector.capability_handler_map.get(sub_capability_id)
        if not mapping or not mapping.handler_ids:
            return None

        handler_id = mapping.handler_ids[0]
        return next((h for h in connector.handlers if h.id == handler_id), None)

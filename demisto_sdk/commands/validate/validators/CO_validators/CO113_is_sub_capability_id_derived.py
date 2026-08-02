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


def normalize_integration_id(integration_id: str) -> str:
    """Normalize an integration id for use in a sub-capability id.

    Mirrors the handler-id normalization (lowercase, spaces -> dashes).
    """
    return integration_id.lower().replace(" ", "-")


class IsSubCapabilityIdDerivedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO113"
    description = (
        "Validates that each sub-capability in a grouped connector has an id "
        "derived as '<capability_id>_<normalized_integration_id>' and a title "
        "equal to the linked integration's display name."
    )
    rationale = (
        "Sub-capability ids and titles are derived deterministically from the "
        "parent capability and the integration they belong to. A sub-capability "
        "id that does not follow '<capability_id>_<normalized_integration_id>', "
        "or a title that does not match the integration's display name, "
        "indicates the capabilities.yaml drifted from the handler/integration."
    )
    error_message = (
        "Grouped connector '{connector_id}' has invalid sub-capabilities: "
        "{details}."
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
                        self._check_sub_capability(
                            connector, capability.id, sub_capability
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

    def _check_sub_capability(
        self,
        connector: ContentTypes,
        capability_id: str,
        sub_capability: SubCapability,
    ) -> List[str]:
        """Validate a single sub-capability's id derivation and title.

        Iterates from the capabilities.yaml side. The subscribing handler (if
        any) is the source of both the integration id (used to derive the id)
        and the integration's display name (used to check the title).

        This method never silently passes: when a sub-capability has a
        subscribing handler but the referenced integration could not be
        resolved (e.g. the content graph was not built), the title check is
        reported as unverifiable rather than skipped, so a missing graph never
        produces a false PASS.

        The "at least one subscribing handler" requirement is intentionally NOT
        enforced here -- that is owned by CO115. The structural id pattern is
        still enforced even when no handler subscribes, so a mis-derived id is
        never accepted.
        """
        details: List[str] = []
        sub_id = sub_capability.id

        # Structural pattern: id must be '<capability_id>_<segment>' with a
        # non-empty segment. This holds regardless of handler resolution.
        prefix = f"{capability_id}_"
        segment = sub_id[len(prefix):] if sub_id.startswith(prefix) else None
        if not segment:
            details.append(
                f"sub-capability '{sub_id}' id must follow the pattern "
                f"'{capability_id}_<normalized_integration_id>'"
            )
            # Without a valid prefix/segment we cannot derive anything further.
            return details

        handler = self._subscribing_handler(connector, sub_id)
        if handler is None:
            # No handler subscribes to this sub-capability. CO115 owns the
            # "must have a subscriber" rule; here we only verified the
            # structural pattern above, so nothing more to check.
            return details

        integration_id = handler.xsoar_integration_id
        if integration_id:
            expected_id = (
                f"{capability_id}_{normalize_integration_id(integration_id)}"
            )
            if sub_id != expected_id:
                details.append(
                    f"sub-capability '{sub_id}' id must be '{expected_id}' "
                    f"(derived from integration '{integration_id}')"
                )

        # Title must equal the linked integration's display name.
        integration = handler.related_integration
        if integration is None:
            details.append(
                f"sub-capability '{sub_id}' title could not be verified: the "
                f"subscribing handler '{handler.id}' references integration "
                f"'{integration_id}' which was not resolved (ensure the content "
                f"graph is built)"
            )
        else:
            display_name = integration.display_name
            if display_name and sub_capability.title != display_name:
                details.append(
                    f"sub-capability '{sub_id}' title must be '{display_name}', "
                    f"got '{sub_capability.title}'"
                )

        return details

    @staticmethod
    def _subscribing_handler(
        connector: ContentTypes, sub_capability_id: str
    ) -> Optional[HandlerData]:
        """Return the first handler subscribing to the given sub-capability.

        Uses the connector's ``capability_handler_map`` (keyed by both
        capability and sub-capability ids). Returns ``None`` when no handler
        subscribes to the sub-capability.
        """
        mapping = connector.capability_handler_map.get(sub_capability_id)
        if not mapping or not mapping.handler_ids:
            return None

        handler_id = mapping.handler_ids[0]
        return next(
            (h for h in connector.handlers if h.id == handler_id), None
        )

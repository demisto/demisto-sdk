from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

# Maps a collection capability id (the segment before the "_<integration>"
# suffix on a sub-capability, or the bare capability id) to a tuple of:
#   1. the Integration content-graph attribute that must be True (the Pydantic
#      field name, which differs from the raw YAML key), and
#   2. the human-readable integration YAML flag key used in error messages.
COLLECTION_CAPABILITY_TO_FLAG: Dict[str, Tuple[str, str]] = {
    "fetch-issues": ("is_fetch", "isfetch"),
    "log-collection": ("is_fetch_events", "isfetchevents"),
    "fetch-assets-and-vulnerabilities": ("is_fetch_assets", "isfetchassets"),
    "fetch-secrets": ("is_fetch_credentials", "isfetchcredentials"),
    "threat-intelligence-and-enrichment": ("is_feed", "feed"),
}


class IsConnectorMatchesIntegrationFlagsValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO116"
    description = (
        "Validates that when a connector declares a collection "
        "capability/sub-capability (fetch-issues, log-collection, "
        "fetch-assets-and-vulnerabilities, fetch-secrets, "
        "threat-intelligence-and-enrichment), the backing integration has the "
        "corresponding fetch flag enabled (e.g. log-collection requires "
        "script.isfetchevents: true)."
    )
    rationale = (
        "A collection capability promises the platform that the integration "
        "collects that data. If the integration's matching fetch flag is off, "
        "the connector advertises collection functionality the integration "
        "cannot perform."
    )
    error_message = (
        "Connector '{connector_id}' declares collection capabilities that are "
        "not backed by the integration's flags: {details}."
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
                if capability.sub_capabilities:
                    # A parent capability with sub-capabilities is checked
                    # through its sub-capabilities (each carries the
                    # "<capability-id>_<integration>" form).
                    for sub_capability in capability.sub_capabilities:
                        details.extend(
                            self._check_entry(connector, sub_capability.id)
                        )
                else:
                    details.extend(self._check_entry(connector, capability.id))

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
    ) -> List[str]:
        """Check one capability/sub-capability against its handlers' integrations.

        Only collection capabilities are checked. For every handler subscribing
        to a collection entry, the backing integration must have the mapped
        fetch flag enabled. A subscribing handler whose integration cannot be
        resolved is flagged (never silently skipped).
        """
        details: List[str] = []

        flag_mapping = self._collection_flag_for(entry_id)
        if flag_mapping is None:
            # Not a collection capability - nothing to check.
            return details

        attr_name, flag_key = flag_mapping

        handler_ids = self._subscribing_handler_ids(connector, entry_id)
        for handler_id in handler_ids:
            handler = next(
                (h for h in connector.handlers if h.id == handler_id), None
            )
            if handler is None:
                continue

            integration = handler.related_integration
            if integration is None:
                details.append(
                    f"'{entry_id}' cannot be verified: the subscribing handler "
                    f"'{handler_id}' references integration "
                    f"'{handler.xsoar_integration_id}' which was not resolved "
                    f"(ensure the content graph is built)"
                )
                continue

            if not getattr(integration, attr_name, False):
                details.append(
                    f"'{entry_id}' requires integration "
                    f"'{handler.xsoar_integration_id}' to have "
                    f"'{flag_key}' enabled, but it is disabled"
                )

        return details

    @staticmethod
    def _collection_flag_for(entry_id: str) -> Optional[Tuple[str, str]]:
        """Resolve the collection flag mapping for a capability/sub-capability id.

        Sub-capability ids take the form ``<capability-id>_<integration>``; the
        capability id is the segment before the first underscore. Bare
        capability ids are matched directly.
        """
        prefix = entry_id.split("_", 1)[0]
        return COLLECTION_CAPABILITY_TO_FLAG.get(prefix)

    @staticmethod
    def _subscribing_handler_ids(
        connector: ContentTypes, entry_id: str
    ) -> List[str]:
        """Return the handler ids subscribing to the capability/sub-capability."""
        mapping = connector.capability_handler_map.get(entry_id)
        if not mapping:
            return []
        return list(mapping.handler_ids)

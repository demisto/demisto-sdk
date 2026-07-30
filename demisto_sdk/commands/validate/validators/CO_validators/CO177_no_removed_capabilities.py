from __future__ import annotations

from typing import Iterable, List, Set, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoRemovedCapabilitiesValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO177"
    description = (
        "Breaking-change check: a capability or sub-capability present in the "
        "prior version of the connector must not be removed."
    )
    rationale = (
        "Removing a capability or sub-capability is a breaking change: "
        "existing enabled instances that rely on it would lose functionality. "
        "Capabilities and sub-capabilities may only be added, never removed, "
        "across versions."
    )
    error_message = (
        "Connector '{connector_id}' removed capabilities/sub-capabilities "
        "that existed in the prior version: {removed}."
    )
    related_field = "capabilities"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                # No prior version to compare against - cannot be a removal.
                continue

            removed = self._removed_capability_ids(old_connector, connector)
            if removed:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            removed=", ".join(map(repr, sorted(removed))),
                        ),
                        path=connector.capabilities_file.file_path,
                        content_object=connector,
                    )
                )

        return results

    @staticmethod
    def _capability_ids(connector: ContentTypes) -> Set[str]:
        """Return every capability id and sub-capability id in the connector."""
        ids: Set[str] = set()
        for capability in connector.capabilities:
            ids.add(capability.id)
            for sub_capability in capability.sub_capabilities:
                ids.add(sub_capability.id)
        return ids

    def _removed_capability_ids(
        self, old_connector: ContentTypes, new_connector: ContentTypes
    ) -> Set[str]:
        old_ids = self._capability_ids(old_connector)
        new_ids = self._capability_ids(new_connector)
        return old_ids - new_ids

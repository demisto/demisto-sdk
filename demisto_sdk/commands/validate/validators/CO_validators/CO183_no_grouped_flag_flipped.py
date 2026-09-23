from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class NoGroupedFlagFlippedValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO183"
    description = (
        "Breaking-change check: ``settings.grouped`` must not change value "
        "(``true`` ↔ ``false``) between the prior and new versions of a "
        "connector. The flag fundamentally alters the connector shape "
        "(single service vs multi-service view-group registry) and the id "
        "conventions it enforces."
    )
    rationale = (
        "Flipping ``grouped`` changes how the platform materializes the "
        "connector: id namespacing, view-group registration, and "
        "auth-profile expectations all differ between the two modes. Any "
        "enabled instance built for one mode would fail to load - or worse, "
        "load with a corrupt registry - under the other. New connectors may "
        "choose either mode, but an existing connector must keep its choice."
    )
    error_message = (
        "Connector '{connector_id}' flipped `settings.grouped` from "
        "{old_val!r} to {new_val!r}. This flag is not changeable across "
        "versions once published."
    )
    related_field = "settings.grouped"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """One result per connector whose ``settings.grouped`` flipped."""
        results: List[ValidationResult] = []

        for connector in content_items:
            old_connector = cast(ContentTypes, connector.old_base_content_object)
            if old_connector is None:
                continue

            old_val = self._grouped(old_connector)
            new_val = self._grouped(connector)
            if old_val == new_val:
                continue

            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        connector_id=connector.object_id,
                        old_val=old_val,
                        new_val=new_val,
                    ),
                    content_object=connector,
                    path=connector.path,
                )
            )

        return results

    @staticmethod
    def _grouped(connector: ContentTypes) -> bool:
        """Return ``settings.grouped``. Missing settings block defaults to
        False (mirrors the model default so first-time serializations don't
        false-flag when a prior version omitted the block entirely)."""
        settings = getattr(connector, "settings", None)
        if settings is None:
            return False
        return bool(getattr(settings, "grouped", False))

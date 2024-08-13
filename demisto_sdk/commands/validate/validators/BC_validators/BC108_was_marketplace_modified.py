from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses, MarketplaceVersions
from demisto_sdk.commands.content_graph.objects import Pack, Playbook
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    IncidentType,
    Mapper,
    IndicatorField,
    IndicatorType,
    IncidentField,
    Pack,
    Playbook,
]
ALL_MARKETPLACES = list(MarketplaceVersions)


class WasMarketplaceModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC108"
    description = "Ensuring that the 'marketplaces' property hasn't been removed or added in a manner that effectively removes all others."
    rationale = "Removing `marketplaces` or adding a new one that effectively removes all others can cause issues with the content item's visibility and availability."
    error_message = "You can't delete current marketplaces or add new ones if doing so will remove existing ones. Please undo the change or request a forced merge."
    related_field = "marketplaces"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            new_marketplaces = content_item.marketplaces
            old_marketplaces = content_item.old_base_content_object.marketplaces  # type: ignore

            # if the content is not a pack, we may want to compare to the pack marketplaces as well, since the item inherits the pack marketplaces, if not specified
            if not isinstance(content_item, Pack):
                pack_marketplaces = content_item.in_pack.marketplaces  # type: ignore

                # If all marketplaces are included, it might be due to the field not appearing. However, in reality, it is available only in a specific marketplace inherited from the pack marketplace.
                # In this scenario, we will compare the pack's marketplaces as it serves as the source of truth.
                if set(old_marketplaces) == set(ALL_MARKETPLACES):
                    old_marketplaces = pack_marketplaces

                #  If the content item was renamed (perhaps because it was moved into a new pack), we need to compare the marketplaces at the pack level.
                if content_item.git_status == GitStatuses.RENAMED:
                    old_pack_marketplaces = (
                        content_item.old_base_content_object.in_pack.marketplaces  # type: ignore[union-attr]
                    )
                    old_marketplaces = old_pack_marketplaces
                    new_marketplaces = pack_marketplaces

            if not (set(old_marketplaces).issubset(set(new_marketplaces))):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message,
                        content_object=content_item,
                    )
                )

        return results

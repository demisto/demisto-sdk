from typing import List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.incident_to_alert import (
    prepare_descriptions_and_names,
    prepare_playbook_access_fields,
)


class MarketplaceIncidentToAlertPlaybooksPreparer:
    @staticmethod
    def prepare(
        playbook: ContentItem,
        data: dict,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        supported_marketplaces: Optional[List[MarketplaceVersions]] = None,
    ) -> dict:
        """
        Iterate over all the given playbook's descriptions and names fields and if a description or a name field
        contains the word incident / incidents (without the wrapper), then replace it with alert / alerts just in case
        of XSIAM Marketplace.
        In any case (for all Marketplaces) remove the wrapper (<-incident-> to incident, <-incidents-> to incidents).
        Args:
            data: content item data
            current_marketplace: the destination marketplace.
            supported_marketplaces: list of the marketplaces this content item supports.

        Returns: A (possibly) modified content item data

        """

        if supported_marketplaces is None:
            supported_marketplaces = list(MarketplaceVersions)
        data = prepare_descriptions_and_names(data, current_marketplace)

        # convert the access fields of the playbook from the `incident` terminology to `alert` only if the playbook
        # should be uploaded to the XSIAM marketplace and is supported in more than one marketplace.
        if (
            current_marketplace == MarketplaceVersions.MarketplaceV2
            and MarketplaceVersions.MarketplaceV2 in supported_marketplaces
        ):
            data = prepare_playbook_access_fields(data, playbook)

        return data

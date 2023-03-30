import logging

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.prepare_content.preparers.incident_to_alert import (
    prepare_descriptions_and_names, prepare_playbook_access_fields,
)

logger = logging.getLogger("demisto-sdk")


class MarketplaceIncidentToAlertPlaybooksPreparer:
    @staticmethod
    def prepare(data: dict, supported_marketplaces: list,
                current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR) -> dict:
        """
        Iterate over all the given playbook's descriptions and names fields and if a description or a name field
        contains the word incident / incidents (without the wrapper), then replace it with alert / alerts just in case
        of XSIAM Marketplace.
        In any case (for all Marketplaces) remove the wrapper (<-incident-> to incident, <-incidents-> to incidents).
        Args:
            data: content item data
            supported_marketplaces: list of the marketplaces this content item supports.
            current_marketplace: Marketplace.

        Returns: A (possibly) modified content item data

        """

        data = prepare_descriptions_and_names(data, current_marketplace)

        if current_marketplace == MarketplaceVersions.MarketplaceV2 and MarketplaceVersions.MarketplaceV2 in supported_marketplaces\
                and len(supported_marketplaces) > 1:
            data = prepare_playbook_access_fields(data)

        return data

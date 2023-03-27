import logging
from demisto_sdk.commands.prepare_content.preparers.incident_to_alert import prepare_descriptions_and_names

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")


class MarketplaceIncidentToAlertPlaybooksPreparer:
    @staticmethod
    def prepare(
        data: dict,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> dict:
        """
        Iterate over all the given content item descriptions and name fields and if a description or name field contains
        the word incident / incidents, then replace it with alert / alerts in case of XSIAM Marketplace.
        In any case (for all Marketplaces) remove wrapper (<-incident-> to incident, <-incidents-> to incidents).
        Args:
            data: content item data
            marketplace: Marketplace.

        Returns: A (possibly) modified content item data

        """

        data = prepare_descriptions_and_names(data, marketplace)

        return data

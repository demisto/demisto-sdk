import logging

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.prepare_content.preparers.incident_to_alert import (
    prepare_script_access_fields,
    create_wrapper_script,
)

logger = logging.getLogger("demisto-sdk")


class MarketplaceIncidentToAlertScriptsPreparer:
    @staticmethod
    def prepare(data: dict,
                current_marketplace: MarketplaceVersions,
                incident_to_alert: bool) -> tuple:
        """
        For each script iterate over all the given script's descriptions comments ids
        and names fields and if a comment or a description or a name or an id field
        contains the word incident / incidents (without the wrapper),
        then replace it with alert / alerts just in case of XSIAM Marketplace. ( `incident_to_alert` = True )
        In any case (for all Marketplaces) remove the wrapper (<-incident-> to incident, <-incidents-> to incidents).

        Aditionaly
        Args:
            data: content item data
            current_marketplace: the destination marketplace.
            incident_to_alert: A boolean flag that determines whether a new script and a wrapper script should be created.

        Returns:
            Tuple[dict]: A tuple of two scripts, the wrapper script and the modified original script.
        """
        scripts_preparation = []

        # Creating a wrapper script
        if incident_to_alert:
            scripts_preparation.append(create_wrapper_script(data))

        # Handling the incident word in the script
        scripts_preparation.append(prepare_script_access_fields(data, incident_to_alert))
        logging.debug(f"Script preparation {data['name']} completed")

        return tuple(scripts_preparation)

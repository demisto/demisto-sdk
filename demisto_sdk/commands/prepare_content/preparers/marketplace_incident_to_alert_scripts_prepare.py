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
        Checks whether the script needs conversion from incident to alert,

        If so:
            1. Changes the existing script so that incident is converted to alert
               (for example: id: incidentState -> id: alertState),
               the changes are made only under the keys `id`, `name`, `description` and `comment`.

            2. Creates a script that wraps the script that changed.

        Otherwise:
            returns a tuple with the script as is.

        Args:
            data (dict): dictionary of the script.
        Returns:
            Tuple[dict, Optional[dict]]: A tuple of two scripts, the wrapper script and the modified original script.
        """
        scripts_preparation = []

        # Creating a wrapper script
        if incident_to_alert:
            scripts_preparation.append(create_wrapper_script(data))

        # Handling the incident word in the script
        scripts_preparation.append(prepare_script_access_fields(data, incident_to_alert))
        logging.debug(f"Script preparation {data['name']} completed")

        return tuple(scripts_preparation)

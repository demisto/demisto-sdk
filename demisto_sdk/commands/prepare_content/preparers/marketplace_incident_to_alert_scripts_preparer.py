import logging
import copy
from typing import Any, Tuple, Optional
import re
from demisto_sdk.commands.common.constants import MarketplaceVersions
logger = logging.getLogger("demisto-sdk")


# A table for converting incident to alert
NOT_WRAPPED_RE_MAPPING = {
    rf"(?<!<-){key}(?!->)": value
    for key, value in {
        'incident': 'alert',
        'incidents': 'alerts',
        'Incident': 'Alert',
        'Incidents': 'Alerts',
        'INCIDENT': 'ALERT',
        'INCIDENTS': 'ALERTS'
    }.items()
}

WRAPPED_MAPPING = {
    rf"<-{key}->": key
    for key in (
        "incident",
        "incidents",
        "Incident",
        "Incidents",
        "INCIDENT",
        "INCIDENTS",
    )
}

# A table for creating the wrapper script content
WRAPPER_SCRIPT = {
    'python': "register_module_line('<script_name>', 'start', __line__())\n\n" \
              "return demisto.executeCommand('<original_script_name>', demisto.args())\n\n" \
              "register_module_line('<script_name>', 'end', __line__())",
    'javascript': "return executeCommand('<original_script_name>', args)\n"
}

class MarketplaceIncidentToAlertScriptsPreparer:
    @staticmethod
    def prepare(data: dict, marketplace: MarketplaceVersions) -> Tuple[dict, Optional[dict]]:
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
        
        # Checks whether it is necessary to make changes to the script and create a wrapper script
        replace_incident_to_alert: bool = marketplace == MarketplaceVersions.MarketplaceV2

        copy_data = copy.deepcopy(data)
        data = recursive_editing(data, replace_incident_to_alert)
        logging.debug(f"Script preparation {data['name']} completed")

        # Creating a wrapper script
        if (wrapper_script := create_wrapper_script(copy_data)):
            logging.debug(f"Created {wrapper_script['name']} script wrapper to {data['name']} script")
            return wrapper_script, data

        return (data,)


"""
HELPER FUNCTIONS
"""
def replace_(data: str, replace_incident_to_alert: bool = False):
    if replace_incident_to_alert:
        for pattern, replace_with in NOT_WRAPPED_RE_MAPPING.items():
            data = re.sub(pattern, replace_with, data)

    for pattern, replace_with in WRAPPED_MAPPING.items():
            data = re.sub(pattern, replace_with, data)
    return data


def create_wrapper_script(data: dict) -> dict:
    if is_need_wrap(data):
        try:
            data['script'] = WRAPPER_SCRIPT[data['type']].replace(
                '<original_script_name>',
                replace_(data['name'], True)).replace(
                    'script_name',
                    data['name'])
        except Exception as e:
            logging.error(f'Failed to create the wrapper script: {e}')

        return data


def is_need_wrap(data: dict) -> bool:
    for key in NOT_WRAPPED_RE_MAPPING.keys():
        if re.search(key, data['name']):
            return True
    return False


def recursive_editing(data: Any, replace_incident_to_alert: bool = False) -> Any:
    if isinstance(data, list):
        return [recursive_editing(item, replace_incident_to_alert) for item in data]
    if isinstance(data, dict):
        for key in tuple(
            data.keys()
        ):
            value = data[key]
            if isinstance(value, str):
                if key in ('name', 'id', 'comment', 'description'):
                    data[key] = replace_(value, replace_incident_to_alert)
            else:
                data[key] = recursive_editing(value, replace_incident_to_alert)
        return data
    else:
        return data

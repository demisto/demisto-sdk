import logging
import copy
from typing import Any
import re
from demisto_sdk.commands.common.constants import MarketplaceVersions
logger = logging.getLogger("demisto-sdk")

REGISTER_MODULE_LINE = r"register_module_line\('(.+)', (?:'start'|'end'), __line__\(\)\)"

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
    'python': "register_module_line('<script_name>', 'start', __line__())\n\n"
              "return demisto.executeCommand('<original_script_name>', demisto.args())\n\n"
              "register_module_line('<script_name>', 'end', __line__())",
    'javascript': "return executeCommand('<original_script_name>', args)\n"
}


class MarketplaceIncidentToAlertScriptsPreparer:
    @staticmethod
    def prepare(data: dict,
                marketplace: MarketplaceVersions,
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
        scripts_preparation.append(editing_script(data, incident_to_alert))
        logging.debug(f"Script preparation {data['name']} completed")

        return tuple(scripts_preparation)


"""
HELPER FUNCTIONS
"""


def handling_for_incident_word(data: str, incident_to_alert: bool = False):
    if incident_to_alert:
        for pattern, replace_with in NOT_WRAPPED_RE_MAPPING.items():
            data = re.sub(pattern, replace_with, data)

    for pattern, replace_with in WRAPPED_MAPPING.items():
        data = re.sub(pattern, replace_with, data)
    return data


def create_wrapper_script(data: dict) -> dict:

    copy_data = copy.deepcopy(data)
    try:
        copy_data['script'] = WRAPPER_SCRIPT[copy_data['type']].replace(
            '<original_script_name>',
            handling_for_incident_word(copy_data['name'], True)).replace(
                'script_name',
                copy_data['name'])
    except Exception as e:
        logging.error(f'Failed to create the wrapper script: {e}')

    logging.debug(f"Created {copy_data['name']} script wrapper to {data['name']} script")
    return copy_data


def recursive_editing(data: Any, incident_to_alert: bool = False) -> Any:
    if isinstance(data, list):
        return [recursive_editing(item, incident_to_alert) for item in data]
    if isinstance(data, dict):
        for key in tuple(
            data.keys()
        ):
            value = data[key]
            if isinstance(value, str):
                if key in ('name', 'id', 'comment', 'description'):
                    data[key] = handling_for_incident_word(value, incident_to_alert)
            else:
                data[key] = recursive_editing(value, incident_to_alert)
        return data
    else:
        return data


def replace_register_module_line(data: dict):
    new_name = handling_for_incident_word(data['name'])
    for state in ('start', 'end'):
        data['script'] = data['script'].replace(
            f"register_module_line('{data['name']}', '{state}', __line__())",
            f"register_module_line('{new_name}', '{state}', __line__())")

    return data


def editing_script(data: dict, incident_to_alert: bool) -> dict:
    if incident_to_alert:
        data = replace_register_module_line(data)
    return recursive_editing(data, incident_to_alert)

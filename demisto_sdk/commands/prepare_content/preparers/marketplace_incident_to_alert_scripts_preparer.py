import logging
from typing import Any, Dict, Tuple, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")

INCIDENTS_TO_ALERT_REPLACE = {
    'incident': 'alert',
    'incidents': 'alerts',
    'Incident': 'Alert',
    'Incidents': 'Alerts'
}

WRAPPER_SCRIPT = {
    'python': "\nregister_module_line('IncidentState', 'start', __line__())\n\n" \
              f"return demisto.executeCommand(<script_name>, args)\n",
    'javascript': 'return executeCommand(<script_name>, args)\n'
}

class MarketplaceIncidentToAlertScriptsPreparer:
    @staticmethod
    def prepare(data: dict, marketplace: str) -> Tuple[dict, Optional[dict]]:
        if not is_wrap(data):
            return (data,)
        def fix_recursively(data: Any) -> Any:
            if isinstance(data, list):
                return [fix_recursively(item) for item in data]
            if isinstance(data, dict):
                for key in tuple(
                    data.keys()
                ):
                    value = data[key]
                    if isinstance(value, str):
                        print(key, value)
                        if key in ('name', 'id', 'comment', 'description'):
                            data[key] = replace_(value)
                            print(key, data[key])
                    else:
                        data[key] = fix_recursively(value)
                return data
            else:
                return data

        wrapper_script = create_wrapper_script(data.copy())
        if not isinstance(data := fix_recursively(data), dict):
            logger.error(
                ''
            )
        return wrapper_script, data


def replace_(data: str):
    for key in INCIDENTS_TO_ALERT_REPLACE.keys():
        data = data.replace(key, INCIDENTS_TO_ALERT_REPLACE[key])
    return data


def create_wrapper_script(data: dict) -> dict:
    try:
        data['script'] = WRAPPER_SCRIPT[data['type']].replace('<script_name>', replace_(data['name']))
    except:
        logging.error('')
    return data


def is_wrap(data: Any) -> bool:
    if isinstance(data, str):
        if 'incident' in data:
            return True 
    if isinstance(data, list):
        for item in data:
            if is_wrap(item):
                return True
    if isinstance(data, dict):
        for key in data:
            if is_wrap(data[key]):
                return True
    return False
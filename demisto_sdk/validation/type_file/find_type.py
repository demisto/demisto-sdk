from demisto_sdk.commands.common.tools import get_yaml, get_json
from typing import Dict, Tuple, Union


def get_dict_from_file(path: str) -> Tuple[Dict, Union[str, None]]:
    if path:
        if path.endswith('.yml'):
            return get_yaml(path), 'yml'
        elif path.endswith('.json'):
            return get_json(path), 'json'
    return {}, None


def find_type(path: str):
    _dict, file_type = get_dict_from_file(path)
    if file_type == 'yml':
        if 'category' in _dict:
            return 'integration'
        elif 'script' in _dict:
            return 'script'
        elif 'tasks' in _dict:
            return 'playbook'

    elif file_type == 'json':
        if 'widgetType' in _dict:
            return 'widget'
        elif 'reportType' in _dict:
            return 'report'
        elif 'preProcessingScript' in _dict:
            return 'incidenttype'
        elif 'regex' in _dict:
            return 'reputation'
        elif 'mapping' in _dict or 'unclassifiedCases' in _dict:
            return 'classifier'
        elif 'layout' in _dict:
            if 'kind' in _dict or 'typeId' in _dict:
                return 'layout'
            else:
                return 'dashboard'

        elif 'id' in _dict:
            _id = _dict['id'].lower()
            if _id.startswith('incident'):
                return 'incidentfield'
            elif _id.startswith('indicator'):
                return 'indicatorfield'

    return ''

from typing import List
from demisto_sdk.commands.common.git_tools import get_changed_files
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_incidentfields import IncidentFieldJSONFormat
from demisto_sdk.commands.format.update_incidenttype import IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatorfields import IndicatorFieldJSONFormat
from demisto_sdk.commands.format.update_indicatortype import IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_layout import LayoutJSONFormat
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_classifier import ClassifierJSONFormat

import os
from demisto_sdk.commands.common.tools import print_error, find_type, get_files_in_dir
from demisto_sdk.commands.common.constants import SCHEMAS_PATH


FILE_TYPE_AND_LINKED_CLASS = {
    'integration': IntegrationYMLFormat,
    'script': ScriptYMLFormat,
    'playbook': PlaybookYMLFormat,
    'incidentfield': IncidentFieldJSONFormat,
    'incidenttype': IncidentTypesJSONFormat,
    'indicatorfield': IndicatorFieldJSONFormat,
    'reputation': IndicatorTypeJSONFormat,
    'layout': LayoutJSONFormat,
    'dashboard': DashboardJSONFormat,
    'classifier': ClassifierJSONFormat,
}


def format_manager(input=None, output=None, from_version=None):
    """
    Format_manager is a function that activated format command on different type of files.
    Args:
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        output: (str) The path to save the formatted file to.
    Returns:
        int 0 in case of success 1 otherwise
    """
    if input:
        files = get_files_in_dir(input, ("json", "yml"))
    else:
        files = [file['name'] for file in get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')]
    error_list = []

    if files:
        for file in files:
            file_path = file.replace('\\', '/')
            file_type = find_type(file_path)
            if file_type:
                error_list.extend(run_format_on_file(input=file_path, file_type=file_type,
                                                     from_version=from_version, output=output))
    else:
        error_list.append(f'Failed to format {input}' + "No such file or directory")

    if error_list:
        print_error('\n'.join(error_list))
        return 1
    return 0


def run_format_on_file(input: str, file_type: str, from_version: str, **kwargs) -> List[str]:
    """Run the relevent format of file type.
    Args:
        input (str): The input file path.
        file_type (str): The type of input file
        from_version (str): The fromVersion value that was set by User.
        old_file (bool): Whether the file is a added file = new or a modified file = old.
    Returns:
        Error List of failures.
    """
    error_list = []
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, '{}.yml'.format(file_type)))
    res = FILE_TYPE_AND_LINKED_CLASS[file_type](input=input, path=schema_path,
                                                from_version=from_version, **kwargs).format_file()
    if res:
        error_list.append(f'Failed to format {input}.' + file_type)
    return error_list

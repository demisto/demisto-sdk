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
import os
from demisto_sdk.commands.common.tools import print_error, find_type, get_files_in_dir, get_remote_file

SCHEMAS_PATH = "schemas"

file_type_and_linked_class = {
    'integration': IntegrationYMLFormat,
    'script': ScriptYMLFormat,
    'playbook': PlaybookYMLFormat,
    'incidentfield': IncidentFieldJSONFormat,
    'incidenttype': IncidentTypesJSONFormat,
    'indicatorfield': IndicatorFieldJSONFormat,
    'reputation': IndicatorTypeJSONFormat,
    'layout': LayoutJSONFormat,
    'dashboard': DashboardJSONFormat,
}


def format_manager(use_git=False, input=None, from_version=None, **kwargs):
    """
    Format_manager is a function that activated format command on different type of files.
    Args:
        use_git: (bool) in case True use git to format every changed file.
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        **kwargs: other data like out_file and so ...

    Returns:
        int 0 in case of success 1 otherwise
    """

    if input:
        error_list = []
        file_type = find_type(input)
        if file_type:
            #  if input is a directory with a specific file
            old_file = get_remote_file(input)
            error_list.extend(run_format_on_file(input=input, file_type=file_type, old_file=old_file,
                                                 from_version=from_version, **kwargs))
        else:
            files = get_files_in_dir(input, ["json", "yml"])
            if files:
                #  if input is a directory with relevent files
                for file in files:
                    file_path = file.replace('\\', '/')
                    file_type = find_type(file_path)
                    old_file = get_remote_file(input)
                    if file_type:
                        error_list.extend(run_format_on_file(input=input, file_type=file_type, old_file=old_file,
                                                             from_version=from_version, **kwargs))
            else:
                error_list.append(f'Failed to format {input}.' + file_type + "No such file or directory")
        if error_list:
            print_error('\n'.join(error_list))
            return 1
    elif use_git:
        error_list = []
        files = get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')
        for _file in files:
            _old_file = _file['status'] == 'M'
            _file = _file['name']
            file_type = find_type(_file)
            if file_type:
                error_list.extend(run_format_on_file(input=_file, file_type=file_type, old_file=_old_file,
                                                     from_version=from_version, **kwargs))
        if error_list:
            print_error('\n'.join(error_list))
            return 1
    return 0


def run_format_on_file(input, file_type, from_version, old_file=False, **kwargs):
    error_list = []
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, '{}.yml'.format(file_type)))
    res = file_type_and_linked_class[file_type](input=input, old_file=old_file, path=schema_path,
                                                from_version=from_version, **kwargs).format_file()
    if res:
        error_list.append(f'Failed to format {input}.' + file_type)
    return error_list

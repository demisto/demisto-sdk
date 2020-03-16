
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

from demisto_sdk.commands.common.tools import print_error, find_pack_files, find_type


def format_manager(use_git=False, input=None, from_version=None, **kwargs):
    """

    Args:
        use_git: (bool) in case True use git to format every changed file.
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        **kwargs: other data like out_file and so ...

    Returns:
        int 0 in case of success 1 otherwise
    """
    file_type = find_type(input)

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

    if input:
        error_list = []
        if "Pack" in input:
            error_list = []
            format_files = find_pack_files(input)
        else:
            format_files = [input]
        for file in format_files:
            file_path = file.replace('\\', '/')
            file_type = find_type(file_path)
            if file_type:
                res = file_type_and_linked_class[file_type](input=file_path, old_file=False) \
                    .update_fromVersion(from_version=from_version)
                if res:
                    error_list.append(f'Failed to format {file_path}.' + file_type)

    elif file_type in file_type_and_linked_class:
        format_object = file_type_and_linked_class[file_type](input, **kwargs)
        return format_object.format_file()

    elif use_git:
        error_list = []
        files = get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')
        for _file in files:
            _old_file = _file['status'] == 'M'
            _file = _file['name']
            file_type = find_type(_file)
            if file_type:
                res = file_type_and_linked_class[file_type](input=_file, old_file=_old_file).format_file()
                if res:
                    error_list.append(f'Failed to format {_file}.' + file_type)

        if error_list:
            print_error('\n'.join(error_list))
            return 1

    return 0

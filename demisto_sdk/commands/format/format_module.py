from demisto_sdk.commands.common.constants import YML_ALL_INTEGRATION_REGEXES, YML_ALL_SCRIPTS_REGEXES, \
    YML_ALL_PLAYBOOKS_REGEX, JSON_ALL_INCIDENT_FIELD_REGEXES, JSON_ALL_INCIDENT_TYPES_REGEXES, \
    JSON_ALL_INDICATOR_FIELDS_REGEXES, \
    JSON_ALL_MISC_REGEXES, JSON_ALL_LAYOUT_REGEXES, JSON_ALL_DASHBOARDS_REGEXES

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

from demisto_sdk.commands.common.update_id_set import checked_type
from demisto_sdk.commands.common.tools import print_error


def format_manager(use_git=False, file_type=None, **kwargs):
    """

    Args:
        use_git: (bool) in case True use git to format every changed file.
        file_type: (str) in case of known source file need for filtering to the correct class.
        **kwargs: other data like out_file and so ...

    Returns:
        int 0 in case of success 1 otherwise
    """
    file_type_and_linked_class = {
        'integration': IntegrationYMLFormat,
        'script': ScriptYMLFormat,
        'playbook': PlaybookYMLFormat,
        'incidentfield': IncidentFieldJSONFormat,
        'incidenttype': IncidentTypesJSONFormat,
        'indicatorfield': IndicatorFieldJSONFormat,
        'indicatortype': IndicatorTypeJSONFormat,
        'layout': LayoutJSONFormat,
        'dashboard': DashboardJSONFormat,
    }

    if file_type in file_type_and_linked_class:
        format_object = file_type_and_linked_class[file_type](**kwargs)
        return format_object.format_file()

    elif use_git:
        error_list = []
        files = get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')
        for _file in files:
            _old_file = _file['status'] == 'M'
            _file = _file['name']
            file_type = 'integration' if checked_type(_file, YML_ALL_INTEGRATION_REGEXES) \
                else 'script' if checked_type(_file, YML_ALL_SCRIPTS_REGEXES) \
                else 'playbook' if checked_type(_file, YML_ALL_PLAYBOOKS_REGEX) \
                else 'incidentfield' if checked_type(_file, JSON_ALL_INCIDENT_FIELD_REGEXES) \
                else 'incidenttype' if checked_type(_file, JSON_ALL_INCIDENT_TYPES_REGEXES) \
                else 'indicatorfield' if checked_type(_file, JSON_ALL_INDICATOR_FIELDS_REGEXES) \
                else 'indicatortype' if checked_type(_file, JSON_ALL_MISC_REGEXES) \
                else 'layout' if checked_type(_file, JSON_ALL_LAYOUT_REGEXES) \
                else 'dashboard' if checked_type(_file, JSON_ALL_DASHBOARDS_REGEXES) \
                else None
            if file_type:
                res = file_type_and_linked_class[file_type](source_file=_file, old_file=_old_file).format_file()
                if res:
                    error_list.append(f'Failed to format {_file}.' + file_type)

        if error_list:
            print_error('\n'.join(error_list))
            return 1

    return 0

from demisto_sdk.commands.common.constants import YML_ALL_INTEGRATION_REGEXES, YML_ALL_SCRIPTS_REGEXES,\
    YML_ALL_PLAYBOOKS_REGEX
from demisto_sdk.commands.common.git_tools import get_changed_files
from demisto_sdk.commands.format.update_playbook import PlaybookYMLFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
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
        'playbook': PlaybookYMLFormat
    }
    if file_type in file_type_and_linked_class:
        format_object = file_type_and_linked_class[file_type](**kwargs)
        return format_object.format_file()

    elif use_git:
        error_list = []
        files = get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')
        for _file in files:
            _file = _file['name']
            file_type = 'integration' if checked_type(_file, YML_ALL_INTEGRATION_REGEXES) \
                else 'script' if checked_type(_file, YML_ALL_SCRIPTS_REGEXES) \
                else 'playbook' if checked_type(_file, YML_ALL_PLAYBOOKS_REGEX) \
                else None
            if file_type:
                res = file_type_and_linked_class[file_type](source_file=_file).format_file()
                if res:
                    error_list.append(f'Failed to format {_file}.' + file_type)

        if error_list:
            print_error('\n'.join(error_list))
            return 1

    return 0

from demisto_sdk.common.constants import YML_ALL_INTEGRATION_REGEXES, YML_ALL_SCRIPTS_REGEXES, YML_ALL_PLAYBOOKS_REGEX
from demisto_sdk.git_tools import Git
from demisto_sdk.yaml_tools.update_playbook import PlaybookYMLFormat
from demisto_sdk.yaml_tools.update_script import ScriptYMLFormat
from demisto_sdk.yaml_tools.update_integration import IntegrationYMLFormat
from demisto_sdk.common.scripts.update_id_set import checked_type
from demisto_sdk.common.tools import print_error


def format_command(kwargs):
    file_type_and_linked_class = {
        'integration': IntegrationYMLFormat,
        'script': ScriptYMLFormat,
        'playbook': PlaybookYMLFormat
    }
    if kwargs.get('file_type') in file_type_and_linked_class:
        format_object = file_type_and_linked_class[kwargs['file_type']](**kwargs)
        return format_object.format_file()

    elif kwargs.get('use_git'):
        error_list = []
        files = Git.get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')
        for _file in files:
            _file = _file['name']
            file_type = 'integration' if checked_type(_file, YML_ALL_INTEGRATION_REGEXES) \
                else 'script' if checked_type(_file, YML_ALL_SCRIPTS_REGEXES) \
                else 'playbook' if checked_type(_file, YML_ALL_PLAYBOOKS_REGEX) \
                else None
            if file_type:
                res = file_type_and_linked_class[file_type](source_file=_file).format_file()
                if res:
                    error_list.append(f'Failed to format {_file}.')

        if error_list:
            print_error('\n'.join(error_list))
            return 1

    return 0

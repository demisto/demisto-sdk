import os
from typing import List, Tuple

from demisto_sdk.commands.common.git_tools import get_changed_files
from demisto_sdk.commands.common.tools import (find_type, get_files_in_dir,
                                               print_error, print_success,
                                               print_warning)
from demisto_sdk.commands.format.format_constants import SCHEMAS_PATH
from demisto_sdk.commands.format.update_classifier import (
    ClassifierJSONFormat, OldClassifierJSONFormat)
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_incidentfields import \
    IncidentFieldJSONFormat
from demisto_sdk.commands.format.update_incidenttype import \
    IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatorfields import \
    IndicatorFieldJSONFormat
from demisto_sdk.commands.format.update_indicatortype import \
    IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_layout import (
    LayoutJSONFormat, LayoutsContainerJSONFormat)
from demisto_sdk.commands.format.update_mapper import MapperJSONFormat
from demisto_sdk.commands.format.update_playbook import (PlaybookYMLFormat,
                                                         TestPlaybookYMLFormat)
from demisto_sdk.commands.format.update_pythonfile import PythonFileFormat
from demisto_sdk.commands.format.update_report import ReportJSONFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_widget import WidgetJSONFormat

FILE_TYPE_AND_LINKED_CLASS = {
    'integration': IntegrationYMLFormat,
    'script': ScriptYMLFormat,
    'playbook': PlaybookYMLFormat,
    'testplaybook': TestPlaybookYMLFormat,
    'incidentfield': IncidentFieldJSONFormat,
    'incidenttype': IncidentTypesJSONFormat,
    'indicatorfield': IndicatorFieldJSONFormat,
    'reputation': IndicatorTypeJSONFormat,
    'layout': LayoutJSONFormat,
    'layoutscontainer': LayoutsContainerJSONFormat,
    'dashboard': DashboardJSONFormat,
    'classifier': ClassifierJSONFormat,
    'classifier_5_9_9': OldClassifierJSONFormat,
    'mapper': MapperJSONFormat,
    'widget': WidgetJSONFormat,
    'pythonfile': PythonFileFormat,
    'report': ReportJSONFormat,
}
UNFORMATTED_FILES = ['canvas-context-connections',
                     'readme',
                     'releasenotes',
                     'description',
                     'changelog',
                     'image',
                     'javascriptfile',
                     'powershellfile']

VALIDATE_RES_SKIPPED_CODE = 2
VALIDATE_RES_FAILED_CODE = 3


def format_manager(input: str = None, output: str = None, from_version: str = '', no_validate: bool = None):
    """
    Format_manager is a function that activated format command on different type of files.
    Args:
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        output: (str) The path to save the formatted file to.
        no_validate (flag): Whether the user specifies not to run validate after format.
    Returns:
        int 0 in case of success 1 otherwise
    """
    if input:
        files = get_files_in_dir(input, ['json', 'yml', 'py'])
    else:
        files = [file['name'] for file in
                 get_changed_files(filter_results=lambda _file: not _file.pop('status') == 'D')]
    if output and not output.endswith(('yml', 'json', 'py')):
        raise Exception("The given output path is not a specific file path.\n"
                        "Only file path can be a output path.  Please specify a correct output.")

    log_list = []
    error_list = []
    if files:
        for file in files:
            file_path = file.replace('\\', '/')
            file_type = find_type(file_path)
            if file_type and file_type.value not in UNFORMATTED_FILES:
                file_type = file_type.value
                info_res, err_res, skip_res = run_format_on_file(input=file_path, file_type=file_type,
                                                                 from_version=from_version, output=output,
                                                                 no_validate=no_validate)
                if err_res:
                    error_list.append("err_res")
                if err_res:
                    log_list.extend([(err_res, print_error)])
                if info_res:
                    log_list.extend([(info_res, print_success)])
                if skip_res:
                    log_list.extend([(skip_res, print_warning)])

    else:
        log_list.append(([f'Failed format file {input}.' + "No such file or directory"], print_error))

    if error_list:
        for string, print_func in log_list:
            print_func('\n'.join(string))
        return 1

    for string, print_func in log_list:
        print_func('\n'.join(string))
    return 0


def run_format_on_file(input: str, file_type: str, from_version: str, **kwargs) -> \
        Tuple[List[str], List[str], List[str]]:
    """Run the relevent format of file type.
    Args:
        input (str): The input file path.
        file_type (str): The type of input file
        from_version (str): The fromVersion value that was set by User.
        old_file (bool): Whether the file is a added file = new or a modified file = old.
    Returns:
        List of Success , List of Error.
    """
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, '{}.yml'.format(file_type)))
    UpdateObject = FILE_TYPE_AND_LINKED_CLASS[file_type](input=input, path=schema_path,
                                                         from_version=from_version,
                                                         **kwargs)
    format_res, validate_res = UpdateObject.format_file()  # type: ignore
    return logger(input, format_res, validate_res)


def logger(input: str, format_res: int, validate_res: int) -> Tuple[List[str], List[str], List[str]]:
    info_list = []
    error_list = []
    skipped_list = []
    if format_res and validate_res:
        if validate_res == VALIDATE_RES_SKIPPED_CODE:
            error_list.append(f'Format Status   on file: {input} - Failed')
            skipped_list.append(f'Validate Status on file: {input} - Skipped')
        elif validate_res == VALIDATE_RES_FAILED_CODE:
            error_list.append(f'Format Status   on file: {input} - Failed')
        else:
            error_list.append(f'Format Status   on file: {input} - Failed')
            error_list.append(f'Validate Status on file: {input} - Failed')
    elif format_res and not validate_res:
        error_list.append(f'Format Status   on file: {input} - Failed')
        info_list.append(f'Validate Status on file: {input} - Success')
    elif not format_res and validate_res:
        if validate_res == VALIDATE_RES_SKIPPED_CODE:
            info_list.append(f'Format Status   on file: {input} - Success')
            skipped_list.append(f'Validate Status on file: {input} - Skipped')
        elif validate_res == VALIDATE_RES_FAILED_CODE:
            info_list.append(f'Format Status   on file: {input} - Success')
        else:
            info_list.append(f'Format Status   on file: {input} - Success')
            error_list.append(f'Validate Status on file: {input} - Failed')
    elif not format_res and not validate_res:
        info_list.append(f'Format Status   on file: {input} - Success')
        info_list.append(f'Validate Status on file: {input} - Success')
    return info_list, error_list, skipped_list

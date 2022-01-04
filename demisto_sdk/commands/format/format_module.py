import os
from pathlib import Path
from typing import Dict, List, Tuple

import click

from demisto_sdk.commands.common.constants import (JOB,
                                                   TESTS_AND_DOC_DIRECTORIES)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import (find_type, get_files_in_dir,
                                               print_error, print_success,
                                               print_warning)
from demisto_sdk.commands.format.format_constants import SCHEMAS_PATH
from demisto_sdk.commands.format.update_classifier import (
    ClassifierJSONFormat, OldClassifierJSONFormat)
from demisto_sdk.commands.format.update_connection import ConnectionJSONFormat
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_description import DescriptionFormat
from demisto_sdk.commands.format.update_genericdefinition import \
    GenericDefinitionJSONFormat
from demisto_sdk.commands.format.update_genericfield import \
    GenericFieldJSONFormat
from demisto_sdk.commands.format.update_genericmodule import \
    GenericModuleJSONFormat
from demisto_sdk.commands.format.update_generictype import \
    GenericTypeJSONFormat
from demisto_sdk.commands.format.update_incidentfields import \
    IncidentFieldJSONFormat
from demisto_sdk.commands.format.update_incidenttype import \
    IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatorfields import \
    IndicatorFieldJSONFormat
from demisto_sdk.commands.format.update_indicatortype import \
    IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_job import JobJSONFormat
from demisto_sdk.commands.format.update_layout import LayoutBaseFormat
from demisto_sdk.commands.format.update_lists import ListsFormat
from demisto_sdk.commands.format.update_mapper import MapperJSONFormat
from demisto_sdk.commands.format.update_playbook import (PlaybookYMLFormat,
                                                         TestPlaybookYMLFormat)
from demisto_sdk.commands.format.update_pre_process_rules import \
    PreProcessRulesFormat
from demisto_sdk.commands.format.update_pythonfile import PythonFileFormat
from demisto_sdk.commands.format.update_report import ReportJSONFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_widget import WidgetJSONFormat
from demisto_sdk.commands.lint.commands_builder import excluded_files

FILE_TYPE_AND_LINKED_CLASS = {
    'integration': IntegrationYMLFormat,
    'script': ScriptYMLFormat,
    'playbook': PlaybookYMLFormat,
    'testplaybook': TestPlaybookYMLFormat,
    'incidentfield': IncidentFieldJSONFormat,
    'incidenttype': IncidentTypesJSONFormat,
    'indicatorfield': IndicatorFieldJSONFormat,
    'reputation': IndicatorTypeJSONFormat,
    'layout': LayoutBaseFormat,
    'layoutscontainer': LayoutBaseFormat,
    'pre-process-rule': PreProcessRulesFormat,
    'list': ListsFormat,
    'dashboard': DashboardJSONFormat,
    'classifier': ClassifierJSONFormat,
    'classifier_5_9_9': OldClassifierJSONFormat,
    'mapper': MapperJSONFormat,
    'widget': WidgetJSONFormat,
    'pythonfile': PythonFileFormat,
    'report': ReportJSONFormat,
    'testscript': ScriptYMLFormat,
    'canvas-context-connections': ConnectionJSONFormat,
    'description': DescriptionFormat,
    'genericfield': GenericFieldJSONFormat,
    'generictype': GenericTypeJSONFormat,
    'genericmodule': GenericModuleJSONFormat,
    'genericdefinition': GenericDefinitionJSONFormat,
    JOB: JobJSONFormat
}

UNFORMATTED_FILES = ['readme',
                     'releasenotes',
                     'changelog',
                     'image',
                     'javascriptfile',
                     'powershellfile',
                     'doc_image',
                     'author_image'
                     ]

VALIDATE_RES_SKIPPED_CODE = 2
VALIDATE_RES_FAILED_CODE = 3

CONTENT_ENTITY_IDS_TO_UPDATE: Dict = {}


def format_manager(input: str = None,
                   output: str = None,
                   from_version: str = '',
                   no_validate: bool = False,
                   verbose: bool = False,
                   update_docker: bool = False,
                   assume_yes: bool = False,
                   deprecate: bool = False,
                   use_git: bool = False,
                   prev_ver: str = None,
                   include_untracked: bool = False,
                   add_tests: bool = None):
    """
    Format_manager is a function that activated format command on different type of files.
    Args:
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        output: (str) The path to save the formatted file to.
        no_validate (flag): Whether the user specifies not to run validate after format.
        verbose (bool): Whether to print verbose logs or not
        update_docker (flag): Whether to update the docker image.
        assume_yes (bool): Whether to assume "yes" as answer to all prompts and run non-interactively
        deprecate (bool): Whether to deprecate the entity
        use_git (bool): Use git to automatically recognize which files changed and run format on them
        prev_ver (str): Against which branch should the difference be recognized
        include_untracked (bool): Whether to include untracked files when checking against git
        add_tests (bool): Whether to exclude tests automatically.
    Returns:
        int 0 in case of success 1 otherwise
    """

    prev_ver = prev_ver if prev_ver else 'demisto/master'
    supported_file_types = ['json', 'yml', 'py', 'md']
    use_git = use_git or not input

    print(f'This is the input: {input} and use git: {use_git}')
    if input:
        files = get_files_in_dir(input, supported_file_types)

    elif use_git:
        files = get_files_to_format_from_git(supported_file_types, prev_ver, include_untracked)

    print(f'This is the files: {files}')

    if output and not output.endswith(('yml', 'json', 'py')):
        raise Exception("The given output path is not a specific file path.\n"
                        "Only file path can be a output path.  Please specify a correct output.")

    log_list = []
    error_list: List[Tuple[int, int]] = []
    if files:
        format_excluded_file = excluded_files + ['pack_metadata.json']
        for file in files:
            file_path = file.replace('\\', '/')
            file_type = find_type(file_path)

            current_excluded_files = format_excluded_file[:]
            dirname = os.path.dirname(file_path)
            if dirname.endswith('CommonServerPython'):
                current_excluded_files.remove('CommonServerPython.py')
            if os.path.basename(file_path) in current_excluded_files:
                continue
            if any(test_dir in str(dirname) for test_dir in TESTS_AND_DOC_DIRECTORIES):
                continue

            if file_type and file_type.value not in UNFORMATTED_FILES:
                file_type = file_type.value
                info_res, err_res, skip_res = run_format_on_file(input=file_path,
                                                                 file_type=file_type,
                                                                 from_version=from_version,
                                                                 output=output,
                                                                 no_validate=no_validate,
                                                                 verbose=verbose,
                                                                 update_docker=update_docker,
                                                                 assume_yes=assume_yes,
                                                                 deprecate=deprecate,
                                                                 add_tests=add_tests)
                if err_res:
                    log_list.extend([(err_res, print_error)])
                if info_res:
                    log_list.extend([(info_res, print_success)])
                if skip_res:
                    log_list.extend([(skip_res, print_warning)])
            elif file_type:
                log_list.append(([f"Ignoring format for {file_path} as {file_type.value} is currently not "
                                  f"supported by format command"], print_warning))
            else:
                log_list.append(([f"Was unable to identify the file type for the following file: {file_path}"],
                                 print_error))

        update_content_entity_ids(files, verbose)

    else:
        if not use_git:
            log_list.append(([f'Failed format file {input}.' + "No such file or directory"], print_error))
        return 1

    print('')  # Just adding a new line before summary
    for string, print_func in log_list:
        print_func('\n'.join(string))

    if error_list:
        return 1
    return 0


def get_files_to_format_from_git(supported_file_types: List[str], prev_ver: str, include_untracked: bool) -> List[str]:
    """Get the files to format from git.

    Args:
        supported_file_types(list): File extensions which are supported by format
        prev_ver(str): The branch name or commit hash to compare with
        include_untracked(bool): Whether to include untracked files

    Returns:
        list. a list of all the files that should be formatted.
    """
    git_util = GitUtil()
    all_changed_files = git_util.get_all_changed_files(prev_ver=prev_ver, include_untracked=include_untracked)

    filtered_files = []
    for file_path in all_changed_files:
        str_file_path = str(file_path)

        # get the file extension without the '.'
        file_extension = os.path.splitext(str_file_path)[1][1:]
        if file_extension in supported_file_types and os.path.exists(str_file_path):
            filtered_files.append(str_file_path)

    if filtered_files:
        detected_files_string = "\n".join(filtered_files)
        click.secho(f'Found the following files to format:\n{detected_files_string}', fg='bright_cyan')

    else:
        click.secho('Did not find any files to format', fg='bright_red')

    return filtered_files


def update_content_entity_ids(files: List[str], verbose: bool):
    """Update the changed content entity ids in the files.
    Args:
        files (list): a list of files in which to update the content ids.
        verbose (bool): whether to print

    """
    if not CONTENT_ENTITY_IDS_TO_UPDATE:
        return

    if verbose:
        click.echo(f'Collected content entities IDs to update:\n{CONTENT_ENTITY_IDS_TO_UPDATE}\n'
                   f'Going over files to update these IDs in other files...')
    for file in files:
        file_path = str(Path(file))
        if verbose:
            click.echo(f'Processing file {file_path} to check for content entities IDs to update')
        with open(file_path, 'r+') as f:
            file_content = f.read()
            for id_to_replace, updated_id in CONTENT_ENTITY_IDS_TO_UPDATE.items():
                file_content = file_content.replace(id_to_replace, updated_id)
            f.seek(0)
            f.write(file_content)
            f.truncate()


def run_format_on_file(input: str, file_type: str, from_version: str, **kwargs) -> \
        Tuple[List[str], List[str], List[str]]:
    """Run the relevent format of file type.
    Args:
        input (str): The input file path.
        file_type (str): The type of input file
        from_version (str): The fromVersion value that was set by User.
    Returns:
        List of Success , List of Error.
    """

    if file_type == 'betaintegration':
        file_type = 'integration'
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, '{}.yml'.format(file_type)))
    if file_type not in ('integration', 'script') and 'update_docker' in kwargs:
        # non code formatters don't support update_docker param. remove it
        del kwargs['update_docker']
    if file_type not in ('integration', 'playbook', 'script') and 'add_tests' in kwargs:
        # adding tests is relevant only for integrations, playbooks and scripts.
        del kwargs['add_tests']
    update_object = FILE_TYPE_AND_LINKED_CLASS[file_type](input=input, path=schema_path,
                                                          from_version=from_version,
                                                          **kwargs)
    format_res, validate_res = update_object.format_file()  # type: ignore
    CONTENT_ENTITY_IDS_TO_UPDATE.update(update_object.updated_ids)
    return logger(input, format_res, validate_res)


def logger(
        input: str,
        format_res: int,
        validate_res: int,
) -> Tuple[List[str], List[str], List[str]]:
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
            error_list.append(f'For more information run: `demisto-sdk validate -i {input}`')
    elif not format_res and not validate_res:
        info_list.append(f'Format Status   on file: {input} - Success')
        info_list.append(f'Validate Status on file: {input} - Success')
    return info_list, error_list, skipped_list

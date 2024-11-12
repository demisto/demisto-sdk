import os
from pathlib import Path
from typing import Dict, List, Tuple, Union

import typer

from demisto_sdk.commands.common.constants import (
    JOB,
    TESTS_AND_DOC_DIRECTORIES,
    FileType,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import find_type, get_files_in_dir
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.format.format_constants import (
    SCHEMAS_PATH,
    SKIP_FORMATTING_DIRS,
    SKIP_FORMATTING_FILES,
    UNSKIP_FORMATTING_FILES,
)
from demisto_sdk.commands.format.update_classifier import (
    ClassifierJSONFormat,
    OldClassifierJSONFormat,
)
from demisto_sdk.commands.format.update_correlation_rule import CorrelationRuleYMLFormat
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_description import DescriptionFormat
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_genericdefinition import (
    GenericDefinitionJSONFormat,
)
from demisto_sdk.commands.format.update_genericfield import GenericFieldJSONFormat
from demisto_sdk.commands.format.update_genericmodule import GenericModuleJSONFormat
from demisto_sdk.commands.format.update_generictype import GenericTypeJSONFormat
from demisto_sdk.commands.format.update_incidentfields import IncidentFieldJSONFormat
from demisto_sdk.commands.format.update_incidenttype import IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatorfields import IndicatorFieldJSONFormat
from demisto_sdk.commands.format.update_indicatortype import IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_job import JobJSONFormat
from demisto_sdk.commands.format.update_layout import LayoutBaseFormat
from demisto_sdk.commands.format.update_lists import ListsFormat
from demisto_sdk.commands.format.update_mapper import MapperJSONFormat
from demisto_sdk.commands.format.update_pack_metadata import PackMetadataJsonFormat
from demisto_sdk.commands.format.update_playbook import (
    PlaybookYMLFormat,
    TestPlaybookYMLFormat,
)
from demisto_sdk.commands.format.update_pre_process_rules import PreProcessRulesFormat
from demisto_sdk.commands.format.update_pythonfile import PythonFileFormat
from demisto_sdk.commands.format.update_readme import ReadmeFormat
from demisto_sdk.commands.format.update_report import ReportJSONFormat
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.commands.format.update_widget import WidgetJSONFormat

FILE_TYPE_AND_LINKED_CLASS = {
    "integration": IntegrationYMLFormat,
    "script": ScriptYMLFormat,
    "playbook": PlaybookYMLFormat,
    "testplaybook": TestPlaybookYMLFormat,
    "incidentfield": IncidentFieldJSONFormat,
    "incidenttype": IncidentTypesJSONFormat,
    "indicatorfield": IndicatorFieldJSONFormat,
    "reputation": IndicatorTypeJSONFormat,
    "layout": LayoutBaseFormat,
    "layoutscontainer": LayoutBaseFormat,
    "pre-process-rule": PreProcessRulesFormat,
    "list": ListsFormat,
    "dashboard": DashboardJSONFormat,
    "classifier": ClassifierJSONFormat,
    "classifier_5_9_9": OldClassifierJSONFormat,
    "mapper": MapperJSONFormat,
    "widget": WidgetJSONFormat,
    "pythonfile": PythonFileFormat,
    "report": ReportJSONFormat,
    "testscript": ScriptYMLFormat,
    "description": DescriptionFormat,
    "genericfield": GenericFieldJSONFormat,
    "generictype": GenericTypeJSONFormat,
    "genericmodule": GenericModuleJSONFormat,
    "genericdefinition": GenericDefinitionJSONFormat,
    JOB: JobJSONFormat,
    "readme": ReadmeFormat,
    "metadata": PackMetadataJsonFormat,
    "correlationrule": CorrelationRuleYMLFormat,
    "xsiamdashboard": BaseUpdateJSON,
    "xsiamreport": BaseUpdateJSON,
    "modelingrule": BaseUpdateYML,
    "modelingruleschema": BaseUpdateJSON,
    "parsingrule": BaseUpdateYML,
    "trigger": BaseUpdateJSON,
    "xdrctemplate": BaseUpdateJSON,
    "xdrctemplateyml": BaseUpdateYML,
    "layoutrule": BaseUpdateJSON,
    "assetsmodelingrule": BaseUpdateYML,
    "assetsmodelingruleschema": BaseUpdateJSON,
    "casefield": BaseUpdateJSON,
    "caselayout": LayoutBaseFormat,
    "caselayoutrule": BaseUpdateJSON,
}

UNFORMATTED_FILES = [
    "releasenotes",
    "changelog",
    "image",
    "javascriptfile",
    "powershellfile",
    "doc_image",
    "author_image",
]

VALIDATE_RES_SKIPPED_CODE = 2
VALIDATE_RES_FAILED_CODE = 3

CONTENT_ENTITY_IDS_TO_UPDATE: Dict = {}

# The content items that use the graph in format
CONTENT_ITEMS_WITH_GRAPH = [
    FileType.INCIDENT_FIELD.value,
    FileType.LAYOUTS_CONTAINER.value,
    FileType.LAYOUT.value,
    FileType.MAPPER.value,
]


def format_manager(
    input: str = None,
    output: str = None,
    from_version: str = "",
    no_validate: bool = False,
    update_docker: bool = False,
    assume_answer: Union[bool, None] = None,
    deprecate: bool = False,
    use_git: bool = False,
    prev_ver: str = None,
    include_untracked: bool = False,
    add_tests: bool = None,
    interactive: bool = True,
    id_set_path: str = None,
    clear_cache: bool = False,
    use_graph: bool = True,
):
    """
    Format_manager is a function that activated format command on different type of files.
    Args:
        input: (str) The path of the specific file.
        from_version: (str) in case of specific value for from_version that needs to be updated.
        output: (str) The path to save the formatted file to.
        no_validate (flag): Whether the user specifies not to run validate after format.
        update_docker (flag): Whether to update the docker image.
        assume_answer (bool | None): Whether to assume "yes" or "no" as answer to all prompts and run non-interactively
        deprecate (bool): Whether to deprecate the entity
        use_git (bool): Use git to automatically recognize which files changed and run format on them
        prev_ver (str): Against which branch should the difference be recognized
        include_untracked (bool): Whether to include untracked files when checking against git
        interactive (bool): Whether to run the format interactively or not (usually for contribution management)
        add_tests (bool): Whether to exclude tests automatically.
        id_set_path (str): The path of the id_set.json file.
        clear_cache (bool): wether to clear the cache
        use_graph (bool): wheter to use the graph in format
    Returns:
        int 0 in case of success 1 otherwise
    """

    if id_set_path:
        logger.error("The --id-set-path argument is deprecated.")

    prev_ver = prev_ver if prev_ver else "demisto/master"
    supported_file_types = ["json", "yml", "py", "md"]
    use_git = use_git or not input

    if input:
        files = []
        for i in input.split(","):
            files.extend(
                get_files_in_dir(
                    project_dir=i,
                    file_endings=supported_file_types,
                    exclude_list=SKIP_FORMATTING_DIRS + TESTS_AND_DOC_DIRECTORIES,
                )
            )

    elif use_git:
        files = get_files_to_format_from_git(
            supported_file_types, prev_ver, include_untracked
        )

    if output and not output.endswith(("yml", "json", "py")):
        raise Exception(
            "The given output path is not a specific file path.\n"
            "Only file path can be a output path.  Please specify a correct output."
        )
    if output and input and "," in input:
        raise Exception(
            "Cannot use the output argument when provided with a list of inputs. Remove the first or only provide a single file as input."
        )

    log_list = []
    error_list: List[Tuple[int, int]] = []
    if files:
        graph = (
            ContentGraphInterface()
            if is_graph_related_files(files, clear_cache) and use_graph
            else None
        )
        if graph:
            try:
                update_content_graph(
                    graph,
                    use_git=True,
                    output_path=graph.output_path,
                )
            except Exception as e:
                logger.warning(
                    "Error updating content graph. Will not format using the graph."
                )
                logger.debug(f"Error encountered when updating content graph: {e}")
                graph = False
        for file in files:
            file_path = str(Path(file))
            file_type = find_type(file_path, clear_cache=clear_cache)

            # Check if this is an unskippable file
            if not any(
                [
                    file_path.endswith(unskippable_file)
                    for unskippable_file in UNSKIP_FORMATTING_FILES
                ]
            ):
                # If it is not an unskippable file, skip if needed
                if Path(file_path).name in SKIP_FORMATTING_FILES:
                    continue

            if file_type and file_type.value not in UNFORMATTED_FILES:
                file_type = file_type.value
                info_res, err_res, skip_res = run_format_on_file(
                    input=file_path,
                    file_type=file_type,
                    from_version=from_version,
                    interactive=interactive,
                    output=output,
                    no_validate=no_validate,
                    update_docker=update_docker,
                    assume_answer=assume_answer,
                    deprecate=deprecate,
                    add_tests=add_tests,
                    graph=graph,
                    clear_cache=clear_cache,
                )
                if err_res:
                    log_list.extend([(err_res, "red")])
                if info_res:
                    log_list.extend([(info_res, "green")])
                if skip_res:
                    log_list.extend([(skip_res, "yellow")])
            elif file_type:
                log_list.append(
                    (
                        [
                            f"Ignoring format for {file_path} as {file_type.value} is currently not "
                            f"supported by format command"
                        ],
                        "yellow",
                    )
                )
            else:
                log_list.append(
                    (
                        [
                            f"Was unable to identify the file type for the following file: {file_path}"
                        ],
                        "red",
                    )
                )
        if graph:  # In case that the graph was activated, we need to call exit in order to close it.
            graph.__exit__()
        update_content_entity_ids(files)

    else:
        if not use_git:
            log_list.append(
                (
                    [f"Failed format file {input}." + "No such file or directory"],
                    "red",
                )
            )
        # No files were found to format
        raise typer.Exit(0)

    logger.info("")  # Just adding a new line before summary
    for string, print_color in log_list:
        joined_string = "\n".join(string)
        logger.info(f"<{print_color}>{joined_string}</{print_color}>")

    if error_list:
        raise typer.Exit(1)
    raise typer.Exit(0)


def get_files_to_format_from_git(
    supported_file_types: List[str], prev_ver: str, include_untracked: bool
) -> List[str]:
    """Get the files to format from git.

    Args:
        supported_file_types(list): File extensions which are supported by format
        prev_ver(str): The branch name or commit hash to compare with
        include_untracked(bool): Whether to include untracked files

    Returns:
        list. a list of all the files that should be formatted.
    """
    git_util = GitUtil()
    all_changed_files = git_util.get_all_changed_files(
        prev_ver=prev_ver, include_untracked=include_untracked
    )

    filtered_files = []
    for file_path in all_changed_files:
        str_file_path = str(file_path)

        # get the file extension without the '.'
        file_extension = os.path.splitext(str_file_path)[1][1:]
        if file_extension in supported_file_types and Path(str_file_path).exists():
            filtered_files.append(str_file_path)

    if filtered_files:
        detected_files_string = "\n".join(filtered_files)
        logger.info(
            f"<cyan>Found the following files to format:\n{detected_files_string}</cyan>"
        )

    else:
        logger.info("<red>Did not find any files to format</red>")

    return filtered_files


def update_content_entity_ids(files: List[str]):
    """Update the changed content entity ids in the files.
    Args:
        files (list): a list of files in which to update the content ids.

    """
    if not CONTENT_ENTITY_IDS_TO_UPDATE:
        return

    logger.debug(
        f"Collected content entities IDs to update:\n{CONTENT_ENTITY_IDS_TO_UPDATE}\n"
        f"Going over files to update these IDs in other files..."
    )
    for file in files:
        file_path = str(Path(file))
        logger.debug(
            f"Processing file {file_path} to check for content entities IDs to update"
        )
        with open(file_path, "r+") as f:
            file_content = f.read()
            for id_to_replace, updated_id in CONTENT_ENTITY_IDS_TO_UPDATE.items():
                file_content = file_content.replace(id_to_replace, updated_id)
            f.seek(0)
            f.write(file_content)
            f.truncate()


def run_format_on_file(
    input: str, file_type: str, from_version: str, interactive: bool, **kwargs
) -> Tuple[List[str], List[str], List[str]]:
    """Run the relevent format of file type.
    Args:
        input (str): The input file path.
        file_type (str): The type of input file
        from_version (str): The fromVersion value that was set by User.
        interactive (bool): Whether to run the format interactively or not (usually for contribution management)
    Returns:
        List of Success , List of Error.
    """

    if file_type == "betaintegration":
        file_type = "integration"
    schema_path = os.path.normpath(
        os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, f"{file_type}.yml")
    )
    if file_type not in ("integration", "script") and "update_docker" in kwargs:
        # non code formatters don't support update_docker param. remove it
        del kwargs["update_docker"]
    if file_type not in ("integration", "playbook", "script") and "add_tests" in kwargs:
        # adding tests is relevant only for integrations, playbooks and scripts.
        del kwargs["add_tests"]
    if file_type not in CONTENT_ITEMS_WITH_GRAPH and "graph" in kwargs:
        # relevant only for incidentfield/layouts/mappers
        del kwargs["graph"]

    updater_class = FILE_TYPE_AND_LINKED_CLASS.get(file_type)
    if not updater_class:  # fail format so long as xsiam entities dont have formatters
        logger.info(
            f"<yellow>No updater_class was found for file type {file_type}</yellow>"
        )
        return format_output(input, 1, VALIDATE_RES_SKIPPED_CODE)

    update_object = updater_class(
        input=input,
        path=schema_path,
        from_version=from_version,
        interactive=interactive,
        **kwargs,
    )
    format_res, validate_res = update_object.format_file()  # type: ignore
    CONTENT_ENTITY_IDS_TO_UPDATE.update(update_object.updated_ids)
    return format_output(input, format_res, validate_res)


def format_output(
    input: str,
    format_res: int,
    validate_res: int,
) -> Tuple[List[str], List[str], List[str]]:
    info_list = []
    error_list = []
    skipped_list = []
    if format_res and validate_res:
        if validate_res == VALIDATE_RES_SKIPPED_CODE:
            error_list.append(f"Format Status on file: {input} - Failed")
            skipped_list.append(f"Validate Status on file: {input} - Skipped")
        elif validate_res == VALIDATE_RES_FAILED_CODE:
            error_list.append(f"Format Status on file: {input} - Failed")
        else:
            error_list.append(f"Format Status on file: {input} - Failed")
            error_list.append(f"Validate Status on file: {input} - Failed")
    elif format_res and not validate_res:
        error_list.append(f"Format Status on file: {input} - Failed")
        info_list.append(f"Validate Status on file: {input} - Success")
    elif not format_res and validate_res:
        if validate_res == VALIDATE_RES_SKIPPED_CODE:
            info_list.append(f"Format Status on file: {input} - Success")
            skipped_list.append(f"Validate Status on file: {input} - Skipped")
        elif validate_res == VALIDATE_RES_FAILED_CODE:
            info_list.append(f"Format Status on file: {input} - Success")
        else:
            info_list.append(f"Format Status on file: {input} - Success")
            error_list.append(f"Validate Status on file: {input} - Failed")
            error_list.append(
                f"For more information run: `demisto-sdk validate -i {input}`"
            )
    elif not format_res and not validate_res:
        info_list.append(f"Format Status on file: {input} - Success")
        info_list.append(f"Validate Status on file: {input} - Success")
    return info_list, error_list, skipped_list


def is_graph_related_files(files: List[str], clear_cache: bool) -> bool:
    """
    Check if the files that Format should check are of type mapper, layout or incident fields.
    Otherwise, we don't need to start the graph.

    Args:
        files (List[str]): a list of the paths of the files Format should check.
        clear_cache (bool): wether to clear the cache.

    Returns:
        True if the files are of type mapper, layout or incident fields, else False.
    """
    for file in files:
        file_path = str(Path(file))
        if file_type := find_type(file_path, clear_cache=clear_cache):
            file_type = file_type.value
            if file_type in CONTENT_ITEMS_WITH_GRAPH:
                return True
    return False

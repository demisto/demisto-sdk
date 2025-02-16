from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import NO_COLOR, RED, FileType
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter


@logging_setup_decorator
def split(
    ctx: typer.Context,
    input: Path = typer.Option(
        ..., "-i", "--input", help="The yml/json file to extract from"
    ),
    output: Path = typer.Option(
        None,
        "-o",
        "--output",
        help="The output dir to write the extracted code/description/image/json to.",
    ),
    no_demisto_mock: bool = typer.Option(
        False,
        help="Don't add an import for demisto mock. (only for yml files)",
        show_default=True,
    ),
    no_common_server: bool = typer.Option(
        False,
        help="Don't add an import for CommonServerPython. (only for yml files)",
        show_default=True,
    ),
    no_auto_create_dir: bool = typer.Option(
        False,
        help="Don't auto create the directory if the target directory ends with *Integrations/*Scripts/*Dashboards/*GenericModules.",
        show_default=True,
    ),
    new_module_file: bool = typer.Option(
        False,
        help="Create a new module file instead of editing the existing file. (only for json files)",
        show_default=True,
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
):
    """
    Splits downloaded scripts, integrations and generic module files into multiple files.
    Integrations and scripts are split into the package format.
    Generic modules have their dashboards split into separate files and modify the module to the content repository standard.

    Files are stored in the content repository in a directory format, which enables performing extensive code validations and maintaining a more stable code base.
    For more details [see](https://xsoar.pan.dev/docs/integrations/package-dir).
    """
    sdk = ctx.obj

    file_type: FileType = find_type(str(input), ignore_sub_categories=True)
    if file_type not in [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.GENERIC_MODULE,
        FileType.MODELING_RULE,
        FileType.PARSING_RULE,
        FileType.LISTS,
        FileType.ASSETS_MODELING_RULE,
    ]:
        typer.echo(
            f"{RED}File is not an Integration, Script, List, Generic Module, Modeling Rule or Parsing Rule.{NO_COLOR}"
        )
        raise typer.Exit(code=1)

    if file_type in [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.MODELING_RULE,
        FileType.PARSING_RULE,
        FileType.ASSETS_MODELING_RULE,
    ]:
        yml_splitter = YmlSplitter(
            input=str(input),
            configuration=sdk.configuration,
            file_type=file_type.value,
            no_demisto_mock=no_demisto_mock,
            no_common_server=no_common_server,
            no_auto_create_dir=no_auto_create_dir,
        )
        return yml_splitter.extract_to_package_format()

    else:
        json_splitter = JsonSplitter(
            input=str(input),
            output=str(output) if output else None,
            no_auto_create_dir=no_auto_create_dir,
            new_module_file=new_module_file,
            file_type=file_type,
        )
        return json_splitter.split_json()

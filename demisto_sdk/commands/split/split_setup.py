import typer
from pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.config import get_config

split_app = typer.Typer()


@split_app.command()
def split(
    input: Path = typer.Option(..., help="The yml/json file to extract from"),
    output: Path = typer.Option(None, help="The output dir to write the extracted code/description/image/json to."),
    no_demisto_mock: bool = typer.Option(False, help="Don't add an import for demisto mock. (only for yml files)", show_default=True),
    no_common_server: bool = typer.Option(False, help="Don't add an import for CommonServerPython. (only for yml files)", show_default=True),
    no_auto_create_dir: bool = typer.Option(False, help="Don't auto create the directory if the target directory ends with *Integrations/*Scripts/*Dashboards/*GenericModules.", show_default=True),
    new_module_file: bool = typer.Option(False, help="Create a new module file instead of editing the existing file. (only for json files)", show_default=True),
):
    """Split the code, image and description files from a Demisto integration or script yaml file
    to multiple files (To a package format - https://demisto.pan.dev/docs/package-dir).
    """

    config = get_config()

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
        typer.echo("<red>File is not an Integration, Script, List, Generic Module, Modeling Rule or Parsing Rule.</red>")
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
            configuration=config.configuration,
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

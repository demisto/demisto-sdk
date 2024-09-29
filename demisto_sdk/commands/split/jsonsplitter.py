import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from demisto_sdk.commands.common.constants import (
    DASHBOARDS_DIR,
    DEFAULT_JSON_INDENT,
    GENERIC_MODULES_DIR,
    LISTS_DIR,
    PACKS_DIR,
    FileType,
)
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.common.tools import (
    get_pack_name,
    is_external_repository,
    pascal_case,
    write_dict,
)


class ListData(StrEnum):
    """
    A closed list of types of list (content-item) that the server accepts
    """

    TEXT = "plain_text"
    HTML = "html"
    CSS = "css"
    MD = "markdown"
    JSON = "json"


class JsonSplitter:
    """
    JsonSplitter is a class intended to split Generic Modules from their intrinsic dashboards

    Attributes:
        input (str): The path to the Generic module json file to split.
        output (str): The path to a directory in which the new dashboards should be put (and the module
                    if we create a new module file).
        no_auto_create_dir (bool): Whether to auto create new directories in content repo.
        new_module_file (bool): Whether to create a new module file.
    """

    def __init__(
        self,
        input: Union[Path, str],
        output: Optional[
            Union[Path, str]
        ] = None,  # If not provided, the output will be created next to the input
        file_type: FileType = FileType.GENERIC_MODULE,
        no_auto_create_dir: bool = False,
        new_module_file: bool = False,
        input_file_data: Optional[Dict] = None,
    ):
        self.input = input
        self.output = output or Path(input).parent
        self.dashboard_dir = output if output else ""
        self.module_dir = output if output else ""
        self.autocreate_dir = not no_auto_create_dir
        self.new_module_file = new_module_file
        self.json_data = (
            input_file_data
            if input_file_data is not None
            else JsonFile.read_from_local_path(path=str(self.input))
        )
        self.type = file_type

    def split_json(self):
        if self.type == FileType.LISTS:
            self.split_list()
        else:
            self.split_dashboard()
        return 0

    def split_dashboard(self):
        logger.debug(
            f"<cyan>Starting dashboard extraction from generic module {self.json_data.get('name')}</cyan>"
        )
        self.create_output_dirs()
        self.create_dashboards()
        self.create_module()

    def create_output_dir(self, path):
        try:
            os.mkdir(path)
        except FileExistsError:
            pass

    def create_output_dirs(self):
        # no output given
        if not self.dashboard_dir:
            # check if in content repository
            if not is_external_repository() and self.autocreate_dir:
                pack_name = get_pack_name(self.input)
                logger.debug(
                    f"No output path given creating Dashboards and GenericModules "
                    f"directories in pack {pack_name}"
                )
                pack_path = os.path.join(PACKS_DIR, pack_name)
                self.dashboard_dir = os.path.join(pack_path, DASHBOARDS_DIR)
                self.module_dir = os.path.join(pack_path, GENERIC_MODULES_DIR)

                # create the dirs, dont fail if exist
                self.create_output_dir(self.dashboard_dir)
                self.create_output_dir(self.module_dir)

            # if not in content create the files locally
            else:
                logger.debug(
                    "No output path given and not running in content repo, creating "
                    "files in the current working directory"
                )
                self.dashboard_dir = "."
                self.module_dir = "."

    def create_dashboards(self):
        logger.debug("Starting dashboard creation")

        for view in self.json_data.get("views", []):
            for tab in view.get("tabs", []):
                dashboard_data = tab.get("dashboard")

                if dashboard_data:
                    dashboard_file_name = (
                        dashboard_data.get("name").replace(" ", "") + ".json"
                    )
                    full_dashboard_path = os.path.join(
                        self.dashboard_dir, dashboard_file_name
                    )

                    logger.debug(f"Creating dashboard: {full_dashboard_path}")
                    write_dict(full_dashboard_path, data=dashboard_data, indent=4)
                    tab["dashboard"] = {"id": dashboard_data.get("id")}

    def create_module(self):
        if not self.new_module_file:
            logger.debug(f"Updating module file {self.input}")
            module_file_path = self.input

        else:
            logger.debug("Creating new module file")

            given_name = False
            while not given_name:
                file_name = str(input("\nPlease enter a new module file name: "))
                if not file_name or " " in file_name:
                    logger.info("File name cannot be empty nor have spaces in it")

                else:
                    given_name = True

                if not file_name.endswith(".json"):
                    file_name = file_name + ".json"

            module_file_path = os.path.join(self.module_dir, file_name)

        write_dict(module_file_path, data=self.json_data, indent=DEFAULT_JSON_INDENT)

    def get_auto_output_path_for_list(self) -> Tuple[Path, Path, Path]:
        """
        Obtains the output path automatically according to the List name
        if autocreate_dir == true, otherwise returns the output as is
        """
        suffix_by_type = {
            ListData.TEXT: ".txt",
            ListData.HTML: ".html",
            ListData.CSS: ".css",
            ListData.MD: ".md",
            ListData.JSON: ".json",
        }

        suffix = suffix_by_type.get(self.json_data["type"], ".txt")

        file_name = Path(pascal_case(self.json_data["name"]) + ".json")
        file_data_name = file_name.with_name(f"{file_name.stem}_data{suffix}")

        if self.autocreate_dir:
            pack_name = get_pack_name(self.input)

            if not pack_name:
                return Path(self.input).parent, file_name, file_data_name

            (
                list_name_dir := Path(PACKS_DIR)
                / pack_name
                / LISTS_DIR
                / file_name.stem
            ).mkdir(parents=True, exist_ok=True)

            return list_name_dir, file_name, file_data_name

        if not (output := Path(self.output)).is_dir():
            output = output.parent

        return output, file_name, file_data_name

    def write_file_data(self, list_name_dir: Path, file_data_name: Path):
        if file_data_name.suffix == ".json":
            try:
                data_list = json.loads(self.json_data["data"])
            except Exception as e:
                raise Exception(
                    f"Could not parse data of the list {self.json_data['name']}.\n"
                ) from e

            JsonFile.write(
                data_list,
                (list_name_dir / file_data_name),
                indent=DEFAULT_JSON_INDENT,
            )
        else:
            TextFile.write(self.json_data["data"], (list_name_dir / file_data_name))

    def write_file_metadata_list(self, file_path: Path):
        """
        writes the metadata of the list so that the data segment with `-` because the split
        """
        self.json_data["data"] = "-"
        JsonFile.write(self.json_data, file_path, indent=DEFAULT_JSON_INDENT)

    def split_list(self):
        list_name_dir, file_name, file_data_name = self.get_auto_output_path_for_list()

        self.write_file_data(list_name_dir, file_data_name)

        self.write_file_metadata_list(list_name_dir / file_name)

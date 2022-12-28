import os

import click

from demisto_sdk.commands.common.constants import (
    DASHBOARDS_DIR,
    GENERIC_MODULES_DIR,
    PACKS_DIR,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import get_pack_name, is_external_repository

json = JSON_Handler()


class JsonSplitter:
    """
    JsonSplitter is a class intended to split Generic Modules from their intrinsic dashboards

    Attributes:
        input (str): The path to the Generic module json file to split.
        output (str): The path to a directory in which the new dashboards should be put (and the module
                    if we create a new module file).
        no_auto_create_dir (bool): Whether to auto create new directories in content repo.
        no_logging (bool): Whether to print logs to the user.
        new_module_file (bool): Whether to create a new module file.
    """

    def __init__(
        self,
        input: str,
        output: str,
        no_auto_create_dir: bool = False,
        no_logging: bool = False,
        new_module_file: bool = False,
    ):
        self.input = input
        self.dashboard_dir = output if output else ""
        self.module_dir = output if output else ""
        self.logging = not no_logging
        self.autocreate_dir = not no_auto_create_dir
        self.new_module_file = new_module_file

        with open(self.input, "rb") as json_file:
            self.module_json_data = json.load(json_file)

    def split_json(self):
        if self.logging:
            click.secho(
                f"Starting dashboard extraction from generic module {self.module_json_data.get('name')}",
                fg="bright_cyan",
            )
        self.create_output_dirs()
        self.create_dashboards()
        self.create_module()
        return 0

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
                if self.logging:
                    click.echo(
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
                if self.logging:
                    click.echo(
                        "No output path given and not running in content repo, creating "
                        "files in the current working directory"
                    )
                self.dashboard_dir = "."
                self.module_dir = "."

    def create_dashboards(self):
        if self.logging:
            click.echo("Starting dashboard creation")

        for view in self.module_json_data.get("views", []):
            for tab in view.get("tabs", []):
                dashboard_data = tab.get("dashboard")

                if dashboard_data:
                    dashboard_file_name = (
                        dashboard_data.get("name").replace(" ", "") + ".json"
                    )
                    full_dashboard_path = os.path.join(
                        self.dashboard_dir, dashboard_file_name
                    )

                    if self.logging:
                        click.echo(f"Creating dashboard: {full_dashboard_path}")

                    with open(full_dashboard_path, "w") as dashboard_file:
                        json.dump(dashboard_data, dashboard_file, indent=4)

                    tab["dashboard"] = {"id": dashboard_data.get("id")}

    def create_module(self):
        if not self.new_module_file:
            if self.logging:
                click.echo(f"Updating module file {self.input}")
            module_file_path = self.input

        else:
            if self.logging:
                click.echo("Creating new module file")

            given_name = False
            while not given_name:
                file_name = str(input("\nPlease enter a new module file name: "))
                if not file_name or " " in file_name:
                    click.echo("File name cannot be empty nor have spaces in it")

                else:
                    given_name = True

                if not file_name.endswith(".json"):
                    file_name = file_name + ".json"

            module_file_path = os.path.join(self.module_dir, file_name)

        with open(module_file_path, "w") as module_file:
            json.dump(self.module_json_data, module_file, indent=4)

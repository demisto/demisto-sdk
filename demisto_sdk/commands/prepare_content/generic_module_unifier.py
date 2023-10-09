import os
import sys
from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.constants import PACKS_DIR, FileType
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_file,
    get_pack_name,
    write_dict,
)


class GenericModuleUnifier:
    """
    Unifies a GenericModule object with it's Dashboards
    """

    def __init__(
        self,
        input: str,
        output: str = "",
        force: bool = False,
        marketplace: Optional[str] = None,
        **kwargs,
    ):
        """
        Init a GenericModuleUnifier
        Args:
            input: a path of the GenericModule file to unify.
            output: The output dir to write the unified GenericModule json to.
            force: if True - Forcefully overwrites the preexisting unified GenericModule file if one exists.
        """

        self.input_path = input
        self.pack_name = get_pack_name(file_path=self.input_path)
        self.pack_path = os.path.join(PACKS_DIR, self.pack_name)

        self.input_file_name = Path(self.input_path).name.rstrip(".json")
        self.use_force = force
        self.marketplace = marketplace

        if output:
            if not os.path.isdir(output):
                logger.error("[red]You have failed to provide a legal dir path[/red]")
                sys.exit(1)

            self.dest_dir = output

        else:
            # an output wasn't given, save the unified file in the input's file dir
            self.dest_dir = os.path.dirname(self.input_path)

        self.dest_path = os.path.join(
            self.dest_dir, f"{self.input_file_name}_unified.json"
        )

    def find_dashboard_by_id(self, dashboard_id: str) -> Optional[Dict]:
        """
        Search for a dashboard with the given id in the relevant pack path.
        Args:
            dashboard_id: dashboard id to search for

        Returns: if found - the content of the dashboard, else - None.
        """
        dashboards_dir_path = f"{self.pack_path}/Dashboards/"
        for file_name in os.listdir(dashboards_dir_path):
            file_path = os.path.join(dashboards_dir_path, file_name)
            if find_type(file_path) == FileType.DASHBOARD:
                # it's a dashboard
                dashboard = get_file(file_path, raise_on_error=True)
                if dashboard.get("id") == dashboard_id:
                    # the searched dashboard was found
                    return dashboard
        return None

    def merge_generic_module_with_its_dashboards(self) -> Dict:
        """
        Unifies a GenericModule object with it's Dashboards

        Returns: the unified GenericModule
        """
        generic_module = get_file(self.input_path, raise_on_error=True)

        views = generic_module.get("views", [])
        for view in views:
            tabs = view.get("tabs", [])
            for tab in tabs:
                dashboard_id = tab.get("dashboard", {}).get("id")
                if dashboard_id:
                    # search dashboard in the GenericModule's pack
                    dashboard_content = self.find_dashboard_by_id(
                        dashboard_id=dashboard_id
                    )
                    if dashboard_content:
                        tab["dashboard"] = dashboard_content

                    else:
                        logger.info(
                            f"[red]Dashboard {dashboard_id} was not found in pack: {self.pack_name} "
                            f"and therefore was not unified[/red]"
                        )

        self.save_unified_generic_module(generic_module)

        return generic_module

    def save_unified_generic_module(self, unified_generic_module_json: Dict):
        """
        Save the unified GenericModule to a json file.
        Args:
            unified_generic_module_json: unified GenericModule

        """
        if Path(self.dest_path).is_file() and self.use_force is False:
            raise ValueError(
                f"Output file already exists: {self.dest_path}."
                " Make sure to remove this file from source control, set a different output dir or set the"
                "-f argument to True in order to overwrite the preexisting file."
            )

        write_dict(self.dest_path, data=unified_generic_module_json, indent=4)

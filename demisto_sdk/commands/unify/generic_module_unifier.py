
import json
import os
import sys
from argparse import FileType
from typing import Dict, Optional

import click

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.tools import get_pack_name, print_error, find_type


class GenericModuleUnifier:
    """
    Unifies a GenericModule object with it's Dashboards
    """

    def __init__(self, input: str, output: str = '', force: bool = False):
        """
        Init a GenericModuleUnifier
        Args:
            input: a path of the GenericModule file to unify.
            output: The output dir to write the unified GenericModule json to.
            force: if True - Forcefully overwrites the preexisting unified GenericModule file if one exists.
        """

        if find_type(input) == FileType.GENERIC_MODULE:
            self.input_path = input
        else:
            print_error('You have failed to provide a legal file path, a legal file path '
                        'should be to a directory of a GenericModule file.')

        self.pack_name = get_pack_name(file_path=self.input_path)
        self.pack_path = os.path.dirname(os.path.dirname(self.input_path))

        self.input_file_name = os.path.basename(self.input_path).rstrip('.json')
        self.use_force = force

        if output:
            if not os.path.isdir(output):
                print_error('You have failed to provide a legal dir path')
                sys.exit(1)
            self.dest_dir = output
        else:
            # an output wasn't given, save the unified file in the input's file dir
            self.dest_dir = os.path.dirname(self.input_path)
        self.dest_path = os.path.join(self.dest_dir, f'{self.input_file_name}_unified.json')

    def find_dashboard_by_id(self, dashboard_id: str) -> Optional[Dict]:
        """
        Search for a dashboard with the given id in the relevant pack path.
        Args:
            dashboard_id: dashboard id to search for

        Returns: if found - the content of the dashboard, else - None.
        """
        dashboards_dir_path = f'{self.pack_path}/Dashboards/'
        for file_name in os.listdir(dashboards_dir_path):
            file_path = os.path.join(dashboards_dir_path, file_name)
            if file_path.endswith('.json') and file_name.startswith('dashboard'):
                # it's a dashboard
                with open(file_path) as f:
                    dashboard = json.load(f)
                if dashboard.get('id') == dashboard_id:
                    # the searched dashboard was found
                    return dashboard
        return None

    def merge_generic_module_with_its_dashboards(self) -> Dict:
        """
        Unifies a GenericModule object with it's Dashboards

        Returns: the unified GenericModule
        """
        with open(self.input_path) as f:
            generic_module = json.load(f)

        views = generic_module.get('views')
        if views:
            for view in views:
                tabs = view.get('tabs')
                if tabs:
                    for tab in tabs:
                        dashboard = tab.get('dashboard')
                        if dashboard:
                            dashboard_id = dashboard.get('id')
                            if dashboard_id:
                                # search dashboard in the GenericModule's pack
                                dashboard_content = self.find_dashboard_by_id(dashboard_id=dashboard_id)
                                if dashboard_content:
                                    tab['dashboard'] = dashboard_content
                                else:
                                    click.secho(f'Dashboard {dashboard_id} was not found in pack: {self.pack_name} '
                                                f'and therefore was not unified', fg="bright_red")

        self.save_unified_generic_module(generic_module)

        return generic_module

    def save_unified_generic_module(self, unified_generic_module_json: Dict):
        """
        Save the unified GenericModule to a json file.
        Args:
            unified_generic_module_json: unified GenericModule

        Returns: None
        """

        if os.path.isfile(self.dest_path) and self.use_force is False:
            raise ValueError(f'Output file already exists: {self.dest_path}.'
                             ' Make sure to remove this file from source control or set a different output dir.')

        with open(self.dest_path, mode='w') as file:
            json.dump(unified_generic_module_json, file, indent=4)

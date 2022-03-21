import io
import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

from demisto_sdk.commands.common.constants import (DIR_TO_PREFIX,
                                                   INTEGRATIONS_DIR,
                                                   SCRIPTS_DIR)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir, print_error

UNSUPPORTED_INPUT_ERR_MSG = '''Unsupported input. Please provide either:
1. a directory of an integration or a script.
2. a path of a GenericModule file.'''


class YAMLUnifier(ABC):
    """Interface to YAML objects that need to be unified

    Attributes:
        package_path (str): The directory path to the files to unify.
        dest_path (str, optional): The output dir to write the unified YAML to.
        use_force(bool): Forcefully overwrites the preexisting yml if one exists.
        yaml(YAML_Handler): Wrapper object to handle YAML files.
        yml_path(str): The YAML file path.
        yml_data(dict): The YAML doucment Python object.
    """

    def __init__(
        self,
        input: str,
        output: Optional[str] = None,
        force: bool = False,
    ):
        directory_name = ''
        # Changing relative path to current abspath fixed problem with default output file name.
        if input == '.':
            input = os.path.abspath(input)
        if not os.path.isdir(input):
            print_error(UNSUPPORTED_INPUT_ERR_MSG)
            sys.exit(1)
        for optional_dir_name in DIR_TO_PREFIX:
            if optional_dir_name in input:
                directory_name = optional_dir_name

        if not directory_name:
            print_error(UNSUPPORTED_INPUT_ERR_MSG)

        self.package_path = input
        self.package_path = self.package_path.rstrip(os.sep)

        self.use_force = force
        self.dest_path = output

        yml_paths, self.yml_path = get_yml_paths_in_dir(self.package_path, Errors.no_yml_file(self.package_path))
        for path in yml_paths:
            # The plugin creates a unified YML file for the package.
            # In case this script runs locally and there is a unified YML file in the package we need to ignore it.
            # Also,
            # we don't take the unified file by default because
            # there might be packages that were not created by the plugin.
            if 'unified' not in path and os.path.basename(os.path.dirname(path)) not in [SCRIPTS_DIR, INTEGRATIONS_DIR]:
                self.yml_path = path
                break

        self.yaml = YAML_Handler(width=50000)  # make sure long lines will not break (relevant for code section)

        if self.yml_path:
            with io.open(self.yml_path, 'r', encoding='utf8') as yml_file:
                self.yml_data = self.yaml.load(yml_file)
        else:
            self.yml_data = {}
            print_error(f'No yml found in path: {self.package_path}')

    @abstractmethod
    def unify(self):
        """Merges the various components to create an output yml file."""
        ...

import io
import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

from demisto_sdk.commands.common.constants import DIR_TO_PREFIX, INTEGRATIONS_DIR, SCRIPTS_DIR, MarketplaceVersions
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.handlers import YAML_Handler, XSOAR_Handler
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir, print_error
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser
from demisto_sdk.commands.content_graph.objects.base_content import content_type_to_model
UNSUPPORTED_INPUT_ERR_MSG = '''Unsupported input. Please provide either:
1. Path to directory of an integration or a script.
2. Path to directory of a Parsing/Modeling rule.'''


class Unifier(ABC):
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
        marketplace: Optional[str] = None,
    ):
        # pasrer ContentItemParser.from_path(input, [marketplace])
        content_item = ContentItemParser.from_path(input, marketplace)
        content_type_to_model[content_item.content_type].from_orm(content_item)
        directory_name = ''
        # Changing relative path to current abspath fixed problem with default output file name.
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
        self.dir_name = ''
        self.marketplace = marketplace
        self.data = None
    
    @abstractmethod
    def _unify(self):
        ...
    
    @abstractmethod
    @property
    def suffix(self) -> str:
        ...
    
    @abstractmethod
    @property
    def handler(self) -> XSOAR_Handler:
        ...
    
    # def _rename_incidents(self):
    #     if self.marketplace == MarketplaceVersions.MarketplaceV2:
    #         if widget:
    #             widget["name"] = widget["name"].replace("Incidents", "Alerts")
    #         if layout or layoutContainer or dashboard:
    #             layout["name"] = layout["name"].replace("Incidents", "Alerts")
    #             layoutContainer["name"] = layoutContainer["name"].replace("Incidents", "Alerts")
    
    def _prepare_for_marketplace(self):
        if self.data and self.marketplace in {MarketplaceVersions.MarketplaceV2, MarketplaceVersions.XPANSE}:
            self._alternate_item_fields(self.data)
    
    def _alternate_item_fields(self, yml_data):
        """
        Go over all of the given content item fields and if there is a field with an alternative name, which is marked
        by '_x2', use that value as the value of the original field (the corresponding one without the '_x2' suffix).
        Args:
            content_item: content item object

        """
        copy_dict = yml_data.copy()  # for modifying dict while iterating
        for field, value in copy_dict.items():
            if field.endswith('_x2'):
                yml_data[field[:-3]] = value
                yml_data.pop(field)
            elif isinstance(yml_data[field], dict):
                self._alternate_item_fields(yml_data[field])
            elif isinstance(yml_data[field], list):
                for item in yml_data[field]:
                    if isinstance(item, dict):
                        self._alternate_item_fields(item)

    def _prepare(self):
        to_upload = self.content_item.prepare()

    def unify(self):
        """Merges the various components to create an output yml file."""
        self._prepare()
        self._unify()

    def _set_dest_path(
        self,
        file_name_suffix: Optional[str] = None,
    ):
        """Sets the target (destination) output path for the unified YAML, based on:
            - Integration/Script directory name.
            - Content item type (Integration/Script/Rule).
            - Content item prefix (integration/script/parsingrule/modelingrule).
            - Provided file name suffix.

        Args:
            file_name_suffix(str): An optional suffix to concat to the filename.
        """
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}.{}'.format(DIR_TO_PREFIX[self.dir_name], package_dir_name, self.suffix)

        if file_name_suffix:
            # append suffix to output file name
            output_filename = file_name_suffix.join(os.path.splitext(output_filename))

        if self.dest_path:
            self.dest_path = os.path.join(self.dest_path, output_filename)
        else:
            self.dest_path = os.path.join(self.package_path, output_filename)

    def _output(
        self,
        file_path: Optional[str],
        file_data: dict,
    ):
        """Writes the YAML unified to the given path.
        Checks whether the unified YAML already exists, and either fail or overwrite it forced to.

        Args:
            file_path(str): The file path to output the YAML to.
            file_data(dict): The unified YAML contents.
        """
        if os.path.isfile(file_path) and not self.use_force:  # type: ignore[arg-type]
            raise ValueError(
                f'Output file already exists: {self.dest_path}.'
                ' Make sure to remove this file from source control'
                ' or rename this package (for example if it is a v2).'
            )

        with io.open(file_path, mode='w', encoding='utf-8') as file_:  # type: ignore[arg-type]
            self.handler.dump(file_data, file_)

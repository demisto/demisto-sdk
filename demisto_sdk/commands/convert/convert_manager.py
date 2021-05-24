import os

import click
from packaging.version import Version

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager
# noinspection PyUnresolvedReferences
from demisto_sdk.commands.convert.converters.classifier.classifiers_convert_manager import ClassifiersDirConvertManager
# noinspection PyUnresolvedReferences
from demisto_sdk.commands.convert.converters.layout.layouts_convert_manager import LayoutsDirConvertManager


class ConvertManager:
    SERVER_MAX_VERSION_SUPPORTED = Version('6.1.0')
    SERVER_MIN_VERSION_SUPPORTED = Version('5.5.0')

    def __init__(self, input_path: str, server_version: str):
        self.input_path: str = input_path
        self.server_version: Version = Version(server_version)

    def convert(self):
        from demisto_sdk.commands.common.tools import (get_yaml)
        schema_data: dict = get_yaml(
            '/Users/tneeman/dev/demisto/demisto-sdk/demisto_sdk/commands/common/schemas/layoutscontainer.yml')
        schema_mapping = schema_data.get('mapping', dict())
        layout_indicator_fields_2 = {schema_field for schema_field, schema_value in schema_mapping.items()
                                   if 'mapping' in schema_value and 'indicator' in schema_field}
        # self.schema_data: dict = get_yaml(schema_data)
        layout_dynamic_fields: list = [f for f, _ in schema_data.get('mapping').items() if
                                       schema_data.get('mapping').get(f).get('mapping')]
        layout_indicator_fields: list = [f for f in layout_dynamic_fields if 'indicator' in f]
        pack = self.create_pack_object()
        if self.version_requested_is_below_pack_version(pack):
            click.secho('Given version is lower than pack version.\n'
                        f'Requested version: {self.server_version}.\n'
                        f'Pack version: {str(pack.metadata.server_min_version)}', fg='red')
            # TODO check str on version works as expected
            return 1
        all_dir_converters = [dir_converter(pack, self.input_path, self.server_version)
                              for dir_converter in AbstractDirConvertManager.__subclasses__()]
        relevant_dir_converters = [dir_converter for dir_converter in all_dir_converters
                                   if dir_converter.should_convert()]
        if not relevant_dir_converters:
            click.secho('No entities were found to convert. Please validate your input path and version are'
                        f'valid: {self.input_path}, {self.server_version}', fg='red')
            return 1
        for dir_converter in relevant_dir_converters:
            dir_converter.convert()

    def create_pack_object(self) -> Pack:
        """
        Uses self.input_path, returns a Pack object corresponding to the pack given in the path.
        Examples:
            - self.input_path = 'Packs/BitcoinAbuse/Layouts'
              Returns: Pack('Packs/BitcoinAbuse')
            - self.input_path = 'Packs/BitcoinAbuse'
              Returns: Pack('Packs/BitcoinAbuse')
        Returns:
            (Pack): Pack object of the pack the conversion was requested for.
        """
        path_dir = os.path.dirname(self.input_path)
        pack_path = self.input_path if path_dir == PACKS_DIR else path_dir
        return Pack(pack_path)

    def version_requested_is_below_pack_version(self, pack: Pack) -> bool:
        """
        Receives Pack object, returns whether the version requested by user for conversion is below the minimal
        server version of the pack.
        Args:
            pack (Pack): Pack object of the corresponding pack of the requested conversion.

        Returns:
            (bool):
            - True if pack minimum version > requested version.
            - false if pack minimum version <= requested version.
        """
        return self.server_version >= pack.metadata.server_min_version

    def server_version_is_not_supported(self) -> bool:
        """
        Checks whether the requested version is supported for conversion.
        This is needed to make sure that the requested versions do have a corresponding converter
        before starting the conversion process.
        Returns:
            (bool):
            - True if server version requested for conversion is not supported.
            - False if server version requested for conversion is supported.
        """
        return self.SERVER_MIN_VERSION_SUPPORTED <= self.server_version <= self.SERVER_MAX_VERSION_SUPPORTED

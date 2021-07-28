import os
from abc import abstractmethod

import click
from packaging.version import Version

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import is_pack_path
from demisto_sdk.commands.convert.converters.classifier.classifier_6_0_0_converter import \
    ClassifierSixConverter
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import \
    ClassifierBaseConverter
from demisto_sdk.commands.convert.converters.layout.layout_6_0_0_converter import \
    LayoutSixConverter
from demisto_sdk.commands.convert.converters.layout.layout_base_converter import \
    LayoutBaseConverter
from demisto_sdk.commands.convert.converters.layout.layout_up_to_5_9_9_converter import \
    LayoutBelowSixConverter


class AbstractDirConvertManager:
    VERSION_6_0_0 = Version('6.0.0')

    def __init__(self, pack: Pack, input_path: str, server_version: Version, entity_dir_name: str = ''):
        self.pack = pack
        self.input_path = input_path
        self.server_version = server_version
        self.entity_dir_name = entity_dir_name

    @abstractmethod
    def convert(self) -> int:
        pass

    def should_convert(self) -> bool:
        """
        Checks whether conversion should be done or not. Uses the 'entity_dir_name' received in init function
        by the inheriting class.
        Conversion should happen if one of the 2 cases occur:
        1) The input path for conversion is the whole pack
        2) The input path for conversion ends with the corresponding dir given in 'entity_dir_name'.
        Returns:
            (bool):
            - True if conversion should be done.
            - False if conversion should not be done.
        """
        return self.is_dir_convert_manager_path() or is_pack_path(self.input_path)

    def is_dir_convert_manager_path(self) -> bool:
        """
        Checks whether path given ends the 'entity_dir_name' field.
        Examples
            - self.input_path = 'Packs/BitcoinAbuse
              self.entity_dir_name = 'Layouts'
              Returns: False
            - self.input_path = 'Packs/BitcoinAbuse/Classifiers
              self.entity_dir_name = 'Layouts'
              Returns: False
            - self.input_path = 'Packs/BitcoinAbuse/Layouts
              self.entity_dir_name = 'Layouts'
              Returns: True
        Returns:
            (bool):
            - True if the path ends with 'entity_dir_name'.
            - False if path does not end with 'entity_dir_name'.
        """
        return os.path.basename(self.input_path) == self.entity_dir_name


class LayoutsDirConvertManager(AbstractDirConvertManager):

    def __init__(self, pack: Pack, input_path: str, server_version: Version):
        super().__init__(pack, input_path, server_version, entity_dir_name='Layouts')

    def convert(self) -> int:
        if self.server_version >= self.VERSION_6_0_0:
            layout_converter: LayoutBaseConverter = LayoutSixConverter(self.pack)
        else:
            layout_converter = LayoutBelowSixConverter(self.pack)
        convert_result = layout_converter.convert_dir()
        if not convert_result:
            click.secho(f'Converted Layouts successfully in pack: {str(self.pack.path)}', fg='green')
        return convert_result


class ClassifiersDirConvertManager(AbstractDirConvertManager):

    def __init__(self, pack: Pack, input_path: str, server_version: Version):
        super().__init__(pack, input_path, server_version, entity_dir_name='Classifiers')

    def convert(self) -> int:
        if self.server_version >= self.VERSION_6_0_0:
            classifier_converter: ClassifierBaseConverter = ClassifierSixConverter(self.pack)
            convert_result = classifier_converter.convert_dir()
            if not convert_result:
                click.secho(f'Converted Classifiers successfully in pack: {str(self.pack.path)}', fg='green')
            return convert_result
        else:
            raise NotImplementedError('Version requested to convert is not supported.')

    def should_convert(self) -> bool:
        """
        Returns whether conversion for classifiers should be made.
        Currently, conversion for versions 6_0_0 and above are supported, but
        conversion to 5_9_9 and below are not.
        Returns:
            (bool): True if server version is 6_0_0 and above, false otherwise.
        """
        return self.server_version >= self.VERSION_6_0_0 and super().should_convert()

from packaging.version import Version

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager
from demisto_sdk.commands.convert.converters.layout.layout_6_0_0_converter import LayoutSixConverter


class LayoutsDirConvertManager(AbstractDirConvertManager):
    VERSION_6_0_0 = Version('6.0.0')

    def __init__(self, pack: Pack, input_path: str, server_version: Version):
        super().__init__(pack, input_path, server_version, entity_dir_name='Layouts')
        self.input_path: str = input_path
        self.server_version = server_version
        self.pack = pack

    def convert(self):
        if self.server_version >= self.VERSION_6_0_0:
            layout_converter = LayoutSixConverter(self.pack)
        else:
            a = 2
            # TODO - layout below 6

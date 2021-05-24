from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from packaging.version import Version

class ClassifiersDirConvertManager(AbstractDirConvertManager):
    def convert(self):
        pass

    def __init__(self, pack: Pack, input_path: str, server_version: Version):
        super().__init__(pack, input_path, server_version, entity_dir_name='Classifiers')
        self.files_path: str = input_path
        self.server_version = server_version
        self.pack = pack

from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager


class LayoutsDirConvertManager(AbstractDirConvertManager):
    def __init__(self, input_path: str, server_version: str):
        super().__init__(input_path, server_version, 'Layouts')
        self.files_path: str = input_path
        self.server_version = server_version

    def convert(self):
        pass

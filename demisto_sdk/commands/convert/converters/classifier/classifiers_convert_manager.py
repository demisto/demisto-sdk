from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager


class ClassifiersDirConvertManager(AbstractDirConvertManager):
    def convert(self):
        pass

    def __init__(self, input_path: str, server_version: str):
        super().__init__(input_path, server_version, 'Classifiers')
        self.files_path: str = input_path
        self.version = server_version

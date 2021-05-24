import click

from demisto_sdk.commands.convert.converters.abstract_dir_convert_manager import AbstractDirConvertManager
# noinspection PyUnresolvedReferences
from demisto_sdk.commands.convert.converters.classifier.classifiers_convert_manager import ClassifiersDirConvertManager
# noinspection PyUnresolvedReferences
from demisto_sdk.commands.convert.converters.layout.layouts_convert_manager import LayoutsDirConvertManager


class ConvertManager:

    def __init__(self, input_path: str, server_version: str):
        self.input_path: str = input_path
        self.server_version: str = server_version

    def convert(self):
        all_dir_converters = [dir_converter(self.input_path, self.server_version)
                              for dir_converter in AbstractDirConvertManager.__subclasses__()]
        relevant_dir_converters = [dir_converter for dir_converter in all_dir_converters
                                   if dir_converter.should_convert()]
        if not relevant_dir_converters:
            click.secho('No entities were found to convert. Please validate your input path and version are'
                        f'valid: {self.input_path}, {self.server_version}', fg='red')
            return 1
        for dir_converter in relevant_dir_converters:
            dir_converter.convert()

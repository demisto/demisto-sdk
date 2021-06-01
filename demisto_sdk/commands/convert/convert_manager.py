import click
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.dir_convert_managers import *


class ConvertManager:
    MAX_VERSION_SUPPORTED = Version('6.1.0')
    MIN_VERSION_SUPPORTED = Version('5.5.0')

    def __init__(self, input_path: str, server_version: str):
        self.input_path: str = input_path
        self.server_version: Version = Version(server_version)

    def convert(self) -> int:
        """
        Manages the conversions of entities between versions.
        Returns:
            (int): Returns 0 upon success, 1 if failure occurred.
        """
        if not self.server_version_not_supported():
            click.secho(f'Version requested: {str(self.server_version)} should be between '
                        f'{str(self.MIN_VERSION_SUPPORTED)} to {str(self.MAX_VERSION_SUPPORTED)}', fg='red')
            return 1
        pack = self.create_pack_object()
        all_dir_converters = [dir_converter(pack, self.input_path, self.server_version)
                              for dir_converter in AbstractDirConvertManager.__subclasses__()]
        relevant_dir_converters = [dir_converter for dir_converter in all_dir_converters
                                   if dir_converter.should_convert()]
        if not relevant_dir_converters:
            click.secho(f'No entities were found to convert. Please validate your input path is '
                        f'valid: {self.input_path}', fg='red')
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
        pack_path = self.input_path if os.path.basename(path_dir) == PACKS_DIR else path_dir
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
        return (pack_version := pack.metadata.get('serverMinVersion')) and self.server_version >= Version(pack_version)

    def server_version_not_supported(self) -> bool:
        """
        Checks whether the requested version is supported for conversion.
        This is needed to make sure that the requested versions do have a corresponding converter
        before starting the conversion process.
        Returns:
            (bool):
            - True if server version requested for conversion is not supported.
            - False if server version requested for conversion is supported.
        """
        return self.MIN_VERSION_SUPPORTED <= self.server_version <= self.MAX_VERSION_SUPPORTED

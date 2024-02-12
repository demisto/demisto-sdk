from pathlib import Path

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.dir_convert_managers import *  # lgtm [py/polluting-import]


class ConvertManager:
    MIN_VERSION_SUPPORTED = Version("5.5.0")

    def __init__(self, input_path: str, server_version: str):
        self.input_path: str = input_path
        self.server_version: Version = Version(server_version)

    def convert(self) -> int:
        """
        Manages the conversions of entities between versions.
        Returns:
            (int): Returns 0 upon success, 1 if failure occurred.
        """
        if self.MIN_VERSION_SUPPORTED > self.server_version:
            logger.error(
                f"[red]Version requested: {str(self.server_version)} should be higher or equal to "
                f"{str(self.MIN_VERSION_SUPPORTED)}[/red]"
            )
            return 1
        pack = self.create_pack_object()
        all_dir_converters = [
            dir_converter(pack, self.input_path, self.server_version)  # type: ignore[abstract]
            for dir_converter in AbstractDirConvertManager.__subclasses__()
        ]  # type: ignore[abstract]
        relevant_dir_converters = [
            dir_converter
            for dir_converter in all_dir_converters
            if dir_converter.should_convert()
        ]
        if not relevant_dir_converters:
            logger.error(
                f"[red]No entities were found to convert. Please validate your input path is "
                f"valid: {self.input_path}[/red]"
            )
            return 1
        exit_code = 0
        for dir_converter in relevant_dir_converters:
            exit_code = max(dir_converter.convert(), exit_code)
        if exit_code:
            logger.error("[red]Error occurred during convert command.[/red]")
        else:
            logger.info(
                f"[green]Finished convert for given path successfully:\n{self.input_path}[/green]"
            )
        return exit_code

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
        pack_path = (
            self.input_path
            if is_pack_path(self.input_path)
            else Path(self.input_path).parent
        )
        return Pack(pack_path)

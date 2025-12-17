from pathlib import Path
import traceback
from typing import Tuple

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

MIN_FROM_VERSION_LISTS = "6.5.0"


class ListsFormat(BaseUpdateJSON):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "list",
        from_version: str = "",
        no_validate: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            **kwargs,
        )

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the list JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def _should_format_file(self) -> bool:
        """
        Validate if the file should be formatted.
        
        Returns:
            bool: True if the file should be formatted, False otherwise.
        """
        filename = Path(self.source_file).name
        
        if filename.endswith("_data.json"):
            # When downloading a list of type json using the demisto-sdk download command,
            # there are 2 files that will download: one that contains the data and one that contains the metadata.
            # We don't want to format the one that contains the data, which ends with _data.json
            logger.info(
                f"Skipping formatting for {filename} as this is a data file and not a metadata file."
            )
            return False
        
        return True

    def run_format(self) -> int:
        """
        Run the format operation on the list file.
        
        Returns:
            int: SUCCESS_RETURN_CODE if successful, SKIP_RETURN_CODE if skipped,
                 ERROR_RETURN_CODE if an error occurred.
        """
        try:
            if not self._should_format_file():
                return SKIP_RETURN_CODE
            
            logger.info(f"\n======= Updating file: {self.source_file} =======")
            super().update_json(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.LISTS)
            )
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                "".join(
                    traceback.format_exception(
                        type(err), value=err, tb=err.__traceback__
                    )
                )
            )
            logger.error(
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
            )
            return ERROR_RETURN_CODE

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


class PreProcessRulesFormat(BaseUpdateJSON):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "pre-process-rules",
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
        """Manager function for the PreProcessRules JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            logger.info(f"\n======= Updating file: {self.source_file} =======")
            super().update_json(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(
                    FileType.PRE_PROCESS_RULES
                )
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
            logger.debug(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

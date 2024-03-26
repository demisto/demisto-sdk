from typing import Tuple

from demisto_sdk.commands.common.constants import (
    CORRELATION_RULE,
    FILETYPE_TO_DEFAULT_FROMVERSION,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
    FileType,
)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class CorrelationRuleYMLFormat(BaseUpdateYML):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
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
        if isinstance(self.data, list) and len(self.data) == 1:
            self.data = self.data[0]

    def run_format(self):
        try:
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            super().set_fromVersion(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION[
                    FileType.CORRELATION_RULE
                ],
                file_type=CORRELATION_RULE,
            )
            self.save_yml_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

import traceback
from typing import Tuple

import click

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
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
        verbose: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            verbose=verbose,
            **kwargs,
        )
        if isinstance(self.data, list) and len(self.data) == 1:
            self.data = self.data[0]

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the Correlation Rules YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n======= Updating file: {self.source_file} =======", fg="white"
            )
            super().update_yml(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(
                    FileType.CORRELATION_RULE
                )
            )
            self.save_yml_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print(
                "".join(
                    traceback.format_exception(
                        type(err), value=err, tb=err.__traceback__
                    )
                )
            )
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE

from distutils.version import LooseVersion
from typing import Tuple

import click

from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class WidgetJSONFormat(BaseUpdateJSON):
    """WidgetJSONFormat class is designed to update widget JSON file according to Demisto's convention.

    Attributes:
         input (str): the path to the file we are updating at the moment.
         output (str): the desired file name to save the updated version of the JSON to.
    """

    WIDGET_TYPE_METRICS_MIN_VERSION = "6.2.0"

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

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n================= Updating file {self.source_file} =================",
                fg="bright_blue",
            )
            self.update_json()
            self.set_description()
            self.set_isPredefined()
            self.set_from_version_for_type_metrics()
            self.save_json_to_destination_file()

            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the widget JSON updater."""
        format_res = self.run_format()
        return format_res, SKIP_RETURN_CODE

    def set_isPredefined(self):
        """
        isPredefined is a required field for widget.
        If the key does not exist in the json file, a field will be set with true value.

        """
        if not self.data.get("isPredefined"):
            self.data["isPredefined"] = True

    def set_from_version_for_type_metrics(self):

        widget_data_type = self.data.get("dataType", "")
        current_from_version = self.data.get("fromVersion")

        if widget_data_type == "metrics" and LooseVersion(
            current_from_version
        ) < LooseVersion(self.WIDGET_TYPE_METRICS_MIN_VERSION):
            self.data["fromVersion"] = self.WIDGET_TYPE_METRICS_MIN_VERSION

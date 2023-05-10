import re
from typing import Tuple

from demisto_sdk.commands.common.constants import BETA_INTEGRATION_DISCLAIMER
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic import BaseUpdate

CONTRIBUTOR_DETAILED_DESC = "Contributed Integration"


class DescriptionFormat(BaseUpdate):
    """DescriptionFormat class is designed to update integration description file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        update_docker: bool = False,
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
        description_type = input.replace("_description.md", ".yml")
        self.is_beta = False
        file_type = find_type(description_type)
        if file_type:
            self.is_beta = find_type(description_type).value == "betaintegration"
        with open(self.source_file) as f:
            self.description_content = f.read()

    def remove_community_partner_details(self):
        """update description file to not contain community/partner details"""

        formatted_description = re.sub(
            "###.*Contributed Integration[\\S\n ]+?[*]{3}[\n]*",
            "",
            self.description_content,
        )
        self.description_content = formatted_description.rstrip("\n")

    def add_betaintegration_description(self):
        """update description file of a beta integration to contain beta integration's description"""
        if BETA_INTEGRATION_DISCLAIMER not in self.description_content:
            self.description_content = (
                BETA_INTEGRATION_DISCLAIMER + "\n" + self.description_content
            )

    def save_md_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        if self.source_file != self.output_file:
            logger.debug(f"Saving output description file to {self.output_file} \n")
        with open(self.output_file, "w") as f:
            f.write(self.description_content)
        f.close()

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            self.remove_community_partner_details()
            if self.is_beta:
                self.add_betaintegration_description()
            self.save_md_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.debug(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration description updater."""

        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator()

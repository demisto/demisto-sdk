from typing import Optional, Tuple

import click

from demisto_sdk.commands.common.hook_validations.readme import (
    ReadmeUrl,
    get_relative_urls,
)
from demisto_sdk.commands.common.tools import print_error
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic import BaseUpdate


class ReadmeFormat(BaseUpdate):
    """ReadmeFormat class is designed to update README files according to Demisto's convention.
    This is relevant for pack, Integrations, scripts and playbooks README files.

     Attributes:
         input (str): the path to the file we are updating at the moment.
         output_file (str): the desired file name to save the updated version to.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        no_validate: bool = False,
        verbose: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            no_validate=no_validate,
            verbose=verbose,
            **kwargs,
        )
        with open(self.source_file) as f:
            self.readme_content = f.read()

    def replace_url_in_content(self, relative_url: ReadmeUrl, new_url: str):
        """Replace the relative url link with the new url in README."""

        old_link = relative_url.get_full_link()
        new_link = relative_url.get_new_link(new_url)
        self.readme_content = str.replace(self.readme_content, old_link, new_link)
        click.secho(f"Replaced {relative_url.get_url()} with {new_url}")

    def get_new_url_from_user(self, readme_url: ReadmeUrl) -> Optional[str]:
        """Given we found a relative url, the user has the following options-
        1. Add https:// prefix.
        2. Enter a new absolute address to replace the current.
        3. Leave as is

        Args:
            readme_url: relative url found in README

        Returns: new url or None if we leave as is

        """
        old_url = str.strip(readme_url.get_url())
        new_address = None
        if self.assume_yes:
            return f"https://{old_url}"
        else:
            click.secho(
                f"Should https:// be added to the following address? [Y/n]\n {readme_url.get_url()}",
                fg="red",
            )
            user_answer = input()
            if user_answer.lower()[0] == "y":
                new_address = f"https://{old_url}"
            else:
                click.secho(
                    "Would you like to change the relative address to something else?\n"
                    " Enter the new address or leave empty to skip:",
                    fg="red",
                )
                user_answer = input()
                if user_answer and user_answer.lower() not in ["n", "no"]:
                    new_address = user_answer
        return new_address

    def relative_url_format(self):
        """Find all relative url links in README,
            And prompt the user for following options-
        1. Add https:// prefix.
        2. Enter a new absolute address to replace the current.
        3. Leave as is
        """

        relative_urls = get_relative_urls(self.readme_content)

        if relative_urls:
            click.secho(
                "Relative urls were found and are not supported within README.",
                fg="red",
            )
        for url in relative_urls:
            new_address = self.get_new_url_from_user(url)
            if new_address:
                self.replace_url_in_content(url, new_address)

    def save_md_to_destination_file(self):
        """Safely saves formatted data to destination file."""
        if self.source_file != self.output_file and self.verbose:
            click.secho(
                f"Saving output description file to {self.output_file} \n", fg="white"
            )
        with open(self.output_file, "w") as f:
            f.write(self.readme_content)
        f.close()

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n================= Updating file {self.source_file} ================= ",
                fg="bright_blue",
            )
            self.relative_url_format()
            self.save_md_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print_error(f"\nFailed to update file {self.source_file}. Error: {err}")
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the README updater."""

        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

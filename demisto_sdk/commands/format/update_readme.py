from typing import Optional, Tuple

from demisto_sdk.commands.common.hook_validations.readme import (
    ReadmeUrl,
    get_relative_urls,
    mdx_server_is_up,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
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
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            no_validate=no_validate,
            **kwargs,
        )
        with open(self.source_file) as f:
            self.readme_content = f.read()

    def replace_url_in_content(self, relative_url: ReadmeUrl, new_url: str):
        """Replace the relative url link with the new url in README."""

        old_link = relative_url.get_full_link()
        new_link = relative_url.get_new_link(new_url)
        self.readme_content = str.replace(self.readme_content, old_link, new_link)
        logger.info(f"Replaced {relative_url.get_url()} with {new_url}")

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
        if self.assume_answer:
            return f"https://{old_url}"
        elif self.assume_answer is False:
            return None
        else:
            logger.info(
                f"[red]Should https:// be added to the following address? [Y/n]\n {readme_url.get_url()}[/red]"
            )
            user_answer = input()
            if user_answer.lower()[0] == "y":
                new_address = f"https://{old_url}"
            else:
                logger.info(
                    "[red]Would you like to change the relative address to something else?\n"
                    " Enter the new address or leave empty to skip:[/red]"
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
            logger.info(
                "[red]Relative urls were found and are not supported within README.[/red]"
            )
        for url in relative_urls:
            new_address = self.get_new_url_from_user(url)
            if new_address:
                self.replace_url_in_content(url, new_address)

    def save_md_to_destination_file(self):
        """Safely saves formatted data to destination file."""
        if self.source_file != self.output_file:
            logger.debug(f"Saving output description file to {self.output_file} \n")
        with open(self.output_file, "w") as f:
            f.write(self.readme_content)
        f.close()

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            self.relative_url_format()
            self.fix_lint_markdown()
            self.save_md_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the README updater."""

        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def fix_lint_markdown(self):
        if mdx_server_is_up():
            if self.readme_content:
                response = run_markdownlint(
                    file_path=self.source_file,
                    file_content=self.readme_content,
                    fix=True,
                )
                if response.validations:
                    logger.info(
                        f"[yellow]Markdown lint was not able to fix the following "
                        f"markdown validations for file {self.source_file}.\n{response.validations}[/yellow]"
                    )
                if response.fixed_text and response.fixed_text != self.readme_content:
                    logger.info(f"Received markdown fixes for file {self.source_file}")
                    self.readme_content = response.fixed_text
            else:
                logger.info(f"Markdownlint skipping {self.source_file} with no content")
        else:
            logger.info("Skipping markdownlint as node server is not up")

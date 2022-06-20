import re
from typing import List, Optional, Tuple

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.common.hook_validations.readme import UrlLink, get_relative_urls


class ReadmeFormat(BaseUpdate):
    """ReadmeFormat class is designed to update README files according to Demisto's convention.
       This is relevant for pack, Integrations, scripts and playbooks README files.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output_file (str): the desired file name to save the updated version to.
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, no_validate=no_validate,
                         verbose=verbose, **kwargs)
        with open(self.source_file, 'r') as f:
            self.readme_content = f.read()

    def replace_url_in_content(self, relative_url: list, new_url: str):
        """Replace the relative url link with the new url in README."""

        # md link
        if '[' in relative_url[0]:
            old_link = relative_url[0] + '(' + relative_url[1] + ')'
            new_link = relative_url[0] + '(' + new_url + ')'
        # href link
        else:
            old_link = relative_url[0]
            new_link = str.replace(relative_url[0], relative_url[1], new_url, 1)

        self.readme_content = str.replace(self.readme_content, old_link, new_link, 1)
        click.secho(f'Replaced {relative_url[1]} with {new_url}')

    # def get_relative_urls(self) -> List[list]:
    #     """
    #     Find all relative urls (md link and href links_ in README.
    #     Returns: a regex list of urls.
    #
    #     """
    #     relative_urls = re.findall(RELATIVE_MARKDOWN_URL_REGEX, self.readme_content,
    #                                re.IGNORECASE | re.MULTILINE)
    #     relative_urls += re.findall(RELATIVE_HREF_URL_REGEX, self.readme_content,
    #                                 re.IGNORECASE | re.MULTILINE)
    #     relative_urls = [url for url in relative_urls if url[1]]
    #     return relative_urls

    def get_new_url_from_user(self, url_link: UrlLink) -> Optional[str]:
        """ Given we found a relative url, the user has the following options-
        1. Add https:// prefix.
        2. Enter a new absolute address to replace the current.
        3. Leave as is

        Args:
            url: relative url found in README

        Returns: new url or None if we leave as is

        """
        old_url = str.strip(url_link.url)
        new_address = None
        if self.assume_yes:
            new_address = f'https://{old_url}'
        else:
            click.secho(f'Relative urls are not supported within README, Should https:// be added to the '
                        f'following address? [Y/n]\n {url_link.url}',
                        fg='red')
            user_answer = input()
            if user_answer in ['y', 'Y', 'yes', 'Yes']:
                new_address = f'https://{old_url}'
            else:
                click.secho('Would you like to change the relative address to something else?\n'
                            ' Enter the new address or leave empty to skip:',
                            fg='red')
                user_answer = input()
                if user_answer and user_answer not in ['n', 'N', 'No', 'no']:
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

        for url in relative_urls:
            new_address = self.get_new_url_from_user(url)
            if new_address:
                self.replace_url_in_content(url, new_address)

    def save_md_to_destination_file(self):
        """Safely saves formatted data to destination file."""
        if self.source_file != self.output_file and self.verbose:
            click.secho(f'Saving output description file to {self.output_file} \n', fg='white')
        with open(self.output_file, 'w') as f:
            f.write(self.readme_content)
        f.close()

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} ================= ', fg='bright_blue')
            self.relative_url_format()
            self.save_md_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the README updater."""

        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

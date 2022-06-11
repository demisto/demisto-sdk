import logging
import os

import click

from demisto_sdk.commands.common.content.objects.custom_pack_objects.deprecated_pack_content_items import \
    DeprecatedPackContentItems
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

logger = logging.getLogger('demisto-sdk')


class PackMetadataJsonFormat(BaseUpdateJSON):

    def __init__(
        self,
        input: str = '',
        output: str = '',
        path: str = '',
        from_version: str = '',
        no_validate: bool = False,
        verbose: bool = False,
        clear_cache: bool = False,
        **kwargs
    ):
        super().__init__(
            input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
            verbose=verbose, clear_cache=clear_cache, **kwargs
        )

    def format_file(self):
        """
        Manager function for the pack-metadata JSON updater.
        """
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            self.hide_pack()
            self.save_json_to_destination_file(encode_html_chars=False)
            return SUCCESS_RETURN_CODE

        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def hide_pack(self):
        """
        Hide the in which the pack_metadata.json is in if the following rules appear:

        1. if the pack is not already hidden.
        2. If the pack has integrations and all integrations are deprecated -> pack should be hidden.
        3. if pack does not have integrations and all scripts and PBs are deprecated -> pack should be hidden.
        """
        deprecated_pack_content_items = DeprecatedPackContentItems(os.path.dirname(self.source_file))
        if deprecated_pack_content_items.should_pack_be_hidden():
            self.data['hidden'] = True

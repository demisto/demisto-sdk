import os

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class PackMetadataJsonFormat(BaseUpdateJSON):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        clear_cache: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            clear_cache=clear_cache,
            **kwargs,
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
            logger.info(
                f"\n[blue]================= Updating file {self.source_file} =================[/blue]"
            )
            self.deprecate_pack()
            self.save_json_to_destination_file(encode_html_chars=False)
            return SUCCESS_RETURN_CODE

        except Exception as err:
            logger.debug(
                f"\n[red]Failed to update file {self.source_file}. Error: {err}[/red]"
            )
            return ERROR_RETURN_CODE

    def deprecate_pack(self):
        """
        Deprecate the pack if all the content items (playbooks/scripts/integrations) are deprecated.
        """
        pack = Pack(os.path.dirname(self.source_file))
        if pack.should_be_deprecated():
            current_pack_name = (self.data.get("name") or "").strip()
            new_pack_name_to_use = self.get_answer(
                f"Please provide the pack name to use instead of {current_pack_name}. "
                f'if not provided, the "Deprecated. No available replacement." will be generated automatically.'
            )
            if not new_pack_name_to_use or new_pack_name_to_use.isspace():
                description = "Deprecated. No available replacement."
            else:
                description = f"Deprecated. Use {new_pack_name_to_use.strip()} instead."
            self.data["name"] = f"{current_pack_name} (Deprecated)"
            self.data["description"] = description

from typing import Optional, Tuple

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    TYPE_JS,
    TYPE_PWSH,
    FileType,
)
from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import is_iron_bank_pack, server_version_compare
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class ScriptYMLFormat(BaseUpdateYML):
    """ScriptYMLFormat class is designed to update script YML file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        update_docker: bool = False,
        add_tests: bool = False,
        **kwargs,
    ):
        super().__init__(
            input,
            output,
            path,
            from_version,
            no_validate,
            add_tests=add_tests,
            **kwargs,
        )
        self.update_docker = update_docker

        if not from_version and self.data.get("type") == TYPE_PWSH:
            self.from_version = "5.5.0"

    @staticmethod
    def update_docker_image_in_script(
        script_obj: dict, file_path: str, from_version: Optional[str] = None
    ):
        """Update the docker image for the passed script object. Will ignore if this is a javascript
        object or using default image (not set).

        Args:
            script_obj (dict): script object
        """
        if script_obj.get("type") == TYPE_JS:
            logger.info(
                "<yellow>Skipping docker image update as this is a Javascript automation.</yellow>"
            )
            return
        dockerimage = script_obj.get("dockerimage")
        if not dockerimage:  # default image -> nothing to do
            logger.info(
                "<yellow>Skipping docker image update as default docker image is being used.</yellow>"
            )
            return
        image_name = dockerimage.split(":")[0]
        try:
            if is_iron_bank_pack(file_path):
                latest_tag = DockerImageValidator.get_docker_image_latest_tag_from_iron_bank_request(
                    image_name
                )
            else:
                latest_tag = DockerImageValidator.get_docker_image_latest_tag_request(
                    image_name
                )
            if not latest_tag:
                logger.info("<yellow>Failed getting docker image latest tag</yellow>")
                return
        except Exception as e:
            logger.info(
                f"<yellow>Failed getting docker image latest tag. {e} - Invalid docker image</yellow>"
            )
            return
        full_name = f"{image_name}:{latest_tag}"
        if full_name != dockerimage:
            logger.info(f"Updating docker image to: {full_name}")
            script_obj["dockerimage"] = full_name
            if (not from_version) or server_version_compare("5.0.0", from_version) > 0:
                # if this is a script that supports 4.5 and earlier. Make sure dockerimage45 is set
                if not script_obj.get("dockerimage45"):
                    logger.info(
                        f"Setting dockerimage45 to previous image value: {dockerimage} for 4.5 and earlier support"
                    )
                    script_obj["dockerimage45"] = dockerimage
        else:
            logger.info(
                f"Already using latest docker image: {dockerimage}. Nothing to update."
            )

    def update_docker_image(self):
        if self.update_docker:
            self.update_docker_image_in_script(
                self.data, self.source_file, self.data.get(self.from_version_key)
            )

    def run_format(self) -> int:
        try:
            logger.info(
                f"\n<blue>================= Updating file {self.source_file} =================</blue>"
            )
            super().update_yml(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION[FileType.SCRIPT],
            )
            self.update_tests()
            self.update_docker_image()
            self.save_yml_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
            )
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

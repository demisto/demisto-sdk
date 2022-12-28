import os
import shutil
import tempfile

from demisto_sdk.commands.common.constants import (
    ENV_DEMISTO_SDK_MARKETPLACE,
    MarketplaceVersions,
)
from demisto_sdk.utils.utils import check_configuration_file


def upload_content_entity(**kwargs):
    from demisto_sdk.commands.upload.uploader import ConfigFileParser, Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import EX_FAIL, PacksZipper

    keep_zip = kwargs.pop("keep_zip")
    is_zip = kwargs.pop("zip", False)
    config_file_path = kwargs.pop("input_config_file")
    is_xsiam = kwargs.pop("xsiam", False)
    if is_zip or config_file_path:
        if is_zip:
            pack_path = kwargs["input"]

        else:
            config_file_to_parse = ConfigFileParser(config_file_path=config_file_path)
            pack_path = config_file_to_parse.parse_file()
            kwargs["detached_files"] = True
        if is_xsiam:
            marketplace = MarketplaceVersions.MarketplaceV2.value
        else:
            marketplace = MarketplaceVersions.XSOAR.value
        os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()

        output_zip_path = keep_zip or tempfile.mkdtemp()
        packs_unifier = PacksZipper(
            pack_paths=pack_path,
            output=output_zip_path,
            content_version="0.0.0",
            zip_all=True,
            quiet_mode=True,
            marketplace=marketplace,
        )
        packs_zip_path, pack_names = packs_unifier.zip_packs()
        if packs_zip_path is None and not kwargs.get("detached_files"):
            return EX_FAIL

        kwargs["input"] = packs_zip_path
        kwargs["pack_names"] = pack_names

    check_configuration_file("upload", kwargs)
    upload_result = Uploader(**kwargs).upload()
    if (is_zip or config_file_path) and not keep_zip:
        shutil.rmtree(output_zip_path, ignore_errors=True)
    return upload_result

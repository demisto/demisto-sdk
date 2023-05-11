import logging
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Iterable

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import parse_marketplace_kwargs
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.utils.utils import check_configuration_file

logger = logging.getLogger("demisto-sdk")

MULTIPLE_ZIPPED_PACKS_FILE_NAME = "uploadable_packs.zip"


def upload_content_entity(**kwargs):
    from demisto_sdk.commands.upload.uploader import ConfigFileParser, Uploader

    keep_zip = kwargs.pop("keep_zip", None)

    marketplace: MarketplaceVersions = parse_marketplace_kwargs(kwargs)

    if config_file_path := kwargs.pop("input_config_file", None):
        logger.info("Uploading files from config file")
        if input_ := kwargs.get("input"):
            logger.warning(f"[orange]The input ({input_}) will NOT be used[/orange]")

        output_zip_path = keep_zip or tempfile.mkdtemp()

        zip_multiple_packs(
            paths=ConfigFileParser(Path(config_file_path)).custom_packs_paths,
            marketplace=marketplace,
            dir=Path(output_zip_path),
        )
        kwargs["detached_files"] = True
        kwargs["input"] = Path(output_zip_path, MULTIPLE_ZIPPED_PACKS_FILE_NAME)

    check_configuration_file("upload", kwargs)

    # Here the magic happens
    upload_result = Uploader(marketplace=marketplace, **kwargs).upload()

    # Clean up
    if config_file_path and not keep_zip:
        shutil.rmtree(output_zip_path, ignore_errors=True)

    return upload_result


def zip_multiple_packs(
    paths: Iterable[Path],
    marketplace: MarketplaceVersions,
    dir: DirectoryPath,
):
    for path in paths:
        if not path.exists():
            logger.error(f"[red]{path} does not exist, skipping[/red]")
            continue

        if path.is_file() and path.suffix == ".zip":
            # zipped pack
            shutil.copy(src=path, dst=dir)
            continue

        pack = None
        with suppress(Exception):
            pack = BaseContent.from_path(path)
        if (pack is None) or (not isinstance(pack, Pack)):
            logger.error(f"[red]could not parse pack from {path}, skipping[/red]")
            continue

        pack.dump(dir, marketplace)  # dump into a zip

    shutil.make_archive(
        str((dir / Path(MULTIPLE_ZIPPED_PACKS_FILE_NAME).stem)), "zip", str(dir)
    )

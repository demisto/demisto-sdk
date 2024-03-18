import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Iterable, List, Sequence
from zipfile import ZipFile

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    parse_marketplace_kwargs,
    parse_multiple_path_inputs,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.upload.constants import (
    MULTIPLE_ZIPPED_PACKS_FILE_NAME,
)
from demisto_sdk.commands.upload.uploader import (
    ABORTED_RETURN_CODE,
    ERROR_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.utils.utils import check_configuration_file


def upload_content_entity(**kwargs):
    from demisto_sdk.commands.upload.uploader import ConfigFileParser, Uploader

    inputs = parse_multiple_path_inputs(kwargs.get("input"))

    keep_zip = kwargs.pop("keep_zip", None)
    destination_zip_path = Path(keep_zip or tempfile.mkdtemp())
    marketplace = parse_marketplace_kwargs(kwargs)

    if config_file_path := kwargs.pop("input_config_file", None):
        logger.info("Uploading files from config file")
        if input_ := kwargs.get("input"):
            logger.warning(f"[orange]The input ({input_}) will NOT be used[/orange]")

        paths = ConfigFileParser(Path(config_file_path)).custom_packs_paths

        if not kwargs.get("zip") and are_all_packs_unzipped(paths=paths):
            inputs = paths
        else:
            pack_names = zip_multiple_packs(
                paths=paths,
                marketplace=marketplace,
                dir=destination_zip_path,
            )
            kwargs["detached_files"] = True
            kwargs["pack_names"] = pack_names
            inputs = tuple(
                [Path(destination_zip_path, MULTIPLE_ZIPPED_PACKS_FILE_NAME)]
            )

    check_configuration_file("upload", kwargs)

    if not inputs:
        logger.error("[red]No input provided for uploading[/red]")
        return ERROR_RETURN_CODE

    kwargs.pop("input")
    # Here the magic happens
    upload_result = SUCCESS_RETURN_CODE
    for input in inputs:
        result = Uploader(
            input=input,
            marketplace=marketplace,
            destination_zip_dir=destination_zip_path,
            **kwargs,
        ).upload()
        if result == ABORTED_RETURN_CODE:
            return result
        elif result == ERROR_RETURN_CODE:
            upload_result = ERROR_RETURN_CODE

    # Clean up
    if not keep_zip:
        shutil.rmtree(destination_zip_path, ignore_errors=True)

    return upload_result


def zip_multiple_packs(
    paths: Iterable[Path],
    marketplace: MarketplaceVersions,
    dir: DirectoryPath,
) -> Sequence[str]:
    packs: List[Pack] = []
    were_zipped: List[Path] = []

    for path in paths:
        if not path.exists():
            logger.error(f"[red]{path} does not exist, skipping[/red]")
            continue

        if path.is_file() and path.suffix == ".zip":
            were_zipped.append(path)
            continue

        pack = None
        with suppress(Exception):
            pack = BaseContent.from_path(path)
        if (pack is None) or (not isinstance(pack, Pack)):
            logger.error(f"[red]could not parse pack from {path}, skipping[/red]")
            continue
        packs.append(pack)

    result_zip_path = dir / MULTIPLE_ZIPPED_PACKS_FILE_NAME
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        ContentDTO(packs=packs).dump(tmp_dir_path, marketplace=marketplace, zip=False)
        with ZipFile(result_zip_path, "w") as zip_file:
            # copy files that were already zipped into the result
            for was_zipped in were_zipped:
                zip_file.write(was_zipped, was_zipped.name)
            for pack_path in tmp_dir_path.iterdir():
                shutil.make_archive(str(pack_path), "zip", pack_path)
                zip_file.write(pack_path.with_suffix(".zip"), f"{pack_path.name}.zip")

    return [pack.name for pack in packs] + [path.name for path in were_zipped]


def are_all_packs_unzipped(paths: Iterable[Path]) -> bool:
    """
    Checks whether all the packs intended to be uploaded are not zip files.
    """
    return not tuple(filter(lambda path: path.suffix == ".zip", paths))

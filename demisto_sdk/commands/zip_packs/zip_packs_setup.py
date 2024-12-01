from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import parse_marketplace_kwargs
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def zip_packs(
    ctx: typer.Context,
    input: str = typer.Option(
        ..., "-i", "--input", help="The packs to be zipped as csv list of pack paths."
    ),
    output: str = typer.Option(
        ...,
        "-o",
        "--output",
        help="The destination directory to create the packs.",
        resolve_path=True,
    ),
    content_version: str = typer.Option(
        "0.0.0",
        "-c",
        "--content-version",
        help="The content version in CommonServerPython.",
    ),
    upload: bool = typer.Option(
        False, "-u", "--upload", help="Upload the unified packs to the marketplace."
    ),
    zip_all: bool = typer.Option(False, help="Zip all the packs in one zip file."),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
):
    """
    Creates a zip file that can be uploaded to Cortex XSOAR via the Upload pack button in the Cortex XSOAR Marketplace or directly with the -u flag in this command.
    """
    from demisto_sdk.commands.upload.uploader import Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (
        EX_FAIL,
        EX_SUCCESS,
        PacksZipper,
    )

    update_command_args_from_config_file("zip-packs", locals())

    should_upload = upload
    zip_all = zip_all or should_upload
    marketplace = parse_marketplace_kwargs(locals())

    packs_zipper = PacksZipper(
        zip_all=zip_all,
        pack_paths=input,
        output=output,
        quiet_mode=zip_all,
        content_version=content_version,
    )
    zip_path, unified_pack_names = packs_zipper.zip_packs()

    if should_upload and zip_path:
        return Uploader(
            input=Path(zip_path), pack_names=unified_pack_names, marketplace=marketplace
        ).upload()

    return EX_SUCCESS if zip_path is not None else EX_FAIL

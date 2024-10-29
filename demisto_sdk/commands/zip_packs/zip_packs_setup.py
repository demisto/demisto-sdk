from pathlib import Path
from typing import List
import typer

from demisto_sdk.commands.common.tools import parse_marketplace_kwargs
from demisto_sdk.utils.utils import update_command_args_from_config_file

zip_packs_app = typer.Typer()


@zip_packs_app.command()
def zip_packs(
    input: List[str] = typer.Option(..., help="The packs to be zipped as a list of pack paths."),
    output: str = typer.Option(..., help="The destination directory to create the packs.", resolve_path=True),
    content_version: str = typer.Option("0.0.0", help="The content version in CommonServerPython."),
    upload: bool = typer.Option(False, help="Upload the unified packs to the marketplace."),
    zip_all: bool = typer.Option(False, help="Zip all the packs in one zip file."),
):
    """Generating zipped packs that are ready to be uploaded to Cortex XSOAR machine."""
    from demisto_sdk.commands.upload.uploader import Uploader
    from demisto_sdk.commands.zip_packs.packs_zipper import (
        EX_FAIL,
        EX_SUCCESS,
        PacksZipper,
    )

    # Update command args from config file if needed
    update_command_args_from_config_file("zip-packs", locals())

    should_upload = upload
    zip_all = zip_all or should_upload
    marketplace = parse_marketplace_kwargs(locals())  # Replace with appropriate function if needed

    packs_zipper = PacksZipper(
        zip_all=zip_all,
        pack_paths=input,
        output=output,
        quiet_mode=zip_all,
        content_version=content_version
    )
    zip_path, unified_pack_names = packs_zipper.zip_packs()

    if should_upload and zip_path:
        return Uploader(
            input=Path(zip_path), pack_names=unified_pack_names, marketplace=marketplace
        ).upload()

    return EX_SUCCESS if zip_path is not None else EX_FAIL


if __name__ == "__main__":
    zip_packs_app()

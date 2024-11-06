import os
from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import FileType, MarketplaceVersions
from demisto_sdk.commands.common.tools import find_type, parse_marketplace_kwargs
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.prepare_content.generic_module_unifier import (
    GenericModuleUnifier,
)
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)
from demisto_sdk.utils.utils import update_command_args_from_config_file
from demisto_sdk.commands.common.configuration import sdk


def prepare_content(
    input: str = typer.Option(
        None, help="Comma-separated list of paths to directories or files to unify."
    ),
    all: bool = typer.Option(
        False,
        is_flag=True,
        help="Run prepare-content on all content packs. If no output path is given, "
        "will dump the result in the current working path.",
    ),
    graph: bool = typer.Option(
        False, is_flag=True, help="Whether to use the content graph"
    ),
    skip_update: bool = typer.Option(
        False,
        is_flag=True,
        help="Whether to skip updating the content graph "
        "(used only when graph is true)",
    ),
    output: Path = typer.Option(
        None, help="The output dir to write the unified YML to"
    ),
    custom: str = typer.Option(
        None, help="Add test label to unified YML id/name/display"
    ),
    force: bool = typer.Option(
        False,
        is_flag=True,
        help="Forcefully overwrites the preexisting YML if one exists",
    ),
    ignore_native_image: bool = typer.Option(
        False,
        is_flag=True,
        help="Whether to ignore the addition of the native image key to "
        "the YML of a script/integration",
    ),
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        help="The marketplace the content items are created for, "
        "that determines usage of marketplace unique text.",
    ),
):
    """
    This command is used to prepare the content to be used in the platform.
    """
    assert (
        sum([bool(all), bool(input)]) == 1
    ), "Exactly one of the '-a' or '-i' parameters must be provided."

    if all:
        content_dto = ContentDTO.from_path()
        output_path = output or Path(".")
        content_dto.dump(
            dir=Path(output_path, "prepare-content-tmp"),
            marketplace=parse_marketplace_kwargs({"marketplace": marketplace}),
        )
        return

    inputs = input.split(",") if input else []

    if output_path := output:
        if "." in Path(output_path).name:  # Check if the output path is a file
            if len(inputs) > 1:
                raise ValueError(
                    "When passing multiple inputs, the output path should be a directory and not a file."
                )
        else:
            dest_path = Path(output_path)
            dest_path.mkdir(exist_ok=True)

    for input_content in inputs:
        if output_path and len(inputs) > 1:
            path_name = Path(input_content).name
            output = Path(output_path, path_name)

        # Update kwargs for the current context
        update_command_args_from_config_file("unify", locals())

        # Input is of type Path.
        locals()["input"] = str(input_content)
        file_type = find_type(locals()["input"])

        os.environ["ENV_DEMISTO_SDK_MARKETPLACE"] = (
            marketplace.lower() if marketplace else ""
        )

        if file_type == FileType.GENERIC_MODULE:
            # Pass arguments to GenericModuleUnifier and call the command
            generic_module_unifier = GenericModuleUnifier(**locals())
            generic_module_unifier.merge_generic_module_with_its_dashboards()
        else:
            PrepareUploadManager.prepare_for_upload(**locals())
    return

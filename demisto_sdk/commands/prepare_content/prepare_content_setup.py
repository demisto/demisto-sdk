import os
from pathlib import Path

import typer

from demisto_sdk.commands.common.constants import (
    ENV_DEMISTO_SDK_MARKETPLACE,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import find_type, parse_marketplace_kwargs
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.prepare_content.generic_module_unifier import (
    GenericModuleUnifier,
)
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def prepare_content(
    ctx: typer.Context,
    input: str = typer.Option(
        None,
        "-i",
        "--input",
        help="Comma-separated list of paths to directories or files to unify.",
    ),
    all: bool = typer.Option(
        False,
        "-a",
        "--all",
        is_flag=True,
        help="Run prepare-content on all content packs. If no output path is given, "
        "will dump the result in the current working path.",
    ),
    graph: bool = typer.Option(
        False, "-g", "--graph", is_flag=True, help="Whether to use the content graph"
    ),
    skip_update: bool = typer.Option(
        False,
        is_flag=True,
        help="Whether to skip updating the content graph "
        "(used only when graph is true)",
    ),
    output: Path = typer.Option(
        None, "-o", "--output", help="The output dir to write the unified YML to"
    ),
    custom: str = typer.Option(
        None, "-c", "--custom", help="Add test label to unified YML id/name/display"
    ),
    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        is_flag=True,
        help="Forcefully overwrites the preexisting YML if one exists",
    ),
    ignore_native_image: bool = typer.Option(
        False,
        "-ini",
        "--ignore-native-image",
        is_flag=True,
        help="Whether to ignore the addition of the native image key to "
        "the YML of a script/integration",
    ),
    marketplace: MarketplaceVersions = typer.Option(
        MarketplaceVersions.XSOAR,
        "-mp",
        "--marketplace",
        help="The marketplace the content items are created for, "
        "that determines usage of marketplace unique text.",
    ),
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
    This command prepares content to upload to the platform. If the content item is a pack, prepare-content creates the pack zip file. If the content item is an integration/script/rule, prepare-content creates the unified YAML file.

    NOTE: The prepare-content command replaces the unify command.
    """
    assert (
        sum([bool(all), bool(input)]) == 1
    ), "Exactly one of '-a' or '-i' must be provided."

    # Process `all` option
    if all:
        content_dto = ContentDTO.from_path()
        output_path = output or Path(".")
        content_dto.dump(
            dir=output_path / "prepare-content-tmp",
            marketplace=parse_marketplace_kwargs({"marketplace": marketplace}),
        )
        raise typer.Exit(0)

    # Split and process inputs
    inputs = input.split(",") if input else []
    output_path = output if output else Path(".")

    if output_path:
        if "." in Path(output_path).name:  # check if the output path is a file
            if len(inputs) > 1:
                raise ValueError(
                    "When passing multiple inputs, the output path should be a directory and not a file."
                )
    elif not output_path.is_file():
        output_path.mkdir(exist_ok=True)

    # Iterate through each input and process it
    for input_content in inputs:
        ctx.params["input"] = input_content  # Update `input` for the current loop
        ctx.params["output"] = (
            str(output_path / Path(input_content).name) if len(inputs) > 1 else output
        )

        # Update command args with additional configurations
        update_command_args_from_config_file("unify", ctx.params)

        file_type = find_type(input_content)
        if marketplace:
            os.environ[ENV_DEMISTO_SDK_MARKETPLACE] = marketplace.lower()

        # Execute the appropriate unification method
        if file_type == FileType.GENERIC_MODULE:
            generic_module_unifier = GenericModuleUnifier(**ctx.params)
            generic_module_unifier.merge_generic_module_with_its_dashboards()
        else:
            PrepareUploadManager.prepare_for_upload(**ctx.params)

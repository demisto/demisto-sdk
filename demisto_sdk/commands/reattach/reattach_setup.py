from typing import List

import typer

from demisto_sdk.commands.common.constants import DetachableItemType
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.reattach.reattach import reattach_content_items


@logging_setup_decorator
def reattach(
    ctx: typer.Context,
    input: List[str] = typer.Option(
        [],
        "--input",
        "-i",
        help="The ID of the content item to reattach. Can be used multiple times.",
    ),
    item_type: DetachableItemType = typer.Option(
        None,
        "--item-type",
        "-it",
        help="The type of the content items to reattach.",
        case_sensitive=False,
    ),
    reattach_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Reattach all detached items for all content types in the XSOAR instance.",
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Skip certificate validation."
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
    ** Reattach content items to Cortex XSOAR/XSIAM.**
    """
    if not reattach_all and not input:
        typer.echo(
            "Error: Missing option '--input' / '-i' or '--all' / '-a'.", err=True
        )
        raise typer.Exit(code=1)
    if reattach_all and input:
        typer.echo("Error: Cannot use '--input' / '-i' with '--all' / '-a'.", err=True)
        raise typer.Exit(code=1)

    if input and not item_type:
        typer.echo(
            "Error: Missing option '--item-type' / '-it' when using '--input'.",
            err=True,
        )
        raise typer.Exit(code=1)

    reattach_content_items(
        ids=input,
        item_type=item_type.value if item_type else None,
        insecure=insecure,
        reattach_all=reattach_all,
    )

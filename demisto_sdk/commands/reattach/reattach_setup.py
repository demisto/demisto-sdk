from typing import List

import typer

from demisto_sdk.commands.common.constants import DetachableItemType
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.reattach.reattach import reattach_content_items


@logging_setup_decorator
def reattach(
    ctx: typer.Context,
    input: List[str] = typer.Option(
        ...,
        "--input",
        "-i",
        help="The ID of the content item to reattach. Can be used multiple times.",
    ),
    item_type: DetachableItemType = typer.Option(
        ...,
        "--item-type",
        "-it",
        help="The type of the content items to reattach.",
        case_sensitive=False,
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
    reattach_content_items(
        ids=input,
        item_type=item_type.value,
        insecure=insecure,
    )

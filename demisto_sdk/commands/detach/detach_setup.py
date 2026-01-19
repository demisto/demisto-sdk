from typing import List

import typer

from demisto_sdk.commands.common.constants import DetachableItemType
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.detach.detach import detach_content_items


@logging_setup_decorator
def detach(
    ctx: typer.Context,
    input: List[str] = typer.Option(
        ...,
        "--input",
        "-i",
        help="The ID of the content item to detach. Can be used multiple times.",
    ),
    item_type: DetachableItemType = typer.Option(
        ...,
        "--item-type",
        "-it",
        help="The type of the content items to detach.",
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
    ** Detach content items from Cortex XSOAR/XSIAM.**
    """
    detach_content_items(
        ids=input,
        item_type=item_type.value,
        insecure=insecure,
    )

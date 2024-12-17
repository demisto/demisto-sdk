from enum import Enum
from pathlib import Path
from typing import List

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator


class ItemType(str, Enum):
    incident_type = "IncidentType"
    indicator_type = "IndicatorType"
    field = "Field"
    layout = "Layout"
    playbook = "Playbook"
    automation = "Automation"
    classifier = "Classifier"
    mapper = "Mapper"


@logging_setup_decorator
def download(
    ctx: typer.Context,
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="A path to a pack directory to download content to.",
    ),
    input: List[str] = typer.Option(
        None,
        "--input",
        "-i",
        help="Name of a custom content item to download. Can be used multiple times.",
    ),
    regex: str = typer.Option(
        None,
        "--regex",
        "-r",
        help="Download all custom content items matching this RegEx pattern.",
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Skip certificate validation."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing content in the output directory.",
    ),
    list_files: bool = typer.Option(
        False,
        "--list-files",
        "-lf",
        help="List all custom content items available to download and exit.",
    ),
    all_custom_content: bool = typer.Option(
        False,
        "--all-custom-content",
        "-a",
        help="Download all available custom content items.",
    ),
    run_format: bool = typer.Option(
        False, "--run-format", "-fmt", help="Format downloaded files."
    ),
    system: bool = typer.Option(False, "--system", help="Download system items."),
    item_type: ItemType = typer.Option(
        None,
        "--item-type",
        "-it",
        help="Type of the content item to download. Required and used only when downloading system items.",
        case_sensitive=False,
    ),
    init: bool = typer.Option(
        False, "--init", help="Initialize the output directory with a pack structure."
    ),
    keep_empty_folders: bool = typer.Option(
        False,
        "--keep-empty-folders",
        help="Keep empty folders when initializing a pack structure.",
    ),
    auto_replace_uuids: bool = typer.Option(
        True,
        "--auto-replace-uuids/--no-auto-replace-uuids",
        help="Automatically replace UUIDs for downloaded content.",
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
    **Downloads and merges content from a Cortex XSOAR or Cortex XSIAM tenant to your local repository.**

    In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
    and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

    **Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
    - Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button on the top rigth corner, and not the browser URL.
    - API key should be of a `standard` security level, and have the `Instance Administrator` role.
    - To use the command the `XSIAM_AUTH_ID` environment variable should also be set.


    To set the environment variables, run the following shell commands:
    ```
    export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
    export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
    ```
    and for Cortex XSIAM or Cortex XSOAR 8.x
    ```
    export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
    ```
    Note!
    As long as `XSIAM_AUTH_ID` environment variable is set, SDK commands will be configured to work with an XSIAM instance.
    In order to set Demisto SDK to work with Cortex XSOAR instance, you need to delete the XSIAM_AUTH_ID parameter from your environment.
    ```bash
    unset XSIAM_AUTH_ID
    ```
    """
    from demisto_sdk.commands.download.downloader import Downloader

    kwargs = locals()
    Downloader(**kwargs).download()

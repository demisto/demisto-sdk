from enum import Enum

import typer
from pathlib import Path
from typing import List


class ItemType(str, Enum):
    incident_type = "IncidentType"
    indicator_type = "IndicatorType"
    field = "Field"
    layout = "Layout"
    playbook = "Playbook"
    automation = "Automation"
    classifier = "Classifier"
    mapper = "Mapper"


def download(
    output: Path = typer.Option(
        None, "--output", "-o", help="A path to a pack directory to download content to."
    ),
    input: List[str] = typer.Option(
        None, "--input", "-i", help="Name of a custom content item to download. Can be used multiple times."
    ),
    regex: str = typer.Option(None, "--regex", "-r", help="Download all custom content items matching this RegEx pattern."),
    insecure: bool = typer.Option(False, "--insecure", help="Skip certificate validation."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing content in the output directory."),
    list_files: bool = typer.Option(False, "--list-files", "-lf", help="List all custom content items available to download and exit."),
    all_custom_content: bool = typer.Option(False, "--all-custom-content", "-a", help="Download all available custom content items."),
    run_format: bool = typer.Option(False, "--run-format", "-fmt", help="Format downloaded files."),
    system: bool = typer.Option(False, "--system", help="Download system items."),
    item_type: ItemType = typer.Option(
        None,
        "--item-type", "-it",
        help="Type of the content item to download. Required and used only when downloading system items.",
        case_sensitive=False
    ),

    init: bool = typer.Option(False, "--init", help="Initialize the output directory with a pack structure."),
    keep_empty_folders: bool = typer.Option(False, "--keep-empty-folders", help="Keep empty folders when initializing a pack structure."),
    auto_replace_uuids: bool = typer.Option(True, "--auto-replace-uuids/--no-auto-replace-uuids", help="Automatically replace UUIDs for downloaded content."),
):
    """
    Download custom content from a Cortex XSOAR / XSIAM instance.
    DEMISTO_BASE_URL environment variable should contain the server base URL.
    DEMISTO_API_KEY environment variable should contain a valid API Key for the server.
    """
    typer.echo(f"Downloading content with options: output={output}, input={input}, regex={regex}, insecure={insecure}")
    # Placeholder: Replace with the actual download logic
    from demisto_sdk.commands.download.downloader import Downloader
    # Assuming kwargs need to be passed as a dict:
    kwargs = locals()
    Downloader(**kwargs).download()

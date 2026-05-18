import sys
from typing import Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.get_schema.get_schema import (
    CONTENT_ITEM_NAME_TO_STRICT_OBJECT,
    print_schema,
)


# Canonical names: prefer the underscore-separated form when it exists,
# otherwise fall back to the concatenated form.  Deduplicate by strict model.
def _build_canonical_names() -> list[str]:
    seen_models: set = set()
    canonical: list[str] = []
    # First pass: collect underscore-separated names (most readable).
    for k, model in sorted(CONTENT_ITEM_NAME_TO_STRICT_OBJECT.items()):
        if "_" in k and id(model) not in seen_models:
            seen_models.add(id(model))
            canonical.append(k)
    # Second pass: add concatenated names for models not yet covered.
    for k, model in sorted(CONTENT_ITEM_NAME_TO_STRICT_OBJECT.items()):
        if "_" not in k and id(model) not in seen_models:
            seen_models.add(id(model))
            canonical.append(k)
    return sorted(canonical)


_AVAILABLE_TYPES = _build_canonical_names()


@logging_setup_decorator
def get_schema(
    ctx: typer.Context,
    input: Optional[str] = typer.Option(
        None,
        "-i",
        "--input",
        help=(
            "The content item type name to retrieve the schema for "
            "(e.g. 'integration', 'script', 'agentix_action'). "
            "Use --list-types to see all supported values."
        ),
    ),
    list_types: bool = typer.Option(
        False,
        "-l",
        "--list-types",
        help="Print all supported content item type names and exit.",
    ),
    output: Optional[str] = typer.Option(
        None,
        "-o",
        "--output",
        help="Path to a file where the JSON schema will be written. If not provided, prints to stdout.",
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None,
        "--file-log-threshold",
        help="Minimum logging threshold for file output.",
    ),
    log_file_path: str = typer.Option(
        None,
        "--log-file-path",
        help="Path to save log files.",
    ),
):
    """
    Returns the JSON schema of a content item type based on its strict pydantic model.

    Example usage:\n
        demisto-sdk get-schema -i integration\n
        demisto-sdk get-schema -i agentix_action\n
        demisto-sdk get-schema -i script -o /tmp/script_schema.json\n
        demisto-sdk get-schema --list-types
    """
    if list_types:
        typer.echo("Supported content item types:")
        for name in _AVAILABLE_TYPES:
            typer.echo(f"  {name}")
        raise typer.Exit(0)

    if not input:
        typer.echo(
            "Error: Missing option '-i' / '--input'. "
            "Provide a content item type name or use --list-types to see all supported values.",
            err=True,
        )
        raise typer.Exit(1)

    result = print_schema(content_item_name=input, output_file=output)
    sys.exit(result)

from pathlib import Path

import typer
from typer.main import get_command

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import convert_path_to_str


def dump_api(
    ctx: typer.Context,
    output_path: Path = typer.Option(
        CONTENT_PATH,
        "-o",
        "--output",
        help="The output directory or JSON file to save the demisto-sdk API.",
    ),
):
    """
    This command dumps the `demisto-sdk` API to a file.
    It is used to view the help of all commands in one file.

    Args:
        ctx (typer.Context): The context of the command.
        output_path (Path, optional): The output directory or JSON file to save the demisto-sdk API.
    """
    from demisto_sdk.__main__ import app

    output_json: dict = {}
    typer_app = get_command(app)

    # Iterate over registered commands in the main application
    for command_name, command in typer_app.commands.items():  # type: ignore[attr-defined]
        typer.echo(command_name, color=True)
        if isinstance(command, typer.Typer):
            output_json[command_name] = {}

            # Iterate over subcommands
            for sub_command in command.registered_commands:
                sub_command_name = sub_command.name
                # Convert subcommand to info dictionary
                output_json[command_name][sub_command_name] = sub_command.to_info_dict(  # type: ignore[attr-defined]
                    ctx
                )
        else:
            # Convert command to info dictionary
            output_json[command_name] = command.to_info_dict(ctx)

    # Convert paths in the output JSON (if applicable)
    convert_path_to_str(output_json)

    # Determine output file path
    if output_path.is_dir():
        output_path = output_path / "demisto-sdk-api.json"

    # Write the JSON output to the specified file
    output_path.write_text(json.dumps(output_json, indent=4))
    typer.echo(f"API dumped successfully to {output_path}")

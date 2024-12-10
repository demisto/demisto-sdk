from pathlib import Path

import typer

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.openapi_codegen.openapi_codegen import OpenAPIIntegration


@logging_setup_decorator
def openapi_codegen(
    ctx: typer.Context,
    input_file: Path = typer.Option(
        ..., "-i", "--input-file", help="The swagger file to load in JSON format"
    ),
    config_file: Path = typer.Option(
        None,
        "-cf",
        "--config-file",
        help="The integration configuration file. Created in the first run.",
    ),
    base_name: str = typer.Option(
        None,
        "-n",
        "--base-name",
        help="The base filename to use for the generated files",
    ),
    output_dir: Path = typer.Option(
        Path("."), "-o", "--output-dir", help="Directory to store the output"
    ),
    command_prefix: str = typer.Option(
        None, "-pr", "--command-prefix", help="Add a prefix to each command in the code"
    ),
    context_path: str = typer.Option(
        None, "-c", "--context-path", help="Context output path"
    ),
    unique_keys: str = typer.Option(
        "",
        "-u",
        "--unique-keys",
        help="Comma-separated unique keys for context paths (case sensitive)",
    ),
    root_objects: str = typer.Option(
        "",
        "-r",
        "--root-objects",
        help="Comma-separated JSON root objects in command outputs (case sensitive)",
    ),
    fix_code: bool = typer.Option(
        False, "-f", "--fix-code", help="Fix the python code using autopep8"
    ),
    use_default: bool = typer.Option(
        False,
        "-a",
        "--use-default",
        help="Use the automatically generated integration configuration",
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
    It is possible to generate a Cortex XSOAR integration package (YAML and Python files) with a dedicated tool in the Cortex XSOAR (demisto) SDK.
    The integration will be usable right away after generation.

    **Requirements**
    * OpenAPI (Swagger) specification file (v2.0 is recommended) in JSON format.
    * Cortex XSOAR (demisto) SDK
    """
    # Ensure output directory exists
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except Exception as err:
            typer.secho(
                f"Error creating directory {output_dir} - {err}", fg=typer.colors.RED
            )
            raise typer.Exit(1)

    if not output_dir.is_dir():
        typer.secho(
            f'The provided output "{output_dir}" is not a directory.',
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Set defaults
    base_name = base_name or "GeneratedIntegration"
    command_prefix = command_prefix or "-".join(base_name.split(" ")).lower()
    context_path = context_path or base_name.replace(" ", "")
    configuration = None

    # Load config if provided
    if config_file:
        try:
            with config_file.open() as f:
                configuration = json.load(f)
        except Exception as e:
            typer.secho(f"Failed to load configuration file: {e}", fg=typer.colors.RED)

    typer.secho("Processing swagger file...", fg=typer.colors.GREEN)
    integration = OpenAPIIntegration(
        file_path=str(input_file),
        base_name=base_name,
        command_prefix=command_prefix,
        context_path=context_path,
        unique_keys=unique_keys,
        root_objects=root_objects,
        fix_code=fix_code,
        configuration=configuration,
    )

    integration.load_file()

    # First run: create configuration file
    if not config_file:
        integration.save_config(integration.configuration, output_dir)
        config_path = output_dir / f"{base_name}_config.json"
        typer.secho(
            f"Created configuration file in {output_dir}", fg=typer.colors.GREEN
        )
        if not use_default:
            command_to_run = (
                f'demisto-sdk openapi-codegen -i "{input_file}" -cf "{config_path}" -n "{base_name}" '
                f'-o "{output_dir}" -pr "{command_prefix}" -c "{context_path}"'
            )
            if unique_keys:
                command_to_run += f' -u "{unique_keys}"'
            if root_objects:
                command_to_run += f' -r "{root_objects}"'
            if fix_code:
                command_to_run += " -f"

            typer.secho(
                f"Run the command again with the created configuration file (after review): {command_to_run}",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(0)

    # Second run: save generated package
    if integration.save_package(output_dir):
        typer.secho(
            f"Successfully saved integration code in {output_dir}",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"There was an error creating the package in {output_dir}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

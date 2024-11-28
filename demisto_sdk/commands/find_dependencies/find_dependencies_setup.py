from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.find_dependencies.find_dependencies import PackDependencies


@logging_setup_decorator
def find_dependencies(
    ctx: typer.Context,
    input: list[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Pack path to find dependencies. For example: Pack/HelloWorld. When using the "
        "--get-dependent-on flag, this argument can be used multiple times.",
    ),
    id_set_path: str = typer.Option(
        "",
        "--id-set-path",
        "-idp",
        help="Path to ID set JSON file.",
    ),
    no_update: bool = typer.Option(
        False,
        "--no-update",
        help="Use to find the pack dependencies without updating the pack metadata.",
    ),
    use_pack_metadata: bool = typer.Option(
        False,
        "--use-pack-metadata",
        help="Whether to update the dependencies from the pack metadata.",
    ),
    all_packs_dependencies: bool = typer.Option(
        False,
        "--all-packs-dependencies",
        help="Return a JSON file with ALL content packs dependencies. The JSON file will be saved under the "
        "path given in the '--output-path' argument.",
    ),
    output_path: Path = typer.Option(
        None,
        "--output-path",
        "-o",
        help="The destination path for the packs dependencies JSON file. This argument is only relevant when "
        "using the '--all-packs-dependencies' flag.",
    ),
    get_dependent_on: bool = typer.Option(
        False,
        "--get-dependent-on",
        help="Get only the packs dependent ON the given pack. Note: this flag cannot be used for the packs ApiModules and Base.",
    ),
    dependency: str = typer.Option(
        None,
        "--dependency",
        "-d",
        help="Find which items in a specific content pack appear as a mandatory dependency of the searched pack.",
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
    Find pack dependencies and update pack metadata.

    **Use Cases**:
    This command is used in order to find the dependencies between packs and to update the dependencies section in the pack metadata.
    """
    # Convert input to tuple to match the expected input type in the PackDependencies function.
    input_paths = tuple(input) if input else ()

    update_pack_metadata = not no_update
    output_path_str = str(output_path) if output_path else "path/to/default_output.json"

    try:
        PackDependencies.find_dependencies_manager(
            id_set_path=id_set_path,
            update_pack_metadata=update_pack_metadata,
            use_pack_metadata=use_pack_metadata,
            input_paths=input_paths,
            all_packs_dependencies=all_packs_dependencies,
            get_dependent_on=get_dependent_on,
            output_path=output_path_str,
            dependency=dependency,
        )
    except ValueError as exp:
        typer.echo(f"<red>{exp}</red>", err=True)

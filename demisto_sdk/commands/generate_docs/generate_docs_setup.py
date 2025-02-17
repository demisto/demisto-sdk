import copy
from pathlib import Path
from typing import Any, Dict

import typer

from demisto_sdk.commands.common.constants import NO_COLOR, RED, FileType
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    generate_integration_doc,
)
from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
    generate_playbook_doc,
)
from demisto_sdk.commands.generate_docs.generate_readme_template import (
    generate_readme_template,
)
from demisto_sdk.commands.generate_docs.generate_script_doc import (
    generate_script_doc,
)
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def generate_docs(
    ctx: typer.Context,
    input: str = typer.Option(..., "-i", "--input", help="Path of the yml file."),
    output: str = typer.Option(
        None,
        "-o",
        "--output",
        help="Output directory to write the documentation file into, documentation file name is README.md. If not specified, will be in the yml dir.",
    ),
    use_cases: str = typer.Option(
        None,
        "-uc",
        "--use_cases",
        help="Top use-cases. Number the steps by '*' (e.g., '* foo. * bar.')",
    ),
    command: str = typer.Option(
        None,
        "-c",
        "--command",
        help="Comma-separated command names to generate docs for (e.g., xdr-get-incidents,xdr-update-incident)",
    ),
    examples: str = typer.Option(
        None,
        "-e",
        "--examples",
        help="Path for file containing command examples, each command in a separate line.",
    ),
    permissions: str = typer.Option(
        "none", "-p", "--permissions", help="Permissions needed.", case_sensitive=False
    ),
    command_permissions: str = typer.Option(
        None,
        "-cp",
        "--command-permissions",
        help="Path for file containing commands permissions, each on a separate line.",
    ),
    limitations: str = typer.Option(
        None,
        "-l",
        "--limitations",
        help="Known limitations, numbered by '*' (e.g., '* foo. * bar.')",
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help="Skip certificate validation for commands in order to generate docs.",
    ),
    old_version: str = typer.Option(
        None, "--old-version", help="Path of the old integration version yml file."
    ),
    skip_breaking_changes: bool = typer.Option(
        False,
        "--skip-breaking-changes",
        help="Skip generating breaking changes section.",
    ),
    custom_image_path: str = typer.Option(
        None,
        "--custom-image-path",
        help="Custom path to a playbook image. If not provided, a default link will be added.",
    ),
    readme_template: str = typer.Option(
        None,
        "-rt",
        "--readme-template",
        help="The readme template to append to README.md file",
        case_sensitive=False,
    ),
    graph: bool = typer.Option(
        True,
        "-gr/-ngr",
        "--graph/--no-graph",
        help="Whether to use the content graph or not.",
    ),
    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        help="Force documentation generation (updates if it exists in version control)",
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
    """Generates a `README` file for your integration, script or playbook. Used to create documentation files for Cortex XSOAR.

    This command creates a new README.md file in the same directory as the entity on which it ran, unless otherwise specified using the -o flag.
    To generate command examples, set up the required environment variables prior to running this command in order to establish a connection between the Demisto SDK and the server, as well as create a file containing command examples to be run for the documentation.
    >Note: This command is not supported in Cortex XSIAM."""
    try:
        update_command_args_from_config_file("generate-docs", ctx.params)
        input_path_str: str = ctx.params.get("input", "")
        if not (input_path := Path(input_path_str)).exists():
            raise Exception(f"Input {input_path_str} does not exist.")

        if (output_path := ctx.params.get("output")) and not Path(output_path).is_dir():
            raise Exception(f"Output directory {output_path} is not a directory.")

        if input_path.is_file():
            if input_path.suffix.lower() not in {".yml", ".md"}:
                raise Exception(
                    f"Input {input_path} is not a valid yml or readme file."
                )
            _generate_docs_for_file(ctx.params)

        elif input_path.is_dir() and input_path.name == "Playbooks":
            for yml in input_path.glob("*.yml"):
                file_kwargs = copy.deepcopy(ctx.params)
                file_kwargs["input"] = str(yml)
                _generate_docs_for_file(file_kwargs)

        else:
            raise Exception(
                f"Input {input_path} is neither a valid yml file, a 'Playbooks' folder, nor a readme file."
            )

        return 0

    except Exception as e:
        typer.echo(f"{RED}Failed generating docs: {str(e)}{NO_COLOR}", err=True)
        raise typer.Exit(1)


def _generate_docs_for_file(kwargs: Dict[str, Any]):
    """Helper function to support Playbooks directory as an input or a single yml file."""
    input_path: str = kwargs.get("input", "")
    output_path = kwargs.get("output")
    command = kwargs.get("command")
    examples: str = kwargs.get("examples", "")
    permissions = kwargs.get("permissions")
    limitations = kwargs.get("limitations")
    insecure: bool = kwargs.get("insecure", False)
    old_version: str = kwargs.get("old_version", "")
    skip_breaking_changes: bool = kwargs.get("skip_breaking_changes", False)
    custom_image_path: str = kwargs.get("custom_image_path", "")
    readme_template: str = kwargs.get("readme_template", "")
    use_graph = kwargs.get("graph", True)
    force = kwargs.get("force", False)

    file_type = find_type(kwargs.get("input", ""), ignore_sub_categories=True)
    if file_type not in {
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.PLAYBOOK,
        FileType.README,
    }:
        raise Exception("File is not an Integration, Script, Playbook, or README.")

    if file_type == FileType.INTEGRATION:
        typer.echo(f"Generating {file_type.value.lower()} documentation")
        use_cases = kwargs.get("use_cases")
        command_permissions = kwargs.get("command_permissions")
        return generate_integration_doc(
            input_path=input_path,
            output=output_path,
            use_cases=use_cases,
            examples=examples,
            permissions=permissions,
            command_permissions=command_permissions,
            limitations=limitations,
            insecure=insecure,
            command=command,
            old_version=old_version,
            skip_breaking_changes=skip_breaking_changes,
            force=force,
        )
    elif file_type == FileType.SCRIPT:
        typer.echo(f"Generating {file_type.value.lower()} documentation")
        return generate_script_doc(
            input_path=input_path,
            output=output_path,
            examples=examples,
            permissions=permissions,
            limitations=limitations,
            insecure=insecure,
            use_graph=use_graph,
        )
    elif file_type == FileType.PLAYBOOK:
        typer.echo(f"Generating {file_type.value.lower()} documentation")
        return generate_playbook_doc(
            input_path=input_path,
            output=output_path,
            permissions=permissions,
            limitations=limitations,
            custom_image_path=custom_image_path,
        )
    elif file_type == FileType.README:
        typer.echo(f"Adding template to {file_type.value.lower()} file")
        return generate_readme_template(
            input_path=Path(input_path), readme_template=readme_template
        )

    else:
        raise Exception(f"File type {file_type.value} is not supported.")

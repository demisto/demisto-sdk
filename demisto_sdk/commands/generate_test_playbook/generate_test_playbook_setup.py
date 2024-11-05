from typing import Optional

import typer
from pathlib import Path
from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import (
    PlaybookTestsGenerator,
)
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.tools import find_type
import sys

from demisto_sdk.utils.utils import update_command_args_from_config_file


def generate_test_playbook(
    ctx: typer.Context,
    input: Path = typer.Option(..., "-i", "--input", help="Specify integration/script yml path"),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        help="Specify output directory or path to an output yml file. If not specified, output will be saved "
             "under the default directories based on input location.",
    ),
    name: str = typer.Option(..., "-n", "--name", help="Specify test playbook name. Output file will be `playbook-<name>_Test.yml"),
    no_outputs: bool = typer.Option(False, "--no-outputs", help="Skip generating verification conditions for each output contextPath."),
    use_all_brands: bool = typer.Option(False, "-ab", "--all-brands", help="Generate test-playbook with all brands available."),
    commands: Optional[str] = typer.Option(None, "-c", "--commands", help="Comma-separated command names to generate playbook tasks for."),
    examples: Optional[str] = typer.Option(None, "-e", "--examples", help="File path containing command examples."),
    upload: bool = typer.Option(False, "-u", "--upload", help="Upload the test playbook after generation."),
):
    """
    Generate test playbook from integration or script
    """
    update_command_args_from_config_file("generate-test-playbook", ctx.params)
    file_type: FileType = find_type(str(input), ignore_sub_categories=True)
    if file_type not in [FileType.INTEGRATION, FileType.SCRIPT]:
        typer.echo("Generating test playbook is possible only for an Integration or a Script.", err=True)
        raise typer.Exit(code=1)

    try:
        generator = PlaybookTestsGenerator(file_type=file_type.value, **ctx.params)
        if generator.run():
            sys.exit(0)
        sys.exit(1)
    except PlaybookTestsGenerator.InvalidOutputPathError as e:
        typer.echo(f"<red>{e}</red>", err=True)
        sys.exit(1)

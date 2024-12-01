from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.generate_yml_from_python.generate_yml import YMLGenerator


@logging_setup_decorator
def generate_yml_from_python(
    ctx: typer.Context,
    input: Path = typer.Option(
        ...,
        "-i",
        "--input",
        exists=True,
        help="Path to the Python code to generate from.",
    ),
    force: bool = typer.Option(
        False, "-f", "--force", help="Override existing YML file."
    ),
):
    """
    Generate YML file from Python code that includes special syntax.
    The output file name will be the same as the Python code with the `.yml` extension instead of `.py`.
    The generation currently supports integrations only.

    The feature is supported from content Base pack version 1.20.0 and on.
    """
    # Initialize the YML generator
    yml_generator = YMLGenerator(
        filename=str(input),
        force=force,
    )

    # Generate and save the YML file
    yml_generator.generate()
    yml_generator.save_to_yml_file()

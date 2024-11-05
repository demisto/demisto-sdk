import typer
from pathlib import Path
from demisto_sdk.commands.generate_yml_from_python.generate_yml import YMLGenerator


def generate_yml_from_python(
    ctx: typer.Context,
    input: Path = typer.Option(..., "-i", "--input", exists=True, help="Path to the Python code to generate from."),
    force: bool = typer.Option(False, "-f", "--force", help="Override existing YML file."),
):
    """
    Generate a YML file from a Python file with special syntax for integrations.
    """
    # Initialize the YML generator
    yml_generator = YMLGenerator(
        filename=str(input),
        force=force,
    )

    # Generate and save the YML file
    yml_generator.generate()
    yml_generator.save_to_yml_file()

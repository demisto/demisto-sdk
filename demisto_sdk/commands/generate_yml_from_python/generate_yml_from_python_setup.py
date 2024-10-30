import typer
from pathlib import Path
from demisto_sdk.commands.generate_yml_from_python.generate_yml import YMLGenerator

generate_yml_app = typer.Typer()


@generate_yml_app.command(
    name="generate-yml-from-python",
    help="""Generate YML file from Python code that includes special syntax.\n
             The output file name will be the same as the Python code with the `.yml` extension instead of `.py`.\n
             The generation currently supports integrations only.\n
             For more information on usage and installation visit the command's README.md file."""
)
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

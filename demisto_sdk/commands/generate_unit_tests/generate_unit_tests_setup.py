import typer
from pathlib import Path
from typing import List, Optional
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import (
    run_generate_unit_tests,
)


def generate_unit_tests(
    ctx: typer.Context,
    input_path: Path = typer.Option(..., "-i", "--input-path", help="Valid integration file path."),
    commands: Optional[List[str]] = typer.Option(
        None, "-c", "--commands", help="Specific commands name to generate unit test for (e.g. xdr-get-incidents)"
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "-o", "--output-dir", help="Directory to store the output in (default is the input integration directory)"
    ),
    examples: Optional[Path] = typer.Option(
        None, "-e", "--examples", help="Path for file containing command examples, each on a separate line."
    ),
    insecure: bool = typer.Option(False, "--insecure", help="Skip certificate validation"),
    use_demisto: bool = typer.Option(False, "-d", "--use-demisto", help="Run commands in Demisto automatically."),
    append: bool = typer.Option(
        False, "-a", "--append", help="Append generated test file to the existing <integration_name>_test.py."
    ),
):
    """
    This command is used to generate unit tests automatically from an integration's Python code.
    Also supports generating unit tests for specific commands.
    """
    # Set up logging control
    import logging
    logging.getLogger("PYSCA").propagate = False

    # Call the run_generate_unit_tests function
    run_generate_unit_tests(
        input_path=str(input_path),
        commands=commands or [],
        output_dir=str(output_dir) if output_dir else "",
        examples=str(examples) if examples else "",
        insecure=insecure,
        use_demisto=use_demisto,
        append=append,
    )

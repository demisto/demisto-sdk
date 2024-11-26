from pathlib import Path
from typing import List, Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator


@logging_setup_decorator
def generate_unit_tests(
    ctx: typer.Context,
    input_path: Path = typer.Option(
        ..., "-i", "--input-path", help="Valid integration file path."
    ),
    commands: Optional[List[str]] = typer.Option(
        None,
        "-c",
        "--commands",
        help="Specific commands name to generate unit test for (e.g. xdr-get-incidents)",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Directory to store the output in (default is the input integration directory)",
    ),
    examples: Optional[Path] = typer.Option(
        None,
        "-e",
        "--examples",
        help="Path for file containing command examples, each on a separate line.",
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Skip certificate validation"
    ),
    use_demisto: bool = typer.Option(
        False, "-d", "--use-demisto", help="Run commands in Demisto automatically."
    ),
    append: bool = typer.Option(
        False,
        "-a",
        "--append",
        help="Append generated test file to the existing <integration_name>_test.py.",
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
    This command generates unit tests automatically from an integration's Python code.
    It also supports generating unit tests for specific commands.
    Note that this command is not intended to fully replace manual work on unit tests but is intended to make it easier to write them.

    >NOTE: The generate-unit-test command only works if demisto-sdk is installed with pip install demisto-sdk [generate-unit-tests].

    """
    import logging  # noqa: TID251 # special case: controlling external logger

    from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import (
        run_generate_unit_tests,
    )

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

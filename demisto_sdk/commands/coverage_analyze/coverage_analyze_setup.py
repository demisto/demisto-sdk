import os
from typing import Optional

import typer

from demisto_sdk.commands.common.constants import DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.coverage_analyze.coverage_report import CoverageReport


@logging_setup_decorator
def coverage_analyze(
    ctx: typer.Context,
    input: str = typer.Option(
        os.path.join("coverage_report", ".coverage"),
        "-i",
        "--input",
        help="The .coverage file to analyze.",
        resolve_path=True,
    ),
    default_min_coverage: float = typer.Option(
        70.0,
        help="Default minimum coverage (for new files).",
    ),
    allowed_coverage_degradation_percentage: float = typer.Option(
        1.0,
        help="Allowed coverage degradation percentage (for modified files).",
    ),
    no_cache: bool = typer.Option(
        False,
        help="Force download of the previous coverage report file.",
    ),
    report_dir: str = typer.Option(
        "coverage_report",
        help="Directory of the coverage report files.",
        resolve_path=True,
    ),
    report_type: Optional[str] = typer.Option(
        None,
        help="The type of coverage report (possible values: 'text', 'html', 'xml', 'json' or 'all').",
    ),
    no_min_coverage_enforcement: bool = typer.Option(
        False,
        help="Do not enforce minimum coverage.",
    ),
    previous_coverage_report_url: str = typer.Option(
        f"https://storage.googleapis.com/{DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV}/code-coverage-reports/coverage-min.json",
        help="URL of the previous coverage report.",
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
    """Generating and printing the coverage reports."""
    try:
        no_degradation_check = allowed_coverage_degradation_percentage == 100.0

        cov_report = CoverageReport(
            default_min_coverage=default_min_coverage,
            allowed_coverage_degradation_percentage=allowed_coverage_degradation_percentage,
            coverage_file=input,
            no_cache=no_cache,
            report_dir=report_dir,
            report_type=report_type,
            no_degradation_check=no_degradation_check,
            previous_coverage_report_url=previous_coverage_report_url,
        )
        cov_report.coverage_report()

        # if no_degradation_check=True we will suppress the minimum coverage check
        if (
            no_degradation_check
            or cov_report.coverage_diff_report()
            or no_min_coverage_enforcement
        ):
            return 0
    except FileNotFoundError as e:
        typer.echo(f"Warning: {e}")
        return 0
    except Exception as error:
        typer.echo(f"Error: {error}")

    return 1

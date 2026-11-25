import multiprocessing
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.xsoar_linter.checkers.runner import (
    display_path,
    format_finding,
    lint_file,
    settings_from_integration_script,
)

ERROR_AND_WARNING_CODE_PATTERN = re.compile(
    r"^(?P<path>[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<error_code>(?P<type>[EW])\d+)(?P<error_message> .*)$",
    re.MULTILINE,
)


@dataclass
class ProcessResults:
    """Class for keeping track of a process execution results."""

    return_code: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors_and_warnings: str = ""
    # The file path, if the file was skipped by `# xsoar-lint: skip-parse-file`.
    skipped_file: str = ""


def process_file(file_path: Path) -> ProcessResults:
    """
    Runs the xsoar-linter checkers on a given path, in the current process.

    Args:
        file_path: the file path to run xsoar-linter on.

    Returns:
        A ProcessResults data class which keeps the execution return code and collected errors and warnings.
    """
    results = ProcessResults()
    try:
        integration_script = BaseContent.from_path(file_path)
        if not isinstance(integration_script, IntegrationScript):
            return results
        file = integration_script.path.parent / f"{integration_script.path.stem}.py"
        if not file.exists():
            return results

        lint_result = lint_file(
            file, settings_from_integration_script(integration_script)
        )
        if lint_result.skipped:
            results.skipped_file = str(display_path(file))
        results.return_code = int(lint_result.fails)
        lines = [format_finding(file, finding) for finding in lint_result.findings]
        results.errors_and_warnings = "\n".join(lines)
        for line in lines:
            if error_or_warning := ERROR_AND_WARNING_CODE_PATTERN.match(line):
                if error_or_warning["type"] == "E":
                    results.errors.append(line)
                else:
                    results.warnings.append(line)
    except Exception as e:
        results.errors.append(
            f"Failed processing the following file: {str(file_path)}: {e}"
        )
        results.return_code = 1

    return results


def xsoar_linter_manager(file_paths: Optional[List[Path]]):
    """
    Manages the xsoar linter command multiprocessing pool.
    Args:
        file_paths: List of files to run xsoar-linter on.

    Returns:
        0 status code if all runs were successful, 1 otherwise.
    """
    return_codes = []
    errors = []
    warning = []
    errors_and_warnings = []
    skipped_files = []

    if not file_paths:
        logger.info("[xsoar-lint] no files to lint.")
        return 0

    logger.info(
        f"[xsoar-lint] starting on {len(file_paths)} file(s) "
        f"with {cpu_count()} process(es)."
    )
    start_time = time.perf_counter()
    with multiprocessing.Pool(processes=cpu_count()) as pool:
        # Map the file_paths to the worker function using the pool
        results = pool.map(process_file, file_paths)
    duration = time.perf_counter() - start_time

    # Extracting and parsing return_codes, errors and warnings form the processes results.
    for result in results:
        return_codes.append(result.return_code)
        errors += result.errors
        warning += result.warnings
        errors_and_warnings.append(result.errors_and_warnings)
        if result.skipped_file:
            skipped_files.append(result.skipped_file)
    errors_and_warnings_concat = "\n".join(elem for elem in errors_and_warnings if elem)
    logger.info(errors_and_warnings_concat)
    for skipped_file in skipped_files:
        logger.info(
            f"[xsoar-lint] skipped {skipped_file} ('# xsoar-lint: skip-parse-file')."
        )
    logger.info(
        f"[xsoar-lint] finished {len(file_paths)} file(s) in {duration:.2f}s. "
        f"errors={len(list(filter(None, errors)))}, warnings={len(list(filter(None, warning)))}, "
        f"failed files={sum(1 for code in return_codes if code)}, skipped={len(skipped_files)}."
    )

    if any(return_codes):  # An error was found
        errors, warnings = list(filter(None, errors)), list(filter(None, warning))

        if os.getenv("GITHUB_ACTIONS"):
            print_errors_github_action(errors)
            if os.getenv("DEMISTO_SDK_XSOAR_LINTER_WARNING_ANNOTATIONS"):
                print_errors_github_action(warnings)

        errors_str = "\n".join(errors)
        logger.error(f"Found the following errors: \n{errors_str}")

    return int(any(return_codes))


def print_errors_github_action(errors_and_warnings: List[str]) -> None:
    for item in errors_and_warnings:
        if not (match := ERROR_AND_WARNING_CODE_PATTERN.match(item)):
            logger.debug(f"Failed parsing error {item}")
            continue

        prefix = {"W": "warning", "E": "error"}[match["type"]]
        print(  # noqa: T201
            f"::{prefix} file={match.group('path')},line={match.group('line')},col={match.group('col')},title=XSOAR Linter {match.group('error_code')}::{match.group('error_message')}"
        )

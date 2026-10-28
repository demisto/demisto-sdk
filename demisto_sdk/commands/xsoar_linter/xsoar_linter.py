import multiprocessing
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from packaging.version import Version

from demisto_sdk.commands.common.content_constant_paths import PYTHONPATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects import Integration, Script
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.resources.pylint_plugins.base_checker import (
    base_msg,
)
from demisto_sdk.commands.pre_commit.resources.pylint_plugins.certified_partner_level_checker import (
    cert_partner_msg,
)
from demisto_sdk.commands.pre_commit.resources.pylint_plugins.community_level_checker import (
    community_msg,
)
from demisto_sdk.commands.pre_commit.resources.pylint_plugins.partner_level_checker import (
    partner_msg,
)
from demisto_sdk.commands.pre_commit.resources.pylint_plugins.xsoar_level_checker import (
    xsoar_msg,
)

ENV = os.environ
PYLINT_ENGINE = "pylint"
AST_ENGINE = "ast"
ENGINES = (PYLINT_ENGINE, AST_ENGINE)
DEFAULT_ENGINE = PYLINT_ENGINE
ENGINE_ENV_VAR = "DEMISTO_SDK_XSOAR_LINTER_ENGINE"
ERROR_AND_WARNING_CODE_PATTERN = re.compile(
    r"^(?P<path>/[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<error_code>(?P<type>[EW])\d+)(?P<error_message> .*)$",
    re.MULTILINE,
)


def build_xsoar_linter_command(
    support_level: Optional[str] = "base", formatting_script: bool = False
) -> List[str]:
    """
    Build the xsoar linter command.
    Args:
        support_level: Support level for the file.
        formatting_script: if the file being checked is a formatting script.

    Returns:
       str: xsoar linter command using pylint load plugins.
    """
    if not support_level:
        support_level = "base"
    # linters by support level
    support_levels = {
        "base": ["base_checker"],
        "community": ["base_checker", "community_level_checker"],
        "developer": ["base_checker", "community_level_checker"],
        "partner": ["base_checker", "community_level_checker", "partner_level_checker"],
        "certified partner": [
            "base_checker",
            "community_level_checker",
            "partner_level_checker",
            "certified_partner_level_checker",
        ],
        "xsoar": [
            "base_checker",
            "community_level_checker",
            "partner_level_checker",
            "certified_partner_level_checker",
            "xsoar_level_checker",
        ],
    }
    # messages from all level linters
    Msg_XSOAR_linter = {
        "base_checker": base_msg,
        "community_level_checker": community_msg,
        "partner_level_checker": partner_msg,
        "certified_partner_level_checker": cert_partner_msg,
        "xsoar_level_checker": xsoar_msg,
    }

    command = [
        f"{Path(sys.executable).parent}/pylint",
        "--disable=all",
        "--fail-under=-100",
        "--fail-on=E",
        "--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'",  # Message format
    ]
    checkers_to_use = []
    errors_to_use = []

    if checkers := support_levels.get(support_level, []):
        for checker in checkers:
            checkers_to_use.append(checker)
            checker_msgs_list = Msg_XSOAR_linter.get(checker, {}).keys()
            if formatting_script and "W9008" in checker_msgs_list:
                checker_msgs_list = [msg for msg in checker_msgs_list if msg != "W9008"]
            for msg in checker_msgs_list:
                errors_to_use.append(msg)
    else:
        logger.warning(
            f"Integration support level: '{support_level}' is not valid. "
            f"Known values: {', '.join(support_levels.keys())}."
        )

    # Enable only Demisto Plugins errors.
    command.append(f"--enable={','.join(errors_to_use)}")
    # Load plugins
    if checkers_to_use:
        command.append(f"--load-plugins={','.join(checkers_to_use)}")

    return command


def build_xsoar_linter_env_var(integration_script: IntegrationScript) -> dict:
    """
    Build the relevant environment variable for each xsoar linter execution.
    Args:
        integration_script: An integration or a script object to process.

    Returns: A dictionary with the added environment variables.

    """
    xsoar_linter_env = {}
    if isinstance(integration_script, Integration) and integration_script.long_running:
        xsoar_linter_env["LONGRUNNING"] = "True"
    if (py_ver := integration_script.python_version) and Version(py_ver).major < 3:
        xsoar_linter_env["PY2"] = "True"
    xsoar_linter_env["is_script"] = str(isinstance(integration_script, Script))
    # as Xsoar checker is a pylint plugin and runs as part of pylint code, we can not pass args to it.
    # as a result we can use the env vars as a getway.
    if isinstance(integration_script, Integration):
        xsoar_linter_env["commands"] = ",".join(
            [command.name for command in integration_script.commands]
        )
    xsoar_linter_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)

    return xsoar_linter_env


@dataclass
class ProcessResults:
    """Class for keeping track of a process execution results."""

    return_code: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors_and_warnings: str = ""


def process_file(file_path: Path) -> ProcessResults:
    """
    Runs the xsoar-linter command of a given path.

    Args:
        file_path: the file path to run xsoar-linter on.

    Returns:
        A ProcessResults data class which keeps the execution return code and collected errors and warnings.
    """
    results = ProcessResults()

    try:
        env = ENV.copy()
        integration_script = BaseContent.from_path(file_path)
        results = ProcessResults()

        if not isinstance(integration_script, IntegrationScript):
            return results
        file = integration_script.path.parent / f"{integration_script.path.stem}.py"
        if not file.exists():
            return results

        xsoar_linter_env = build_xsoar_linter_env_var(integration_script)
        env.update(xsoar_linter_env)
        command = build_xsoar_linter_command(integration_script.support)
        command.append(str(file))

        try:
            process = subprocess.run(command, capture_output=True, env=env, timeout=60)
            results.return_code = process.returncode
            log_data = process.stdout
            errors_and_warnings_str = log_data.decode("utf-8")
            results.errors_and_warnings = errors_and_warnings_str
            # catch only error codes from the error and warning string
            for line in errors_and_warnings_str.splitlines():
                if error_or_warning := ERROR_AND_WARNING_CODE_PATTERN.match(line):
                    if error_or_warning["type"] == "E":
                        results.errors.append(line)
                    else:
                        results.warnings.append(line)
        except subprocess.TimeoutExpired:
            results.errors.append(
                f"Got a timeout while processing the following file: {str(file_path)}"
            )
            results.return_code = 1
    except Exception as e:
        results.errors.append(
            f"Failed processing the following file: {str(file_path)}: {e}"
        )
        results.return_code = 1

    return results


def process_file_ast(file_path: Path) -> ProcessResults:
    """
    Runs the ast-based xsoar-linter on a given path, in the current process (no pylint).

    Args:
        file_path: the file path to run xsoar-linter on.

    Returns:
        A ProcessResults data class, filled the same way as `process_file` fills it.
    """
    from demisto_sdk.commands.xsoar_linter.checkers.runner import (
        format_finding,
        lint_file,
        settings_from_integration_script,
    )

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


def xsoar_linter_manager(
    file_paths: Optional[List[Path]], engine: str = DEFAULT_ENGINE
):
    """
    Manages the xsoar linter command multiprocessing pool.
    Args:
        file_paths: List of files to run xsoar-linter on.
        engine: "pylint" (default) runs the pylint plugins, "ast" runs the ast-based checkers.

    Returns:
        0 status code if all runs were successful, 1 otherwise.
    """
    return_codes = []
    errors = []
    warning = []
    errors_and_warnings = []

    if engine not in ENGINES:
        logger.error(
            f"[xsoar-lint] Unknown engine '{engine}'. Known engines: {', '.join(ENGINES)}."
        )
        return 1

    if not file_paths:
        logger.info(f"[xsoar-lint] engine={engine}: no files to lint.")
        return 0

    worker = process_file_ast if engine == AST_ENGINE else process_file
    logger.info(
        f"[xsoar-lint] engine={engine}: starting on {len(file_paths)} file(s) "
        f"with {cpu_count()} process(es)."
    )
    start_time = time.perf_counter()
    with multiprocessing.Pool(processes=cpu_count()) as pool:
        # Map the file_paths to the worker function using the pool
        results = pool.map(worker, file_paths)
    duration = time.perf_counter() - start_time

    # Extracting and parsing return_codes, errors and warnings form the processes results.
    for result in results:
        return_codes.append(result.return_code)
        errors += result.errors
        warning += result.warnings
        errors_and_warnings.append(result.errors_and_warnings)
    errors_and_warnings_concat = "\n".join(elem for elem in errors_and_warnings if elem)
    logger.info(errors_and_warnings_concat)
    logger.info(
        f"[xsoar-lint] engine={engine}: finished {len(file_paths)} file(s) in {duration:.2f}s. "
        f"errors={len(list(filter(None, errors)))}, warnings={len(list(filter(None, warning)))}, "
        f"failed files={sum(1 for code in return_codes if code)}."
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

import os
from typing import Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.lint.lint_manager import LintManager
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def lint(
    ctx: typer.Context,
    input: str = typer.Option(
        None, "-i", "--input", help="Specify directory(s) of integration/script"
    ),
    git: bool = typer.Option(
        False, "-g", "--git", help="Will run only on changed packages"
    ),
    all_packs: bool = typer.Option(
        False, "-a", "--all-packs", help="Run lint on all directories in content repo"
    ),
    parallel: int = typer.Option(
        1, "-p", "--parallel", help="Run tests in parallel", min=0, max=15
    ),
    no_flake8: bool = typer.Option(
        False, "--no-flake8", help="Do NOT run flake8 linter"
    ),
    no_bandit: bool = typer.Option(
        False, "--no-bandit", help="Do NOT run bandit linter"
    ),
    no_xsoar_linter: bool = typer.Option(
        False, "--no-xsoar-linter", help="Do NOT run XSOAR linter"
    ),
    no_mypy: bool = typer.Option(
        False, "--no-mypy", help="Do NOT run mypy static type checking"
    ),
    no_vulture: bool = typer.Option(
        False, "--no-vulture", help="Do NOT run vulture linter"
    ),
    no_pylint: bool = typer.Option(
        False, "--no-pylint", help="Do NOT run pylint linter"
    ),
    no_test: bool = typer.Option(False, "--no-test", help="Do NOT test (skip pytest)"),
    no_pwsh_analyze: bool = typer.Option(
        False, "--no-pwsh-analyze", help="Do NOT run powershell analyze"
    ),
    no_pwsh_test: bool = typer.Option(
        False, "--no-pwsh-test", help="Do NOT run powershell test"
    ),
    keep_container: bool = typer.Option(
        False, "-kc", "--keep-container", help="Keep the test container"
    ),
    prev_ver: str = typer.Option(
        os.getenv("DEMISTO_DEFAULT_BRANCH", "master"),
        "--prev-ver",
        help="Previous branch or SHA1 commit to run checks against",
    ),
    test_xml: str = typer.Option(
        None, "--test-xml", help="Path to store pytest xml results"
    ),
    failure_report: str = typer.Option(
        None, "--failure-report", help="Path to store failed packs report"
    ),
    json_file: str = typer.Option(
        None,
        "-j",
        "--json-file",
        help="The JSON file path to which to output the command results.",
    ),
    no_coverage: bool = typer.Option(
        False, "--no-coverage", help="Do NOT run coverage report."
    ),
    coverage_report: str = typer.Option(
        None,
        "--coverage-report",
        help="Specify directory for the coverage report files",
    ),
    docker_timeout: int = typer.Option(
        60,
        "-dt",
        "--docker-timeout",
        help="The timeout (in seconds) for requests done by the docker client.",
    ),
    docker_image: str = typer.Option(
        "from-yml",
        "-di",
        "--docker-image",
        help="The docker image to check package on. Can be a comma-separated list.",
    ),
    docker_image_target: str = typer.Option(
        "",
        "-dit",
        "--docker-image-target",
        help="The docker image to lint native supported content with, used with --docker-image native:target.",
    ),
    check_dependent_api_module: bool = typer.Option(
        False,
        "-cdam",
        "--check-dependent-api-module",
        help="Run unit tests and lint on all packages that are dependent on modified API modules.",
    ),
    time_measurements_dir: Optional[str] = typer.Option(
        None,
        "--time-measurements-dir",
        help="Specify directory for the time measurements report file",
    ),
    skip_deprecation_message: bool = typer.Option(
        False,
        "-sdm",
        "--skip-deprecation-message",
        help="Whether to skip the deprecation notice or not.",
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
    Deprecated, use demisto-sdk pre-commit instead.
    Lint command performs:
    1. Package in host checks - flake8, bandit, mypy, vulture.
    2. Package in docker image checks - pylint, pytest, powershell - test, powershell - analyze.
    Meant to be used with integrations/scripts that use the folder (package) structure.
    Will lookup what docker image to use and will setup the dev dependencies and file in the target folder.
    If no additional flags specifying the packs are given, will lint only changed files.
    """
    show_deprecation_message = not (
        os.getenv("SKIP_DEPRECATION_MESSAGE") or skip_deprecation_message
    )
    update_command_args_from_config_file("lint", ctx.args)

    lint_manager = LintManager(
        input=input,
        git=git,
        all_packs=all_packs,
        prev_ver=prev_ver,
        json_file_path=json_file,
        check_dependent_api_module=check_dependent_api_module,
        show_deprecation_message=show_deprecation_message,
    )
    lint_manager.run(
        parallel=parallel,
        no_flake8=no_flake8,
        no_bandit=no_bandit,
        no_mypy=no_mypy,
        no_vulture=no_vulture,
        no_xsoar_linter=no_xsoar_linter,
        no_pylint=no_pylint,
        no_test=no_test,
        no_pwsh_analyze=no_pwsh_analyze,
        no_pwsh_test=no_pwsh_test,
        keep_container=keep_container,
        test_xml=test_xml,
        failure_report=failure_report,
        no_coverage=no_coverage,
        coverage_report=coverage_report,
        docker_timeout=docker_timeout,
        docker_image_flag=docker_image,
        docker_image_target=docker_image_target,
        time_measurements_dir=time_measurements_dir,
    )

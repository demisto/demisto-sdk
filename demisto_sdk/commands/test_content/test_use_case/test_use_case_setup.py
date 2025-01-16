from pathlib import Path
from typing import List, Optional

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.test_content.tools import tenant_config_cb


@logging_setup_decorator
def run_test_use_case(
    ctx: typer.Context,
    inputs: List[Path] = typer.Argument(
        None,
        exists=True,
        dir_okay=True,
        resolve_path=True,
        show_default=False,
        help="The path to a directory of a test use cases. May pass multiple paths to test multiple test use cases.",
    ),
    xsiam_url: Optional[str] = typer.Option(
        None,
        envvar="DEMISTO_BASE_URL",
        help="The base url to the cloud tenant.",
        rich_help_panel="Cloud Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    api_key: Optional[str] = typer.Option(
        None,
        envvar="DEMISTO_API_KEY",
        help="The api key for the cloud tenant.",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    auth_id: Optional[str] = typer.Option(
        None,
        envvar="XSIAM_AUTH_ID",
        help="The auth id associated with the cloud api key being used.",
        rich_help_panel="XSIAM Tenant Configuration",
        show_default=False,
        callback=tenant_config_cb,
    ),
    output_junit_file: Optional[Path] = typer.Option(
        None, "-jp", "--junit-path", help="Path to the output JUnit XML file."
    ),
    service_account: Optional[str] = typer.Option(
        None,
        "-sa",
        "--service_account",
        envvar="GCP_SERVICE_ACCOUNT",
        help="GCP service account.",
        show_default=False,
    ),
    cloud_servers_path: str = typer.Option(
        "",
        "-csp",
        "--cloud_servers_path",
        help="Path to secret cloud server metadata file.",
        show_default=False,
    ),
    cloud_servers_api_keys: str = typer.Option(
        "",
        "-csak",
        "--cloud_servers_api_keys",
        help="Path to file with cloud Servers api keys.",
        show_default=False,
    ),
    machine_assignment: str = typer.Option(
        "",
        "-ma",
        "--machine_assignment",
        help="the path to the machine assignment file.",
        show_default=False,
    ),
    build_number: str = typer.Option(
        "",
        "-bn",
        "--build_number",
        help="The build number.",
        show_default=True,
    ),
    nightly: str = typer.Option(
        "false",
        "--nightly",
        "-n",
        help="Whether the command is being run in nightly mode.",
    ),
    artifacts_bucket: str = typer.Option(
        None,
        "-ab",
        "--artifacts_bucket",
        help="The artifacts bucket name to upload the results to",
        show_default=False,
    ),
    project_id: str = typer.Option(
        None,
        "-pi",
        "--project_id",
        help="The machine project ID",
        show_default=False,
    ),
    console_log_threshold: str = typer.Option(
        "INFO",
        "-clt",
        "--console-log-threshold",
        help="Minimum logging threshold for the console logger.",
    ),
    file_log_threshold: str = typer.Option(
        "DEBUG",
        "-flt",
        "--file-log-threshold",
        help="Minimum logging threshold for the file logger.",
    ),
    log_file_path: Optional[str] = typer.Option(
        None,
        "-lp",
        "--log-file-path",
        help="Path to save log files onto.",
    ),
):
    from demisto_sdk.commands.test_content.test_use_case.test_use_case import (
        run_test_use_case,
    )

    kwargs = locals()
    run_test_use_case(**kwargs)

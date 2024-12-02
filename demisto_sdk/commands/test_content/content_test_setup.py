from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.string_to_bool import string_to_bool
from demisto_sdk.commands.test_content.execute_test_content import execute_test_content


@logging_setup_decorator
def test_content(
    ctx: typer.Context,
    artifacts_path: str = typer.Option(
        Path("./Tests"),
        "-a",
        "--artifacts-path",
        help="Destination directory to create the artifacts.",
        dir_okay=True,
        resolve_path=True,
    ),
    api_key: str = typer.Option(
        ..., "-k", "--api-key", help="The Demisto API key for the server"
    ),
    artifacts_bucket: str = typer.Option(
        None,
        "-ab",
        "--artifacts_bucket",
        help="The artifacts bucket name to upload the results to",
    ),
    server: str = typer.Option(
        None, "-s", "--server", help="The server URL to connect to"
    ),
    conf: str = typer.Option(
        ..., "-c", "--conf", help="Path to content conf.json file"
    ),
    secret: str = typer.Option(
        None, "-e", "--secret", help="Path to content-test-conf conf.json file"
    ),
    nightly: str = typer.Option(None, "-n", "--nightly", help="Run nightly tests"),
    service_account: str = typer.Option(
        None, "-sa", "--service_account", help="GCP service account."
    ),
    slack: str = typer.Option(..., "-t", "--slack", help="The token for slack"),
    build_number: str = typer.Option(
        ..., "-b", "--build-number", help="The build number"
    ),
    branch_name: str = typer.Option(
        ..., "-g", "--branch-name", help="The current content branch name"
    ),
    is_ami: str = typer.Option("false", "-i", "--is-ami", help="is AMI build or not"),
    mem_check: str = typer.Option(
        "false",
        "-m",
        "--mem-check",
        help="Should trigger memory checks or not.",
    ),
    server_version: str = typer.Option(
        "NonAMI",
        "-d",
        "--server-version",
        help="Which server version to run the tests on(Valid only when using AMI)",
    ),
    use_retries: bool = typer.Option(
        False, "-u", "--use-retries", help="Should use retries mechanism or not"
    ),
    server_type: str = typer.Option(
        "XSOAR",
        "--server-type",
        help="On which server type runs the tests: XSIAM, XSOAR, XSOAR SAAS",
    ),
    product_type: str = typer.Option(
        "XSOAR",
        "--product-type",
        help="On which product type runs the tests: XSIAM, XSOAR",
    ),
    cloud_machine_ids: str = typer.Option(
        None, "--cloud_machine_ids", help="Cloud machine ids to use."
    ),
    cloud_servers_path: str = typer.Option(
        None, "--cloud_servers_path", help="Path to secret cloud server metadata file."
    ),
    cloud_servers_api_keys: str = typer.Option(
        None,
        "--cloud_servers_api_keys",
        help="Path to file with cloud Servers API keys.",
    ),
    machine_assignment: str = typer.Option(
        "./machine_assignment.json",
        "--machine_assignment",
        help="Path to the machine assignment file.",
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
    """Configure instances for the integration needed to run tests.

    Run the test module on each integration.
    Create an investigation for each test.
    Run the test playbook on the created investigation using mock if possible.
    Collect the result and give a report.
    """
    is_ami = string_to_bool(is_ami)
    nightly = string_to_bool(nightly)
    mem_check = string_to_bool(mem_check)

    kwargs = {
        "artifacts_path": artifacts_path,
        "api_key": api_key,
        "artifacts_bucket": artifacts_bucket,
        "server": server,
        "conf": conf,
        "secret": secret,
        "nightly": nightly,
        "service_account": service_account,
        "slack": slack,
        "build_number": build_number,
        "branch_name": branch_name,
        "is_ami": is_ami,
        "mem_check": mem_check,
        "server_version": server_version,
        "use_retries": use_retries,
        "server_type": server_type,
        "product_type": product_type,
        "cloud_machine_ids": cloud_machine_ids,
        "cloud_servers_path": cloud_servers_path,
        "cloud_servers_api_keys": cloud_servers_api_keys,
        "machine_assignment": machine_assignment,
    }

    execute_test_content(**kwargs)

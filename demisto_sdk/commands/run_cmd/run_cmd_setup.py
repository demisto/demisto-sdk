from typing import Optional, TypedDict

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.utils.utils import update_command_args_from_config_file


class RunnerArgs(TypedDict):
    query: str
    insecure: bool
    incident_id: Optional[str]
    debug: Optional[str]
    debug_path: Optional[str]
    json_to_outputs: bool
    prefix: str
    raw_response: bool


@logging_setup_decorator
def run(
    ctx: typer.Context,
    query: str = typer.Option(..., "-q", "--query", help="The query to run"),
    insecure: bool = typer.Option(False, help="Skip certificate validation"),
    incident_id: Optional[str] = typer.Option(
        None,
        "-id",
        "--incident-id",
        help="The incident to run the query on, if not specified the playground will be used.",
    ),
    debug: bool = typer.Option(
        False,
        "-D",
        "--debug",
        help="Enable debug-mode feature. If you want to save the output file please use the --debug-path option.",
    ),
    debug_path: Optional[str] = typer.Option(
        None,
        help="The path to save the debug file at, if not specified the debug file will be printed to the terminal.",
    ),
    json_to_outputs: bool = typer.Option(
        False,
        help="Run json_to_outputs command on the context output of the query. If the context output does not exist or the `-r` flag is used, will use the raw response of the query.",
    ),
    prefix: Optional[str] = typer.Option(
        None,
        "-p",
        "--prefix",
        help="Used with `json-to-outputs` flag. Output prefix e.g. Jira.Ticket, VirusTotal.IP, the base path for the outputs that the script generates.",
    ),
    raw_response: bool = typer.Option(
        False,
        "-r",
        "--raw-response",
        help="Used with `json-to-outputs` flag. Use the raw response of the query for `json-to-outputs`.",
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
) -> None:
    """
    Run integration command on remote Demisto instance in the playground.
    DEMISTO_BASE_URL environment variable should contain the Demisto base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.run_cmd.runner import Runner

    kwargs: RunnerArgs = {
        "query": query,
        "insecure": insecure,
        "incident_id": incident_id,
        "debug": "-" if debug else None,  # Convert debug to str or None
        "debug_path": debug_path,
        "json_to_outputs": json_to_outputs,
        "prefix": prefix or "",
        "raw_response": raw_response,
    }

    update_command_args_from_config_file("run", kwargs)
    runner = Runner(**kwargs)
    return runner.run()

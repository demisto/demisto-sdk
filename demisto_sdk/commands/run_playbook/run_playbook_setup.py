import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator


@logging_setup_decorator
def run_playbook(
    ctx: typer.Context,
    playbook_id: str = typer.Option(
        ...,
        "--playbook-id",
        "-p",
        help="The playbook ID to run. This option is required.",
    ),
    url: str = typer.Option(
        None,
        "--url",
        "-u",
        help="URL to a Demisto instance. If not provided, the URL will be taken from DEMISTO_BASE_URL environment variable.",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait until the playbook run is finished and get a response.",
    ),
    timeout: int = typer.Option(
        90,
        "--timeout",
        "-t",
        help="Timeout to query for playbook's state. Relevant only if --wait has been passed.",
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Skip certificate validation."
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
    Run a playbook in Demisto.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    Example: DEMISTO_API_KEY=<API KEY> demisto-sdk run-playbook -p 'p_name' -u
    'https://demisto.local'.
    """
    if not playbook_id:
        typer.echo("Error: --playbook-id is required", err=True)
        raise typer.Exit(code=1)

    from demisto_sdk.commands.run_playbook.playbook_runner import PlaybookRunner

    # Replace the kwargs handling with direct arguments
    playbook_runner = PlaybookRunner(
        playbook_id=playbook_id, url=url, wait=wait, timeout=timeout, insecure=insecure
    )

    playbook_runner.run_playbook()

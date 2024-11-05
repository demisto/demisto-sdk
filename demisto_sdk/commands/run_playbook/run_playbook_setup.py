import typer


def run_playbook(
        playbook_id: str = typer.Option(
            ...,
            "--playbook-id", "-p",
            help="The playbook ID to run. This option is required."
        ),
        url: str = typer.Option(
            None,
            "--url", "-u",
            help="URL to a Demisto instance. If not provided, the URL will be taken from DEMISTO_BASE_URL environment variable."
        ),
        wait: bool = typer.Option(
            False,
            "--wait", "-w",
            help="Wait until the playbook run is finished and get a response."
        ),
        timeout: int = typer.Option(
            90,
            "--timeout", "-t",
            help="Timeout to query for playbook's state. Relevant only if --wait has been passed."
        ),
        insecure: bool = typer.Option(
            False,
            "--insecure",
            help="Skip certificate validation."
        )
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
        playbook_id=playbook_id,
        url=url,
        wait=wait,
        timeout=timeout,
        insecure=insecure
    )

    playbook_runner.run_playbook()

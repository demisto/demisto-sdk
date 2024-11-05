import typer

from demisto_sdk.utils.utils import update_command_args_from_config_file


def run(
    query: str = typer.Option(..., help="The query to run"),
    insecure: bool = typer.Option(False, help="Skip certificate validation"),
    incident_id: str = typer.Option(None, help="The incident to run the query on, if not specified the playground will be used."),
    debug: bool = typer.Option(False, help="Enable debug-mode feature. If you want to save the output file please use the --debug-path option."),
    debug_path: str = typer.Option(None, help="The path to save the debug file at, if not specified the debug file will be printed to the terminal."),
    json_to_outputs: bool = typer.Option(False, help="Run json_to_outputs command on the context output of the query. If the context output does not exist or the `-r` flag is used, will use the raw response of the query."),
    prefix: str = typer.Option(None, help="Used with `json-to-outputs` flag. Output prefix e.g. Jira.Ticket, VirusTotal.IP, the base path for the outputs that the script generates."),
    raw_response: bool = typer.Option(False, help="Used with `json-to-outputs` flag. Use the raw response of the query for `json-to-outputs`."),
):
    """
    Run integration command on remote Demisto instance in the playground.
    DEMISTO_BASE_URL environment variable should contain the Demisto base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    """
    from demisto_sdk.commands.run_cmd.runner import Runner

    kwargs = {
        "query": query,
        "insecure": insecure,
        "incident_id": incident_id,
        "debug": debug,
        "debug_path": debug_path,
        "json_to_outputs": json_to_outputs,
        "prefix": prefix,
        "raw_response": raw_response,
    }

    update_command_args_from_config_file("run", kwargs)
    runner = Runner(**kwargs)
    return runner.run()

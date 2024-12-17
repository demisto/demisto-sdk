import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.utils.utils import update_command_args_from_config_file


@logging_setup_decorator
def run_test_playbook(
    ctx: typer.Context,
    test_playbook_path: str = typer.Option(
        None,
        "-tpb",
        "--test-playbook-path",
        help="Path to test playbook to run, can be a path to specific "
        "test playbook or path to pack name for example: Packs/GitHub.",
    ),
    all: bool = typer.Option(
        False, help="Run all the test playbooks from this repository."
    ),
    wait: bool = typer.Option(
        True,
        "-w",
        "--wait",
        help="Wait until the test-playbook run is finished and get a response.",
    ),
    timeout: int = typer.Option(
        90,
        "-t",
        "--timeout",
        help="Timeout for the command. The test-playbook will continue to run in your instance.",
        show_default=True,
    ),
    insecure: bool = typer.Option(False, help="Skip certificate validation."),
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
    **Run a test playbook in a given XSOAR instance.**
    **This command creates a new instance in XSOAR and runs the given test playbook.**
    In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
    and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

    **Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
    - Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button in the top right corner, and not the browser URL.
    - API key should be of a `standard` security level, and have the `Instance Administrator` role.
    - To use the command the `XSIAM_AUTH_ID` environment variable should also be set.


    To set the environment variables, run the following shell commands:
    ```
    export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
    export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
    ```
    and for Cortex XSIAM or Cortex XSOAR 8.x
    ```
    export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
    ```
    Note!
    As long as `XSIAM_AUTH_ID` environment variable is set, SDK commands will be configured to work with an XSIAM instance.
    In order to set Demisto SDK to work with Cortex XSOAR instance, you need to delete the XSIAM_AUTH_ID parameter from your environment.
    ```bash
    unset XSIAM_AUTH_ID
    ```
    """
    from demisto_sdk.commands.run_test_playbook.test_playbook_runner import (
        TestPlaybookRunner,
    )

    kwargs = {
        "test_playbook_path": test_playbook_path,
        "all": all,
        "wait": wait,
        "timeout": timeout,
        "insecure": insecure,
    }

    update_command_args_from_config_file("run-test-playbook", kwargs)
    test_playbook_runner = TestPlaybookRunner(**kwargs)  # type: ignore[arg-type]
    raise typer.Exit(test_playbook_runner.manage_and_run_test_playbooks())

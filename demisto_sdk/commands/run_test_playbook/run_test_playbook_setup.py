import typer

from demisto_sdk.utils.utils import update_command_args_from_config_file

run_test_playbook_app = typer.Typer(name="run-test-playbook")


@run_test_playbook_app.command()
def run_test_playbook(
    test_playbook_path: str = typer.Option(None, help="Path to test playbook to run, can be a path to specific test playbook or path to pack name for example: Packs/GitHub."),
    all: bool = typer.Option(False, help="Run all the test playbooks from this repository."),
    wait: bool = typer.Option(True, "-w", help="Wait until the test-playbook run is finished and get a response."),
    timeout: int = typer.Option(90, "-t", help="Timeout for the command. The test-playbook will continue to run in your instance.", show_default=True),
    insecure: bool = typer.Option(False, help="Skip certificate validation."),
):
    """Run a test playbooks in your instance."""
    from demisto_sdk.commands.run_test_playbook.test_playbook_runner import TestPlaybookRunner

    kwargs = {
        "test_playbook_path": test_playbook_path,
        "all": all,
        "wait": wait,
        "timeout": timeout,
        "insecure": insecure,
    }

    update_command_args_from_config_file("run-test-playbook", kwargs)
    test_playbook_runner = TestPlaybookRunner(**kwargs)
    raise typer.Exit(test_playbook_runner.manage_and_run_test_playbooks())


if __name__ == "__main__":
    run_test_playbook_app()

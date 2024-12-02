import typer

from demisto_sdk.commands.test_content.playbook_flow_test import (
    run_playbook_flow_test,
)

playbook_flow_app = typer.Typer(
    name="playbook-flow",
    hidden=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
playbook_flow_app.command("test", no_args_is_help=True)(
    run_playbook_flow_test.test_playbook_flow_test
)

playbook_flow_app.command("generate_template_flow", no_args_is_help=True)(
    run_playbook_flow_test.test_playbook_flow_test)

if __name__ == "__main__":
    playbook_flow_app()


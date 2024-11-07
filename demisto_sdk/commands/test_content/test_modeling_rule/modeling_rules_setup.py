import typer

from demisto_sdk.commands.test_content.test_modeling_rule import (
    init_test_data,
    test_modeling_rule,
)

modeling_rules_app = typer.Typer(
    name="modeling-rules",
    hidden=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
modeling_rules_app.command("test", no_args_is_help=True)(
    test_modeling_rule.test_modeling_rule
)
modeling_rules_app.command("init-test-data", no_args_is_help=True)(
    init_test_data.init_test_data
)
if __name__ == "__main__":
    modeling_rules_app()

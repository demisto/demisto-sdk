import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.integration_diff.integration_diff_detector import (
    IntegrationDiffDetector,
)


@logging_setup_decorator
def integration_diff(
    ctx: typer.Context,
    new: str = typer.Option(
        ..., "-n", "--new", help="The path to the new version of the integration"
    ),
    old: str = typer.Option(
        ..., "-o", "--old", help="The path to the old version of the integration"
    ),
    docs_format: bool = typer.Option(
        False,
        "--docs-format",
        help="Whether output should be in the format for the "
        "version differences section in README.",
    ),
):
    """
    Check the differences between two versions of an integration and return a report of missing and changed elements in the new version.

    This command is used to identify missing or modified details in a new integration version. This is useful when
    developing a new version of an integration, and you want to make sure that all old integration version commands/arguments/outputs
    exist in the new version. Running this command will give you a detailed report about all the missing or changed commands/arguments/outputs.
    """
    integration_diff_detector = IntegrationDiffDetector(
        new=new,
        old=old,
        docs_format=docs_format,
    )
    result = integration_diff_detector.check_different()

    if result:
        raise typer.Exit(0)
    raise typer.Exit(1)

import typer
from demisto_sdk.commands.integration_diff.integration_diff_detector import IntegrationDiffDetector
import sys


def integration_diff(
    new: str = typer.Option(..., "-n", "--new", help="The path to the new version of the integration"),
    old: str = typer.Option(..., "-o", "--old", help="The path to the old version of the integration"),
    docs_format: bool = typer.Option(False, "--docs-format", help="Whether output should be in the format for the "
                                                                  "version differences section in README."),
):
    """
    Checks for differences between two versions of an integration and verifies that the new version covers
    the old version.
    """
    integration_diff_detector = IntegrationDiffDetector(
        new=new,
        old=old,
        docs_format=docs_format,
    )
    result = integration_diff_detector.check_different()

    if result:
        sys.exit(0)
    sys.exit(1)

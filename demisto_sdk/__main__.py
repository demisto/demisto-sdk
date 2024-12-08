import os
import platform

import typer
from dotenv import load_dotenv
from pkg_resources import DistributionNotFound, get_distribution
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from demisto_sdk.commands.common.configuration import Configuration, DemistoSDK
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.common.tools import (
    get_last_remote_release_version,
    get_release_note_entries,
    is_sdk_defined_working_offline,
)
from demisto_sdk.commands.content_graph.content_graph_setup import graph_cmd_group
from demisto_sdk.commands.coverage_analyze.coverage_analyze_setup import (
    coverage_analyze,
)
from demisto_sdk.commands.create_id_set.create_id_set_setup import create_id_set
from demisto_sdk.commands.doc_reviewer.doc_reviewer_setup import doc_review
from demisto_sdk.commands.download.download_setup import download
from demisto_sdk.commands.dump_api.dump_api_setup import dump_api
from demisto_sdk.commands.error_code_info.error_code_info_setup import error_code
from demisto_sdk.commands.find_dependencies.find_dependencies_setup import (
    find_dependencies,
)
from demisto_sdk.commands.format.format_setup import format
from demisto_sdk.commands.generate_docs.generate_docs_setup import generate_docs
from demisto_sdk.commands.generate_integration.generate_integration_setup import (
    generate_integration,
)
from demisto_sdk.commands.generate_modeling_rules.generate_modeling_rules import (
    generate_modeling_rules,
)
from demisto_sdk.commands.generate_outputs.generate_outputs_setup import (
    generate_outputs,
)
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests_setup import (
    generate_unit_tests,
)
from demisto_sdk.commands.generate_yml_from_python.generate_yml_from_python_setup import (
    generate_yml_from_python,
)
from demisto_sdk.commands.init.init_setup import init
from demisto_sdk.commands.integration_diff.intergation_diff_setup import (
    integration_diff,
)
from demisto_sdk.commands.lint.lint_setup import lint
from demisto_sdk.commands.merge_id_sets.merge_id_sets_setup import merge_id_sets
from demisto_sdk.commands.openapi_codegen.openapi_codegen_setup import openapi_codegen
from demisto_sdk.commands.postman_codegen.postman_codegen_setup import postman_codegen
from demisto_sdk.commands.pre_commit.pre_commit_setup import pre_commit
from demisto_sdk.commands.prepare_content.prepare_content_setup import prepare_content
from demisto_sdk.commands.run_cmd.run_cmd_setup import run
from demisto_sdk.commands.run_playbook.run_playbook_setup import run_playbook
from demisto_sdk.commands.run_test_playbook.run_test_playbook_setup import (
    run_test_playbook,
)
from demisto_sdk.commands.secrets.secrets_setup import secrets
from demisto_sdk.commands.setup_env.setup_env_setup import setup_env_command
from demisto_sdk.commands.split.split_setup import split
from demisto_sdk.commands.test_content.content_test_setup import test_content
from demisto_sdk.commands.test_content.test_modeling_rule.modeling_rules_setup import (
    modeling_rules_app,
)
from demisto_sdk.commands.update_release_notes.update_release_notes_setup import (
    update_release_notes,
)
from demisto_sdk.commands.update_xsoar_config_file.update_xsoar_config_file_setup import (
    xsoar_config_file_update,
)
from demisto_sdk.commands.upload.upload_setup import upload
from demisto_sdk.commands.validate.validate_setup import validate
from demisto_sdk.commands.xsoar_linter.xsoar_linter_setup import xsoar_linter
from demisto_sdk.commands.zip_packs.zip_packs_setup import zip_packs

app = typer.Typer()

# Registers the commands directly to the Demisto-SDK app.
app.command(name="export-api", help="Dumps the `demisto-sdk` API to a file.")(dump_api)
app.command(name="upload", help="Uploads an entity to Cortex XSOAR or Cortex XSIAM.")(
    upload
)
app.command(
    name="download",
    help="Downloads and merges content from a Cortex XSOAR or Cortex XSIAM tenant to your local repository.",
)(download)
app.command(
    name="run",
    help="Run integration or script commands in the Playground of a remote Cortex XSOAR/XSIAM instance and pretty print the output. ",
)(run)
app.command(
    name="run-playbook", help="Runs the given playbook in Cortex XSOAR or Cortex XSIAM."
)(run_playbook)
app.command(
    name="run-test-playbook",
    help="This command generates a test playbook from "
    "integration/script YAML arguments.",
)(run_test_playbook)
app.command(
    name="doc-review",
    help="Checks the spelling in Markdown and YAML files and compares release note files "
    "to our release note standards.",
)(doc_review)
app.command(name="integration-diff")(integration_diff)
app.command(
    name="generate-docs",
    help="Generates a README file for your integration, script or playbook. "
    "Used to create documentation files for Cortex XSOAR.",
)(generate_docs)
app.command(
    name="format",
    help="This command formats new or modified files to align with the Cortex standard.",
)(format)
app.command(name="coverage-analyze")(coverage_analyze)
app.command(
    name="zip-packs",
    help="Creates a zip file that can be uploaded to Cortex XSOAR via the Upload pack button in the Cortex XSOAR Marketplace or directly with the -u flag in this command.",
)(zip_packs)
app.command(
    name="split",
    help="Splits downloaded scripts, integrations and generic module files into multiple files. Integrations and scripts are split into the package format. Generic modules have their dashboards split into separate files and modify the module to the content repository standard.",
)(split)
app.command(name="find-dependencies")(find_dependencies)
app.command(
    name="generate-integration",
    help="generate a Cortex XSIAM/Cortex XSOAR integration "
    "from an integration config JSON file.",
)(generate_integration)
app.command(
    name="generate-outputs",
    help="Generates outputs for an integration. "
    "This command generates context paths automatically from an example file "
    "directly into an integration YAML file.",
)(generate_outputs)
app.command(
    name="generate-yml-from-python",
    help="Generates a YAML file from Python code that includes " "its special syntax.",
)(generate_yml_from_python)
app.command(name="init", help="Creates a new pack, integration, or script template.")(
    init
)
app.command(
    name="secrets",
    help="Run the secrets validator to catch sensitive data before exposing your code to a public repository.",
)(secrets)
app.command(
    name="openapi-codegen",
    help="Generate a Cortex XSIAM or Cortex XSOAR integration package (YAML and Python files) with a dedicated tool in the Demisto SDK.",
)(openapi_codegen)
app.command(
    name="postman-codegen",
    help="Generate an integration (YAML file) from a Postman Collection v2.1. Note the generated integration is in the YAML format.",
)(postman_codegen)
app.command(
    name="setup-env",
    help="Creates a content environment and and integration/script environment.",
)(setup_env_command)
app.command(
    name="update-release-notes",
    help="Automatically generates release notes for a given pack and updates the pack_metadata.json version for changed items.",
)(update_release_notes)
app.command(
    name="validate",
    help="Ensures that the content repository files are valid and are able to be processed by the platform.",
)(validate)
app.command(name="prepare-content", help="Prepares content to upload to the platform.")(
    prepare_content
)
app.command(name="unify", help="Prepares content to upload to the platform.")(
    prepare_content
)
app.command(name="xsoar-lint", help="Runs the xsoar lint on the given paths.")(
    xsoar_linter
)
app.command(
    name="xsoar-config-file-update", help="Handle your XSOAR Configuration File."
)(xsoar_config_file_update)
app.command(
    name="pre-commit",
    help="Enhances the content development experience by running a variety of checks and linters.",
)(pre_commit)
app.command(
    name="error-code", help="Quickly find relevant information regarding an error code."
)(error_code)
app.command(
    name="test-content",
    help="Created incidents for selected test-playbooks and gives a report about the results.",
    hidden=True,
)(test_content)
app.add_typer(
    graph_cmd_group,
    name="graph",
    help="The content graph commands provide a set of commands for creating, loading, and managing a graph "
    "database representation of the content repository, enabling you to visualize the metadata of "
    "content and the relationships between content packs, including dependencies.",
)
app.add_typer(modeling_rules_app, name="modeling-rules")
app.command(name="generate-modeling-rules", help="Generated modeling-rules.")(
    generate_modeling_rules
)
app.command(
    name="lint", help="Deprecated, use demisto-sdk pre-commit instead.", hidden=True
)(lint)
app.command(
    name="create-id-set",
    help="Deprecated, use demisto-sdk graph command instead.",
    hidden=True,
)(create_id_set)
app.command(
    name="merge-id-sets",
    help="Deprecated. Merge two id_sets.",
    hidden=True,
)(merge_id_sets)
app.command(
    name="generate-unit-tests",
    help="This command generates unit tests automatically from an integration's Python code.",
)(generate_unit_tests)


@logging_setup_decorator
@app.callback(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show the current version of demisto-sdk."
    ),
    release_notes: bool = typer.Option(
        False,
        "--release-notes",
        "-rn",
        help="Show the release notes for the current version.",
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
    sdk = DemistoSDK()  # Initialize your SDK class
    sdk.configuration = Configuration()  # Initialize the configuration
    ctx.obj = sdk  # Pass sdk instance to context
    load_dotenv(CONTENT_PATH / ".env", override=True)
    if platform.python_version_tuple()[:2] == ("3", "9"):
        message = typer.style(
            "Warning: Demisto-SDK will soon stop supporting Python 3.9. Please update your python environment.",
            fg=typer.colors.RED,
        )
        typer.echo(message)

    if platform.system() == "Windows":
        typer.echo(
            "Warning: Using Demisto-SDK on Windows is not supported. Use WSL2 or run in a container."
        )

    if version:
        show_version()
        raise typer.Exit()

    if release_notes:
        show_release_notes()
        raise typer.Exit()


def get_version_info():
    """Retrieve version and latest release information."""
    try:
        current_version = get_distribution("demisto-sdk").version
    except DistributionNotFound:
        current_version = "dev"
        typer.echo(
            "Could not find the version of demisto-sdk. Running in development mode."
        )
    else:
        last_release = ""
        if not os.environ.get("CI") and not is_sdk_defined_working_offline():
            last_release = get_last_remote_release_version()
        return current_version, last_release
    return current_version, None


def show_version():
    """Display the SDK version and notify if updates are available."""
    current_version, last_release = get_version_info()
    typer.echo(f"demisto-sdk version: {current_version}")

    if last_release and current_version != last_release:
        message = typer.style(
            f"A newer version ({last_release}) is available. To update, run 'pip install --upgrade demisto-sdk'",
            fg=typer.colors.YELLOW,
        )
        typer.echo(message)


def show_release_notes():
    """Display release notes for the currently installed demisto-sdk version."""
    current_version, _ = get_version_info()
    rn_entries = get_release_note_entries(current_version)
    remote_changelog_referral = typer.style(
        "See https://github.com/demisto/demisto-sdk/blob/master/CHANGELOG.md for the full demisto-sdk changelog",
        fg=typer.colors.YELLOW,
    )
    if rn_entries:
        # The Rich library centers Markdown headings by default.
        # So the '###' prefix is removed temporary in this command so subtitles will be aligned to the left when printed.
        rn_entries = rn_entries.replace("###", "")
        md = Markdown(rn_entries, justify="left")
        Console().print(
            Panel(
                md,
                title_align="left",
                subtitle_align="left",
                subtitle=remote_changelog_referral,
                title=f"Release notes of the currently installed demisto-sdk version: {current_version}.",
            )
        )
    else:
        typer.echo(
            f"Could not retrieve release notes for this version. {remote_changelog_referral}"
        )


if __name__ == "__main__":
    typer.echo("Running Demisto-SDK CLI")
    app()  # Run the main app

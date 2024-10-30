import typer

from demisto_sdk.commands.download.download_setup import download
from demisto_sdk.commands.upload.upload_setup import upload
from demisto_sdk.commands.run_playbook.run_playbook_setup import run_playbook
from demisto_sdk.commands.doc_reviewer.doc_reviwer_setup import doc_review
from demisto_sdk.commands.integration_diff.intergation_diff_setup import integration_diff
from demisto_sdk.commands.generate_docs.generate_docs_setup import generate_docs
from demisto_sdk.commands.format.format_setup import format
from demisto_sdk.commands.coverage_analyze.coverage_analyze_setup import coverage_analyze
from demisto_sdk.commands.zip_packs.zip_packs_setup import zip_packs
from demisto_sdk.commands.split.split_setup import split
from demisto_sdk.commands.find_dependencies.find_dependencies_setup import find_dependencies
from demisto_sdk.commands.generate_integration.generate_integration_setup import generate_integration
from demisto_sdk.commands.generate_outputs.generate_outputs_setup import generate_outputs
from demisto_sdk.commands.generate_yml_from_python.generate_yml_from_python_setup import generate_yml_from_python
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests_setup import generate_unit_tests
from demisto_sdk.commands.init.init_setup import init
from demisto_sdk.commands.openapi_codegen.openapi_codegen_setup import openapi_codegen
from demisto_sdk.commands.postman_codegen.postman_codegen_setup import postman_codegen
# from demisto_sdk.commands.prepare_content.prepare_content_setup import prepare_content
from demisto_sdk.commands.run_cmd.run_cmd_setup import run
from demisto_sdk.commands.run_test_playbook.run_test_playbook_setup import run_test_playbook
from demisto_sdk.commands.secrets.secrets_setup import secrets
# from demisto_sdk.commands.setup_env.setup_env_setup import setup_env
from demisto_sdk.commands.update_release_notes.update_release_notes_setup import update_release_notes
from demisto_sdk.commands.validate.validate_setup import validate
from demisto_sdk.config import get_config


app = typer.Typer()

# Registers the commands directly to the Demisto-SDK app.
app.command(name="upload")(upload)
app.command(name="download")(download)
app.command(name="run")(run)
app.command(name="run-playbook")(run_playbook)
app.command(name="run-test-playbook")(run_test_playbook)
app.command(name="doc-review")(doc_review)
app.command(name="integration-diff")(integration_diff)
app.command(name="generate-docs")(generate_docs)
app.command(name="format")(format)
app.command(name="coverage-analyze")(coverage_analyze)
app.command(name="zip-packs")(zip_packs)
app.command(name="split")(split)
app.command(name="find-dependencies")(find_dependencies)
app.command(name="generate-integration")(generate_integration)
app.command(name="generate-outputs")(generate_outputs)
app.command(name="generate-yml-from-python")(generate_yml_from_python)
app.command(name="generate-unit-tests")(generate_unit_tests)
app.command(name="init")(init)
app.command(name="secrets")(secrets)
app.command(name="openapi-codegen")(openapi_codegen)
app.command(name="postman-codegen")(postman_codegen)
# app.command(name="setup-env")(setup_env)
app.command(name="update-release-notes")(update_release_notes)
app.command(name="validate")(validate)
# app.command(name="prepare-content")(prepare_content)

config_instance = get_config()

if __name__ == "__main__":
    typer.echo("Running demisto-sdk CLI")
    app()  # Run the main app

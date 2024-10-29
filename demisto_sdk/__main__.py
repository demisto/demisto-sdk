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
from demisto_sdk.config import get_config, DemistoSDK


app = typer.Typer()

# Registers the commands directly to the Demisto-SDK app.
app.command(name="upload")(upload)
app.command(name="download")(download)
app.command(name="run-playbook")(run_playbook)
app.command(name="doc-review")(doc_review)
app.command(name="integration-diff")(integration_diff)
app.command(name="generate-docs")(generate_docs)
app.command(name="format")(format)
app.command(name="coverage-analyze")(coverage_analyze)
app.command(name="zip-packs")(zip_packs)
app.command(name="split")(split)

config_instance = get_config()

if __name__ == "__main__":
    typer.echo("Running demisto-sdk CLI")
    app()  # Run the main app

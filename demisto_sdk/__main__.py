import typer

from demisto_sdk.commands.download.download_setup import download
from demisto_sdk.commands.upload.upload_setup import upload

app = typer.Typer()

# Registers the commands directly to the Demisto-SDK app.
app.command(name="upload")(upload)
app.command(name="download")(download)

if __name__ == "__main__":
    typer.echo("Running demisto-sdk CLI")
    app()  # Run the main app

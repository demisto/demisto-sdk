# main.py

import typer
from demisto_sdk.commands.upload.upload_app import upload_app  # Import the Typer app from upload.py
from demisto_sdk.commands.download.download_app import download_app  # Another example for download.py
from demisto_sdk.commands.run_playbook.run_playbook_app import run_playbook_app

app = typer.Typer()

# Add sub-apps from other modules
app.add_typer(upload_app, name="upload")
app.add_typer(download_app, name="download")
app.add_typer(run_playbook_app, name="run_playbook")

if __name__ == "__main__":
    app()

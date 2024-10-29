# # import functools
# # import os
# # import platform
# # import typer
# # from demisto_sdk.commands.upload.upload_app import upload_app
# # from demisto_sdk.commands.download.download_app import download_app
# # from demisto_sdk.commands.run_playbook.run_playbook_app import run_playbook_app
# # from demisto_sdk.commands.common.configuration import Configuration
# # from demisto_sdk.commands.common.logger import logging_setup
# # from demisto_sdk.commands.common.tools import (
# #     get_last_remote_release_version,
# #     get_release_note_entries,
# # )
# #
# # from dotenv import load_dotenv
# # # Third party packages
# #
# # # Common tools
# #
# #
# # app = typer.Typer()
# #
# #
# # # def logging_setup_decorator(func):
# # #     """Decorator to set up logging for commands."""
# # #
# # #     @functools.wraps(func)
# # #     def wrapper(*args, **kwargs):
# # #         logging_setup(
# # #             console_threshold=kwargs.get("console_log_threshold") or "INFO",
# # #             file_threshold=kwargs.get("file_log_threshold") or "DEBUG",
# # #             path=kwargs.get("log_file_path"),
# # #             calling_function=func.__name__,
# # #         )
# # #         return func(*args, **kwargs)
# # #
# # #     return wrapper
# #
# #
# # # Add sub-apps from other modules
# # app.add_typer(upload_app, name="upload")
# # app.add_typer(download_app, name="download")
# # app.add_typer(run_playbook_app, name="run_playbook")
# #
# #
# # class DemistoSDK:
# #     """The core class for the SDK."""
# #
# #     def __init__(self):
# #         self.configuration = None
# #
# #
# # sdk = DemistoSDK()
# #
# #
# # @app.callback()
# # def main(
# #         version: bool = typer.Option(
# #             False, "--version", "-v", help="Get the demisto-sdk version."
# #         ),
# #         release_notes: bool = typer.Option(
# #             False, "--release-notes", "-rn", help="Display the release notes for the current version."
# #         ),
# #         console_log_threshold: str = typer.Option(
# #             "INFO", "--console-log-threshold", help="Minimum logging threshold for console logger. Default: INFO"
# #         ),
# #         file_log_threshold: str = typer.Option(
# #             "DEBUG", "--file-log-threshold", help="Minimum logging threshold for file logger. Default: DEBUG"
# #         ),
# #         log_file_path: str = typer.Option(
# #             None, "--log-file-path", help="Path to save log files onto."
# #         ),
# # ):
# #     """
# #     The main entry point for DemistoSDK.
# #     This command provides common setup like logging, version checking, and loading the environment.
# #     """
# #     sdk.configuration = Configuration()
# #
# #     # Load environment variables from .env file
# #     load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)
# #
# #     if platform.system() == "Windows":
# #         typer.echo("Warning: Using Demisto-SDK on Windows is not supported. Use WSL2 or run in a container.")
# #
# #     # Version handling
# #     if version:
# #         try:
# #             from pkg_resources import get_distribution, DistributionNotFound
# #             __version__ = get_distribution("demisto-sdk").version
# #         except DistributionNotFound:
# #             __version__ = "dev"
# #             typer.echo("Could not determine the version of the demisto-sdk (running in development mode).")
# #
# #         typer.echo(f"Demisto-SDK version: {__version__}")
# #
# #         last_release = get_last_remote_release_version()
# #         if last_release and __version__ != last_release:
# #             typer.echo(
# #                 f"A newer version ({last_release}) is available. To update, run 'pip install --upgrade demisto-sdk'.")
# #         raise typer.Exit()
# #
# #     # Release notes handling
# #     if release_notes:
# #         try:
# #             from pkg_resources import get_distribution, DistributionNotFound
# #             __version__ = get_distribution("demisto-sdk").version
# #         except DistributionNotFound:
# #             __version__ = "dev"
# #             typer.echo("Could not determine the version of the demisto-sdk.")
# #
# #         rn_entries = get_release_note_entries(__version__)
# #         if rn_entries:
# #             typer.echo("\nRelease notes for the current version:\n")
# #             typer.echo(rn_entries)
# #         else:
# #             typer.echo("Could not retrieve the release notes for this version.")
# #         raise typer.Exit()
# #
# #     logging_setup(
# #         calling_function="CLI",
# #         console_threshold=console_log_threshold or "INFO",
# #         file_threshold=file_log_threshold or "DEBUG",
# #         path=log_file_path,
# #         initial=False
# #     )
# #
# #
# # if __name__ == "__main__":
# #     app()
# from pathlib import Path
#
# import typer
# from demisto_sdk.commands.upload.upload_app import upload_app  # Import the Typer app from upload.py
# from demisto_sdk.commands.download.download_app import download_app  # Another example for download.py
# from demisto_sdk.commands.run_playbook.run_playbook_app import run_playbook_app
#
# app = typer.Typer()
#
# # Add sub-apps from other modules
# app.add_typer(upload_app, name="upload")
# app.add_typer(download_app, name="download")
# app.add_typer(run_playbook_app, name="run_playbook")
#
#
# @app.command()
# def hello(
#         output: Path = typer.Option(None, "--output", "-o", help="A path to a pack directory to download content to.")
# ):
#     print("Hello from Typer")
#
#
# if __name__ == "__main__":
#     print("Running demisto-sdk CLI")
#     app()
# __main__.py
# from pathlib import Path
#
# import typer
# from demisto_sdk.commands.upload.upload_app import upload_app  # Import the Typer app from upload.py
#
# app = typer.Typer()
#
# # Register the external app
# app.add_typer(upload_app, name="upload")
#
# @app.command()
# def hello(
#     output: Path = typer.Option(None, "--output", "-o", help="A path to a pack directory to download content to.")
# ):
#     print("Hello from Typer")
#
# if __name__ == "__main__":
#     print("Running demisto-sdk CLI")
#     app()

# demisto_sdk/__main__.py

import typer

from demisto_sdk.commands.download.download_app import download
from demisto_sdk.commands.upload.upload_app import upload  # Import the upload function

app = typer.Typer()

# Adding the upload command directly
app.command(name="upload")(upload)  # Registers the upload command
app.command(name="download")(download)

if __name__ == "__main__":
    typer.echo("Running demisto-sdk CLI")  # Debug print
    app()  # Run the main app

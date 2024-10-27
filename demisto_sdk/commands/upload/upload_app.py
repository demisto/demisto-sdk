# # demisto_sdk/commands/upload/upload_app.py
#
# import logging
# from pathlib import Path
# import typer
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# # Initialize a Typer app for upload commands
# upload_app = typer.Typer()
#
# @upload_app.command(help="Upload integration or pack to Demisto instance.")
# def upload(
#     input_path: Path = typer.Option(
#         ..., "--input", "-i", help="The path of file or a directory to upload."
#     )
# ):
#     logger.info(f"Uploading {input_path}")
#     print("Executing the upload function...")




import functools

import typer
from pathlib import Path

from demisto_sdk.commands.common.logger import logger, logging_setup

# Initialize the Typer app
upload_app = typer.Typer()


@upload_app.command(help="Upload integration or pack to Demisto instance.")
def upload(
    input_path: Path = typer.Option(
        ...,
        "--input", "-i",
        exists=True,
        resolve_path=True,
        help="The path of file or a directory to upload. The following are supported:\n"
             "- Pack\n"
             "- A content entity directory that is inside a pack. For example: an Integrations "
             "directory or a Layouts directory.\n"
             "- Valid file that can be imported to Cortex XSOAR manually. For example, a playbook: "
             "helloWorld.yml",
    ),
    input_config_file: Path = typer.Option(
        None,
        "--input-config-file",
        exists=True,
        resolve_path=True,
        help="The path to the config file to download all the custom packs from"
    ),
    zip: bool = typer.Option(
        True,
        "--zip/--no-zip",
        help="Compress the pack to zip before upload. Relevant only for packs."
    ),
    tpb: bool = typer.Option(
        False,
        "--tpb",
        help="Adds the test playbook for upload when this flag is used. Relevant only for packs."
    ),
    xsiam: bool = typer.Option(
        False,
        "--xsiam", "-x",
        help="Upload the pack to the XSIAM server. Must be used together with --zip."
    ),
    marketplace: str = typer.Option(
        None,
        "--marketplace",
        help="The marketplace to which the content will be uploaded."
    ),
    keep_zip: Path = typer.Option(
        None,
        "--keep-zip",
        exists=True,
        help="Directory where to store the zip after creation. Relevant only for packs "
             "and in case the --zip flag is used."
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help="Skip certificate validation."
    ),
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Only for upload zipped packs. If true, will skip upload packs validation. "
             "Use this only when migrating existing custom content to packs."
    ),
    reattach: bool = typer.Option(
        False,
        "--reattach",
        help="Reattach the detached files in the XSOAR instance for the CI/CD Flow. "
             "If you set the --input-config-file flag, any detached item in your XSOAR instance "
             "that isn't currently in the repo's SystemPacks folder will be re-attached."
    ),
    override_existing: bool = typer.Option(
        False,
        "--override-existing",
        help="If True, this determines whether a confirmation prompt should be skipped "
             "when attempting to upload a content pack that is already installed."
    ),
):
    """
    Upload integration or pack to Demisto instance.
    DEMISTO_BASE_URL environment variable should contain the Demisto server base URL.
    DEMISTO_API_KEY environment variable should contain a valid Demisto API Key.
    * Note: Uploading classifiers to Cortex XSOAR is available from version 6.0.0 and up. *
    """
    logger.info(f"Upload initiated with input: {input_path}, config file: {input_config_file}, zip: {zip}, "
                f"tpb: {tpb}, xsiam: {xsiam}, marketplace: {marketplace}, keep_zip: {keep_zip}, "
                f"insecure: {insecure}, skip_validation: {skip_validation}, "
                f"reattach: {reattach}, override_existing: {override_existing}.")

    try:
        # Call the actual upload logic
        upload_content_entity(
            input=input_path,
            input_config_file=input_config_file,
            zip=zip,
            tpb=tpb,
            xsiam=xsiam,
            marketplace=marketplace,
            keep_zip=keep_zip,
            insecure=insecure,
            skip_validation=skip_validation,
            reattach=reattach,
            override_existing=override_existing,
        )
        logger.info("Upload completed successfully.")
    except Exception as e:
        logger.error(f"Error during upload: {e}")
        raise  # Reraise the exception to inform Typer of the failure


def upload_content_entity(**kwargs):
    # Placeholder function for the upload logic
    logger.debug(f"Uploading content with the following parameters: {kwargs}")
    # Simulating the upload process; replace with actual logic
    typer.echo(f"Uploading content with the following parameters: {kwargs}")








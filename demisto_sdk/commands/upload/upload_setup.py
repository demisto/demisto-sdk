from pathlib import Path

import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.upload.upload import upload_content_entity


@logging_setup_decorator
def upload(
    ctx: typer.Context,
    input_path: Path = typer.Option(
        None,
        "--input",
        "-i",
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
        help="The path to the config file to download all the custom packs from.",
    ),
    zip: bool = typer.Option(
        True,
        "-z/-nz",
        "--zip/--no-zip",
        help="Compress the pack to zip before upload. Relevant only for packs.",
    ),
    tpb: bool = typer.Option(
        False,
        "-tpb",
        help="Adds the test playbook for upload when this flag is used. Relevant only for packs.",
    ),
    xsiam: bool = typer.Option(
        False,
        "--xsiam",
        "-x",
        help="Upload the pack to the XSIAM server. Must be used together with --zip.",
    ),
    marketplace: str = typer.Option(
        None,
        "-mp",
        "--marketplace",
        help="The marketplace to which the content will be uploaded.",
    ),
    keep_zip: Path = typer.Option(
        None,
        "--keep-zip",
        exists=True,
        help="Directory where to store the zip after creation. Relevant only for packs "
        "and in case the --zip flag is used.",
    ),
    insecure: bool = typer.Option(
        False, "--insecure", help="Skip certificate validation."
    ),
    skip_validation: bool = typer.Option(
        False,
        "--skip_validation",
        help="Only for upload zipped packs. If true, will skip upload packs validation. "
        "Use this only when migrating existing custom content to packs.",
    ),
    reattach: bool = typer.Option(
        False,
        "--reattach",
        help="Reattach the detached files in the XSOAR instance for the CI/CD Flow. "
        "If you set the --input-config-file flag, any detached item in your XSOAR instance "
        "that isn't currently in the repo's SystemPacks folder will be re-attached.",
    ),
    override_existing: bool = typer.Option(
        False,
        "--override-existing",
        help="If True, this determines whether a confirmation prompt should be skipped "
        "when attempting to upload a content pack that is already installed.",
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
    """
    ** Upload a content entity to Cortex XSOAR/XSIAM.**

    In order to run the command, `DEMISTO_BASE_URL` environment variable should contain the Cortex XSOAR/XSIAM instance URL,
    and `DEMISTO_API_KEY` environment variable should contain a valid Cortex XSOAR/XSIAM API Key.

    **Notes for Cortex XSIAM or Cortex XSOAR 8.x:**
    - Cortex XSIAM Base URL should be retrieved from XSIAM instance -> Settings -> Configurations -> API Keys -> `Copy URL` button in the top right corner, and not the browser URL.
    - API key should be of a `standard` security level, and have the `Instance Administrator` role.
    - To use the command the `XSIAM_AUTH_ID` environment variable should also be set.

    To set the environment variables, run the following shell commands:
    ```
    export DEMISTO_BASE_URL=<YOUR_DESMISTO_BASE_URL>
    export DEMISTO_API_KEY=<YOUR_DEMISTO_API_KEY>
    ```
    and for Cortex XSIAM or Cortex XSOAR 8.x
    ```
    export XSIAM_AUTH_ID=<THE_XSIAM_AUTH_ID>
    ```
    Note!
    As long as `XSIAM_AUTH_ID` environment variable is set, SDK commands will be configured to work with an XSIAM instance.
    In order to set Demisto SDK to work with Cortex XSOAR instance, you need to delete the XSIAM_AUTH_ID parameter from your environment.
    ```bash
    unset XSIAM_AUTH_ID
    ```
    """

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

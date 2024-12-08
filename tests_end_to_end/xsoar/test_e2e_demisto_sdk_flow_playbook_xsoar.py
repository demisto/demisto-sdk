from pathlib import Path

import typer
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs import generate_playbook_doc
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from tests_end_to_end import e2e_tests_utils
from TestSuite.test_tools import ChangeCWD


def test_e2e_demisto_sdk_flow_playbook_testsuite(tmp_path):
    """This flow checks:
    1. Creates a new playbook and uploads it demisto-sdk upload command.
    2. Downloads the playbook using demisto-sdk upload command.
    3. Generates docs for the playbook using demisto-sdk generate-docs command.
    4. Formatting the playbook using the demisto-sdk format command.
    5. Validates the playbook using the demisto-sdk validate command.
    6. Uploads the playbook using the demisto-sdk upload command.
    """
    # Importing TestSuite classes from Demisto-SDK, as they are excluded when pip installing the SDK.
    e2e_tests_utils.cli(f"mkdir {tmp_path}/git")
    e2e_tests_utils.git_clone_demisto_sdk(
        destination_folder=f"{tmp_path}/git/demisto-sdk",
        sdk_git_branch=DEMISTO_GIT_PRIMARY_BRANCH,
    )
    from TestSuite.playbook import Playbook
    from TestSuite.repo import Repo

    repo = Repo(tmp_path)

    unique_id = 456
    pack_name = "foo_" + str(unique_id)
    pack = repo.create_pack(name=pack_name)
    playbook_name = "pb_" + pack_name
    playbook: Playbook = pack.create_playbook(name=playbook_name)
    playbook.create_default_playbook(name=playbook_name)
    source_playbook_path = Path(playbook.path)
    assert source_playbook_path.exists()

    logger.info(f"Trying to upload playbook from {source_playbook_path}")
    uploader = Uploader(input=source_playbook_path, insecure=True)
    try:
        uploader.upload()
    except typer.Exit as e:
        assert e.exit_code == 0

    # Preparing updated pack folder
    e2e_tests_utils.cli(f"mkdir {tmp_path}/Packs/{pack_name}_testsuite")

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmp_path}/Packs/{pack_name}_testsuite/Playbooks"
    )
    downloader = Downloader(
        output=f"{tmp_path}/Packs/{pack_name}_testsuite",
        input=(playbook_name,),
        insecure=True,
    )
    try:
        downloader.download()
    except typer.Exit as e:
        assert e.exit_code == 0
    dest_playbook_path = Path(
        f"{tmp_path}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    assert dest_playbook_path.exists()

    logger.info(
        f"Generating docs (creating a readme file) for playbook {dest_playbook_path}"
    )
    generate_playbook_doc.generate_playbook_doc(input_path=str(dest_playbook_path))
    assert dest_playbook_path.with_name(f"{playbook_name}_README.md").exists()

    logger.info(f"Formating playbook {dest_playbook_path}")
    with ChangeCWD(pack.repo_path):
        try:
            format_manager(
                input=str(dest_playbook_path),
                assume_answer=True,
            )
        except typer.Exit as e:
            assert e.exit_code == 0
        logger.info(f"Validating playbook {dest_playbook_path}")
        OldValidateManager(file_path=str(dest_playbook_path)).run_validation()

        logger.info(f"Uploading updated playbook {dest_playbook_path}")
        uploader = Uploader(
            input=dest_playbook_path,
            insecure=True,
        )
        try:
            uploader.upload()
        except typer.Exit as e:
            assert e.exit_code == 0


def test_e2e_demisto_sdk_flow_playbook_client(tmp_path, insecure: bool = True):
    """This flow checks:
    1. Creates a new playbook and uploading it to the machine using an http request.
    2. Downloads the playbook using demisto-sdk download command.
    3. Downloads the script CommonServerUserPowerShell using demisto-sdk upload command.
    4. Generates docs for the playbook using demisto-sdk generate-docs command.
    5. Formatting the playbook using the demisto-sdk format command.
    6. Validates the playbook using the demisto-sdk validate command.
    7. Uploads the playbook using the demisto-sdk upload command.
    8. Deletes the playbook using an http request.
    """
    unique_id = 789
    pack_name = "foo_" + str(unique_id)
    playbook_name = "pb_" + str(unique_id)
    dest_playbook_path = Path(
        f"{tmp_path}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )

    unique_id = 789
    pack_name = "foo_" + str(unique_id)
    playbook_name = "pb_" + str(unique_id)

    demisto_client = e2e_tests_utils.connect_to_server(insecure=insecure)
    body = [
        {
            "name": playbook_name,
            "propagationLabels": ["all"],
            "tasks": {
                "0": {
                    "id": "0",
                    "unqiueId": "0",
                    "type": "start",
                    "nextTasks": None,
                    "task": {},
                }
            },
        }
    ]

    header_params = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
    }

    try:
        demisto_client.api_client.call_api(
            resource_path="/playbook/save",
            method="POST",
            header_params=header_params,
            body=body,
        )
    except ApiException as ae:
        logger.info(f"*** Failed to create playbook {playbook_name}, reason: {ae}")
        assert False

    # Preparing updated pack folder
    e2e_tests_utils.cli(f"mkdir -p {tmp_path}/Packs/{pack_name}_client")

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmp_path}/Packs/{pack_name}_client/Playbooks"
    )
    downloader = Downloader(
        output=f"{tmp_path}/Packs/{pack_name}_client",
        input=(playbook_name,),
        insecure=True,
    )
    try:
        downloader.download()
    except typer.Exit as e:
        assert e.exit_code == 0
    dest_playbook_path = Path(
        f"{tmp_path}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    assert dest_playbook_path.exists()

    logger.info(
        f"Generating docs (creating a readme file for the playbook {dest_playbook_path}"
    )
    generate_playbook_doc.generate_playbook_doc(input_path=str(dest_playbook_path))
    assert Path(
        f"{tmp_path}/Packs/{pack_name}_client/Playbooks/{playbook_name}_README.md"
    ).exists()

    logger.info(f"Formating playbook {dest_playbook_path}")

    with ChangeCWD(str(dest_playbook_path.parent)):
        try:
            format_manager(
                input=str(dest_playbook_path),
                assume_answer=True,
            )
        except typer.Exit as e:
            assert e.exit_code == 0
        logger.info(f"Validating playbook {dest_playbook_path}")
        OldValidateManager(file_path=str(dest_playbook_path)).run_validation()

        logger.info(f"Uploading updated playbook {dest_playbook_path}")
        uploader = Uploader(
            input=dest_playbook_path,
            insecure=True,
        )
        try:
            uploader.upload()
        except typer.Exit as e:
            assert e

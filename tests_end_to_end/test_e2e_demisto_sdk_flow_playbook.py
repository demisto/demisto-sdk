import random
from os import path

import e2e_tests_utils
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs import generate_playbook_doc
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.validate_manager import ValidateManager


def test_e2e_demisto_sdk_flow_playbook_testsuite(tmpdir):
    # Importing TestSuite classes from Demisto-SDK, as they are excluded when pip installing the SDK.
    e2e_tests_utils.cli(f"mkdir {tmpdir}/git")
    e2e_tests_utils.git_clone_demisto_sdk(
        destination_folder=f"{tmpdir}/git/demisto-sdk", sdk_git_branch="master"
    )
    from TestSuite.playbook import Playbook
    from TestSuite.repo import Repo

    repo = Repo(tmpdir)

    unique_id = random.randint(1, 1000)
    pack_name = "foo_" + str(unique_id)
    pack = repo.create_pack(name=pack_name)
    playbook_name = "pb_" + pack_name
    playbook: Playbook = pack.create_playbook(name=playbook_name)
    playbook.create_default_playbook(name=playbook_name)
    assert path.exists(f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}.yml")

    logger.info(
        f"Trying to upload playbook from {tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}.yml"
    )
    Uploader(
        input=f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}.yml", insecure=True
    ).upload()

    # Preparing updated pack folder
    e2e_tests_utils.cli(f"mkdir {tmpdir}/Packs/{pack_name}_testsuite")

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmpdir}/Packs/{pack_name}_testsuite/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_testsuite",
        input=[playbook_name],
        insecure=True,
    ).download()
    assert path.exists(
        f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )

    logger.info(
        "Generating docs (creating a readme file)"
        f" for the playbook {tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    generate_playbook_doc.generate_playbook_doc(
        input_path=f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    assert path.exists(
        f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}_README.md"
    )

    logger.info(
        f"Formating playbook {tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    format_manager(
        input=f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml",
        assume_yes=True,
    )
    logger.info(
        f"Validating playbook {tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    ValidateManager(
        file_path=f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    ).run_validation()

    logger.info(
        f"Uploading updated playbook {tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    Uploader(
        input=f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}.yml", insecure=True
    ).upload()


def test_e2e_demisto_sdk_flow_playbook_client(tmpdir, insecure: bool = True):
    unique_id = random.randint(1, 1000)
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
    e2e_tests_utils.cli(f"mkdir -p {tmpdir}/Packs/{pack_name}_client")

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmpdir}/Packs/{pack_name}_client/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_client",
        input=[playbook_name],
        insecure=True,
    ).download()
    assert path.exists(
        f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )

    logger.info(
        "Generating docs (creating a readme file)"
        f" for the playbook {tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    generate_playbook_doc.generate_playbook_doc(
        input_path=f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    assert path.exists(
        f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}_README.md"
    )

    logger.info(
        f"Formating playbook {tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    format_manager(
        input=f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml",
        assume_yes=True,
    )
    logger.info(
        f"Validating playbook {tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    ValidateManager(
        file_path=f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    ).run_validation()

    logger.info(
        f"Uploading updated playbook {tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    Uploader(
        input=f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}.yml", insecure=True
    ).upload()

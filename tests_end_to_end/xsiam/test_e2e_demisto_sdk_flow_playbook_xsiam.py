from pathlib import Path

from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients import get_client_from_server_type
from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs import generate_playbook_doc
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from tests_end_to_end import e2e_tests_utils
from TestSuite.playbook import Playbook
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


def test_e2e_demisto_sdk_flow_playbook_testsuite(tmpdir):
    # Importing TestSuite classes from Demisto-SDK, as they are excluded when pip installing the SDK.
    e2e_tests_utils.cli(f"mkdir {tmpdir}/git")
    e2e_tests_utils.git_clone_demisto_sdk(
        destination_folder=f"{tmpdir}/git/demisto-sdk",
        sdk_git_branch=DEMISTO_GIT_PRIMARY_BRANCH,
    )

    repo = Repo(tmpdir)

    unique_id = 456
    pack_name = "foo_" + str(unique_id)
    pack = repo.create_pack(name=pack_name)
    playbook_name = "pb_" + pack_name
    playbook: Playbook = pack.create_playbook(name=playbook_name)
    playbook.create_default_playbook(name=playbook_name)
    source_playbook_path = Path(playbook.path)
    source_pack_path = Path(pack.path)
    assert source_playbook_path.exists()

    logger.info(f"Trying to upload pack from {source_pack_path}")
    Uploader(input=source_pack_path, insecure=True, zip=True, marketplace=MarketplaceVersions.MarketplaceV2).upload()

    # Preparing updated pack folder
    e2e_tests_utils.cli(f"mkdir {tmpdir}/Packs/{pack_name}_testsuite")

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmpdir}/Packs/{pack_name}_testsuite/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_testsuite",
        input=(playbook_name,),
        insecure=True,
        system=True,
        item_type='Playbook'
    ).download()
    dest_playbook_path = Path(
        f"{tmpdir}/Packs/{pack_name}_testsuite/Playbooks/{playbook_name}.yml"
    )
    assert not dest_playbook_path.exists()

    logger.info(
        f"Generating docs (creating a readme file) for playbook {source_playbook_path}"
    )
    generate_playbook_doc.generate_playbook_doc(input_path=str(source_playbook_path))
    assert Path(
        f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}_README.md"
    ).exists()
    logger.info(f"Formating playbook {source_playbook_path}")
    with ChangeCWD(pack.repo_path):
        format_manager(
            input=str(source_playbook_path),
            assume_answer=True,
        )
        logger.info(f"Validating playbook {source_playbook_path}")
        ValidateManager(file_path=str(source_playbook_path)).run_validation()

        logger.info(f"Uploading updated playbook {source_playbook_path}")
        Uploader(input=source_pack_path, insecure=True, zip=True, marketplace=MarketplaceVersions.MarketplaceV2).upload()


def test_e2e_demisto_sdk_flow_playbook_client(tmpdir, verify_ssl: bool = False):
    demisto_client = get_client_from_server_type(verify_ssl=verify_ssl)

    repo = Repo(tmpdir)

    unique_id = 456
    pack_name = "foo_" + str(unique_id)
    pack = repo.create_pack(name=pack_name)
    playbook_name = "pb_" + pack_name
    playbook: Playbook = pack.create_playbook(name=playbook_name)
    source_playbook_path = playbook.yml.path

    try:
        demisto_client.client.import_playbook(file=source_playbook_path)
    except ApiException as ae:
        if "already exists" in str(ae):
            logger.info(f"*** Playbook {playbook_name} already exists.")
        else:
            logger.info(f"*** Failed to create playbook {playbook_name}, reason: {ae}")
            assert False

    # Preparing updated pack folder
    e2e_tests_utils.cli(f"mkdir -p {tmpdir}/Packs/{pack_name}_client")

    Downloader(
        list_files=True,
        insecure=True,
    ).download()

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmpdir}/Packs/{pack_name}_client/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_client",
        input=(playbook_name,),
        insecure=True,
        system=True,
        item_type='Playbook'
    ).download()
    dest_playbook_path = Path(
        f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    assert not dest_playbook_path.exists()

    logger.info(
        f"Trying to download the CommonServerUserPowerShell file to {tmpdir}/Packs/{pack_name}_client/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_client",
        input=('CommonServerUserPowerShell',),
        insecure=True,
    ).download()

    logger.info(
        f"Generating docs (creating a readme file for the playbook {source_playbook_path}"
    )
    generate_playbook_doc.generate_playbook_doc(input_path=str(source_playbook_path))
    assert Path(
        f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}_README.md"
    ).exists()

    logger.info(f"Formating playbook {source_playbook_path}")

    with ChangeCWD(str(Path(source_playbook_path).parent)):
        format_manager(
            input=source_playbook_path,
            assume_answer=True,
        )
        logger.info(f"Validating playbook {source_playbook_path}")
        ValidateManager(file_path=source_playbook_path).run_validation()

        logger.info(f"Uploading updated playbook {source_playbook_path}")
        Uploader(input=source_playbook_path, insecure=True, zip=True, marketplace=MarketplaceVersions.MarketplaceV2).upload()

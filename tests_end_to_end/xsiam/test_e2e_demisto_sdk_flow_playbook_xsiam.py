from pathlib import Path

from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients import get_client_from_marketplace
from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.download.downloader import Downloader
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs import generate_playbook_doc
from demisto_sdk.commands.upload.uploader import Uploader
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from tests_end_to_end import e2e_tests_utils
from tests_end_to_end.e2e_tests_constansts import (
    DEFAULT_MODELING_RULES_SCHEMA_STRING,
    DEFAULT_MODELING_RULES_STRING,
    DEFAULT_TEST_DATA_STRING,
)
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


def test_e2e_demisto_sdk_flow_playbook_testsuite(tmpdir, verify_ssl: bool = False):
    """This flow checks:
    1. Creates a new playbook and uploads it demisto-sdk upload command.
    2. Downloads the playbook using demisto-sdk download command.
    3. Generates docs for the playbook using demisto-sdk generate-docs command.
    4. Formatting the playbook using the demisto-sdk format command.
    5. Validates the playbook using the demisto-sdk validate command.
    6. Uploads the playbook using the demisto-sdk upload command.
    """
    # Importing TestSuite classes from Demisto-SDK, as they are excluded when pip installing the SDK.
    git_path = Path(f"{tmpdir}/git")
    git_path.mkdir(exist_ok=True)

    e2e_tests_utils.git_clone_demisto_sdk(
        destination_folder=f"{tmpdir}/git/demisto-sdk",
        sdk_git_branch=DEMISTO_GIT_PRIMARY_BRANCH,
    )

    repo = Repo(tmpdir)
    pack, pack_name, source_pack_path = e2e_tests_utils.create_pack(repo)
    playbook, playbook_name, source_playbook_path = e2e_tests_utils.create_playbook(
        pack, pack_name
    )
    assert Path(source_playbook_path).exists()

    logger.info(f"Trying to upload pack from {source_pack_path}")
    Uploader(
        input=source_pack_path,
        insecure=True,
        zip=True,
        marketplace=MarketplaceVersions.MarketplaceV2,
    ).upload()

    # Preparing updated pack folder
    directory_path = Path(f"{tmpdir}/Packs/{pack_name}_testsuite")
    directory_path.mkdir(exist_ok=True, parents=True)

    logger.info(
        f"Trying to download the updated playbook from {playbook_name} to {tmpdir}/Packs/{pack_name}_testsuite/Playbooks"
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_testsuite",
        input=(playbook_name,),
        insecure=True,
        system=True,
        item_type="Playbook",
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
        OldValidateManager(file_path=str(source_playbook_path)).run_validation()

        logger.info(f"Uploading updated playbook {source_playbook_path}")
        Uploader(
            input=source_pack_path,
            insecure=True,
            zip=True,
            marketplace=MarketplaceVersions.MarketplaceV2,
        ).upload()


def test_e2e_demisto_sdk_flow_playbook_client(tmpdir, verify_ssl: bool = False):
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
    demisto_client = get_client_from_marketplace(
        MarketplaceVersions.MarketplaceV2, verify_ssl=verify_ssl
    )

    repo = Repo(tmpdir)
    pack, pack_name, source_pack_path = e2e_tests_utils.create_pack(repo)
    playbook, playbook_name, source_playbook_path = e2e_tests_utils.create_playbook(
        pack, pack_name
    )

    try:
        # uploads the playbook using API to emulate a playbook that has been created through the UI
        demisto_client.client.import_playbook(file=source_playbook_path)
    except ApiException as ae:
        if "already exists" in str(ae):
            logger.info(f"*** Playbook {playbook_name} already exists.")
        else:
            logger.info(f"*** Failed to create playbook {playbook_name}, reason: {ae}")
            raise

    # Preparing updated pack folder
    directory_path = Path(f"{tmpdir}/Packs/{pack_name}_client")
    directory_path.mkdir(exist_ok=True, parents=True)

    logger.info("Checking which files we can download from the machine.")
    Downloader(
        list_files=True,
        insecure=True,
    ).download()

    logger.info(
        f"Trying to download the updated playbook {playbook_name} to {tmpdir}/Packs/{pack_name}_client/Playbooks."
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_client",
        input=(playbook_name,),
        insecure=True,
        system=True,
        item_type="Playbook",
    ).download()
    dest_playbook_path = Path(
        f"{tmpdir}/Packs/{pack_name}_client/Playbooks/{playbook_name}.yml"
    )
    assert dest_playbook_path.exists()

    logger.info(
        f"Trying to download the CommonServerUserPowerShell file to {tmpdir}/Packs/{pack_name}_client/Playbooks."
    )
    Downloader(
        output=f"{tmpdir}/Packs/{pack_name}_client",
        input=("CommonServerUserPowerShell",),
        insecure=True,
    ).download()

    logger.info(
        f"Generating docs (creating a readme file for the playbook {source_playbook_path}."
    )
    generate_playbook_doc.generate_playbook_doc(input_path=str(source_playbook_path))
    assert Path(
        f"{tmpdir}/Packs/{pack_name}/Playbooks/{playbook_name}_README.md"
    ).exists()

    logger.info(f"Formating playbook {source_playbook_path}.")

    with ChangeCWD(str(Path(source_playbook_path).parent)):
        format_manager(
            input=str(source_playbook_path),
            assume_answer=True,
        )
        logger.info(f"Validating playbook {source_playbook_path}.")
        OldValidateManager(file_path=str(source_playbook_path)).run_validation()

        logger.info(f"Uploading updated playbook {source_playbook_path}.")
        Uploader(
            input=Path(source_playbook_path),
            insecure=True,
            zip=True,
            marketplace=MarketplaceVersions.MarketplaceV2,
        ).upload()

    try:
        demisto_client.delete_playbook(playbook_name, playbook_name)
    except ApiException as ae:
        logger.info(f"*** Failed to delete playbook {playbook_name}, reason: {ae}.")


def test_e2e_demisto_sdk_flow_modeling_rules_happy_path(
    tmpdir, verify_ssl: bool = False
):
    """This flow checks:
    1. Creates a new pack with modeling rules.
    2. Uploads the pack using the demisto-sdk Upload command
    2. Tests the modeling rules using the demisto-sdk modeling-rules test command
    3. deletes the pack from the machine
    """
    repo = Repo(tmpdir)
    pack, pack_name, source_pack_path = e2e_tests_utils.create_pack(repo)

    e2e_tests_utils.create_modeling_rules_folder(
        source_pack_path,
        f"{pack_name}ModelingRules",
        f"{pack_name}ModelingRules",
        DEFAULT_MODELING_RULES_STRING,
        DEFAULT_TEST_DATA_STRING,
        DEFAULT_MODELING_RULES_SCHEMA_STRING,
    )
    assert Path(
        f"{source_pack_path}/ModelingRules/{pack_name}ModelingRules/{pack_name}ModelingRules.yml"
    ).exists()

    demisto_client = get_client_from_marketplace(
        MarketplaceVersions.MarketplaceV2, verify_ssl=verify_ssl
    )

    # Uploads the pack
    Uploader(
        input=Path(source_pack_path),
        insecure=True,
        zip=True,
        marketplace=MarketplaceVersions.MarketplaceV2,
        destination_zip_dir=tmpdir,
    ).upload()

    # check if the pack was installed
    assert demisto_client.get_installed_pack(pack_name)

    # test the created modeling rules
    e2e_tests_utils.cli(
        f"demisto-sdk modeling-rules test {source_pack_path}/ModelingRules/{pack_name}ModelingRules"
    )

    # deletes the pack from the machine
    demisto_client.uninstall_marketplace_packs([pack_name])

import shutil
from pathlib import Path

import pytest

from demisto_sdk.commands.common.git_util import Repo as GitRepo
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


@pytest.fixture(autouse=True)
def setup(mocker):
    from demisto_sdk.scripts.validate_deleted_files import GitUtil

    mocker.patch.object(GitRepo, "remote", return_value="")
    mocker.patch.object(GitUtil, "fetch", return_value=None)


def test_validate_deleted_files_when_deleting_integration_folder(git_repo: Repo):
    """
    Given:
        - an integration folder which was deleted

    When:
        - running the validate-deleted-files script

    Then:
        - TODO
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    pack = git_repo.create_pack("Test")
    integration = pack.create_integration("Test")
    git_repo.git_util.commit_files("create pack and integration")
    git_repo.git_util.repo.git.checkout("-b", "delete_integration")

    shutil.rmtree(integration.path)
    git_repo.git_util.commit_files("delete integration")

    with ChangeCWD(git_repo.path):
        assert main() == 1


def test_validate_deleted_files_when_deleting_from_tests_folder(git_repo: Repo):
    """
    Given:
        - conf.json that was deleted

    When:
        - running the validate-deleted-files script

    Then:
        - TODO
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    git_repo.git_util.repo.git.checkout("-b", "delete_conf_json")
    Path.unlink(Path(git_repo.path) / "Tests/conf.json")
    git_repo.git_util.commit_files("delete conf.json")

    with ChangeCWD(git_repo.path):
        assert main() == 1


def test_validate_deleted_files_when_modifying_pack_metadata(git_repo: Repo):
    """
    Given:
        - pack metadata that was updated

    When:
        - running the validate-deleted-files script

    Then:
        - make sure that the script returns error code 0, which means it didn't identify any deleted files
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    git_repo.git_util.repo.git.checkout("-b", "modify_file")
    pack = git_repo.create_pack("Test")
    pack.pack_metadata.update({"support": "community"})
    git_repo.git_util.commit_files("update packmetadata.json")

    with ChangeCWD(git_repo.path):
        assert main() == 0


def test_validate_deleted_files_when_adding_integration(git_repo: Repo):
    """
    Given:
        - adding a new integration

    When:
        - running the validate-deleted-files script

    Then:
        - make sure that the script returns error code 0, which means it didn't identify any deleted files
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    pack = git_repo.create_pack("Test")
    git_repo.git_util.commit_files("create pack")
    git_repo.git_util.repo.git.checkout("-b", "add_integration")
    pack.create_integration("Test")
    git_repo.git_util.commit_files("add integration")

    with ChangeCWD(git_repo.path):
        assert main() == 0


def test_validate_deleted_files_when_renaming_file_name(git_repo: Repo):
    """
    Given:
        - conf.json file which was renamed

    When:
        - running the validate-deleted-files script

    Then:
        - make sure that the script returns error code 0, which means it didn't identify any deleted files
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    git_repo.git_util.repo.git.checkout("-b", "rename_conf_json_file")
    conf_json_path = Path(git_repo.path) / "Tests/conf.json"
    conf_json_path.rename(Path(git_repo.path) / "Tests/rename_conf_json_file.json")
    git_repo.git_util.commit_files("rename conf.json")

    with ChangeCWD(git_repo.path):
        assert main() == 0

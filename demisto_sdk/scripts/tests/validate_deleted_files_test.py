import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demisto_sdk.commands.common.constants import PACKS_DIR, TESTS_DIR
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.git_util import Repo as GitRepo
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


@pytest.fixture(autouse=True)
def setup(mocker):
    from demisto_sdk.scripts.validate_deleted_files import GitUtil

    mocker.patch.object(GitRepo, "remote", return_value="")
    mocker.patch.object(GitUtil, "fetch", return_value=None)


def test_validate_deleted_files_when_deleting_from_tests_folder(git_repo: Repo):
    """
    Given:
        - conf.json that was deleted

    When:
        - running the validate-get_forbidden_deleted_files-files function

    Then:
        - make sure the script finds all the forbidden files which is the conf.json
    """
    from demisto_sdk.scripts.validate_deleted_files import get_forbidden_deleted_files

    git_repo.git_util.repo.git.checkout("-b", "delete_conf_json")
    Path.unlink(Path(git_repo.path) / "Tests/conf.json")
    git_repo.git_util.commit_files("delete conf.json")

    expected_forbidden_conf_json_path = str(
        git_repo.git_util.path_from_git_root(Path(git_repo.path) / "Tests/conf.json")
    )

    with ChangeCWD(git_repo.path):
        assert get_forbidden_deleted_files({TESTS_DIR}) == [
            expected_forbidden_conf_json_path
        ]


def test_get_forbidden_deleted_files_deleting_script(git_repo: Repo):
    """
    Given:
        - a script folder which was deleted

    When:
        - running the get_forbidden_deleted_files function

    Then:
        - make sure the script finds all the forbidden files
          which were deleted which is all files within the script folder
    """
    from demisto_sdk.scripts.validate_deleted_files import get_forbidden_deleted_files

    pack = git_repo.create_pack("Test")
    script = pack.create_script("Test")

    expected_forbidden_deleted_files = [
        str(git_repo.git_util.path_from_git_root(file_path))
        for file_path in Path(script.path).rglob("*")
    ]

    git_repo.git_util.commit_files("create pack and script")
    git_repo.git_util.repo.git.checkout("-b", "delete_script")

    shutil.rmtree(script.path)
    git_repo.git_util.commit_files("delete script")

    with ChangeCWD(git_repo.path):
        assert sorted(get_forbidden_deleted_files({PACKS_DIR})) == sorted(
            expected_forbidden_deleted_files
        )


def test_get_forbidden_deleted_files_deleting_test_playbook(git_repo: Repo):
    """
    Given:
        - a test playbook which was deleted

    When:
        - running the get_forbidden_deleted_files function

    Then:
        - make sure the script does not find any forbidden deleted files as test-playbook can be deleted
    """
    from demisto_sdk.scripts.validate_deleted_files import get_forbidden_deleted_files

    pack = git_repo.create_pack("Test")
    test_playbook = pack.create_test_playbook("name")

    git_repo.git_util.commit_files("create pack and test playbook")
    git_repo.git_util.repo.git.checkout("-b", "delete_test_playbook")

    Path.unlink(Path(test_playbook.path))

    git_repo.git_util.commit_files("delete test-playbook")

    with ChangeCWD(git_repo.path):
        assert not get_forbidden_deleted_files({PACKS_DIR})


def test_get_forbidden_deleted_files_deleting_silent_playbook(git_repo: Repo):
    """
    Given:
        - a silent playbook which was deleted

    When:
        - running the get_forbidden_deleted_files function

    Then:
        - make sure the script does not find any forbidden deleted files as silent-playbook can be deleted
    """
    from demisto_sdk.scripts.validate_deleted_files import get_forbidden_deleted_files

    pack = git_repo.create_pack("Test")
    silent_playbook = pack.create_playbook("name")

    silent_playbook.yml.update({"issilent": "true"})

    git_repo.git_util.commit_files("create pack and silent playbook")
    git_repo.git_util.repo.git.checkout("-b", "delete_playbook")

    Path.unlink(Path(silent_playbook.path))

    git_repo.git_util.commit_files("delete silent-playbook")

    with ChangeCWD(git_repo.path):
        assert not get_forbidden_deleted_files({PACKS_DIR})


def test_get_forbidden_deleted_files_renaming_test_playbook(git_repo: Repo):
    """
    Given:
        - a test playbook which was renamed
        - Packs DIR that no files cannot be deleted from it

    When:
        - running the get_forbidden_deleted_files function

    Then:
        - make sure the script does not find any forbidden deleted files as test-playbook can be renamed
    """
    from demisto_sdk.scripts.validate_deleted_files import get_forbidden_deleted_files

    pack = git_repo.create_pack("Test")
    test_playbook = pack.create_test_playbook("name")

    git_repo.git_util.commit_files("create pack and test playbook")
    git_repo.git_util.repo.git.checkout("-b", "rename_test_playbook")

    test_playbook_path = Path(test_playbook.path)
    test_playbook_path.rename(test_playbook_path.parent / "test-playbook-1.yml")

    git_repo.git_util.commit_files("rename test-playbook")

    with ChangeCWD(git_repo.path):
        assert not get_forbidden_deleted_files({PACKS_DIR})


def test_validate_deleted_files_when_modifying_pack_metadata(git_repo: Repo):
    """
    Given:
        - pack metadata that was updated
        - Packs DIR that no files cannot be deleted from it

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

    runner = CliRunner()

    with ChangeCWD(git_repo.path):
        result = runner.invoke(
            main,
            [
                PACKS_DIR,
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert not result.exception


def test_validate_deleted_files_when_adding_integration(git_repo: Repo):
    """
    Given:
        - adding a new integration
        - Packs DIR that no files cannot be deleted from it

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

    runner = CliRunner()

    with ChangeCWD(git_repo.path):
        result = runner.invoke(
            main,
            [
                PACKS_DIR,
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert not result.exception


def test_validate_deleted_files_when_renaming_file_name(git_repo: Repo):
    """
    Given:
        - conf.json file which was renamed
        - Tests DIR that no files cannot be deleted from it

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

    runner = CliRunner()

    with ChangeCWD(git_repo.path):
        result = runner.invoke(
            main,
            [
                TESTS_DIR,
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert not result.exception


def test_validate_deleted_files_when_deleting_integration_folder(git_repo: Repo):
    """
    Given:
        - an integration folder which was deleted
        - Packs DIR that no files cannot be deleted from it

    When:
        - running the validate-deleted-files script

    Then:
        - make sure the script finds deleted files and fails with error code 1
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    pack = git_repo.create_pack("Test")
    integration = pack.create_integration("Test")
    git_repo.git_util.commit_files("create pack and integration")
    git_repo.git_util.repo.git.checkout("-b", "delete_integration")

    shutil.rmtree(integration.path)
    git_repo.git_util.commit_files("delete integration")

    runner = CliRunner()

    with ChangeCWD(git_repo.path):
        result = runner.invoke(
            main,
            [
                PACKS_DIR,
                TESTS_DIR,
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)


def test_validate_deleted_files_without_protected_dirs():
    """
    Given:
        - validate deleted files script

    When:
        - executing the validate-deleted-files script with no --protected-dirs argument

    Then:
        - make sure typer returns that the argument is missing
    """
    from demisto_sdk.scripts.validate_deleted_files import main

    runner = CliRunner()

    result = runner.invoke(
        main,
        catch_exceptions=False,
    )
    assert "Missing argument" in result.stdout


def test_is_file_allowed_to_be_deleted_logging_fallback_to_local(
    git_repo: Repo, mocker
):
    """
    Given:
        - A deleted file that cannot be read from remote branch
        - The file can be read from local branch

    When:
        - running is_file_allowed_to_be_deleted_by_file_type function

    Then:
        - Verify that debug messages are logged (not warnings)
        - Verify the file content is successfully read from local branch
    """
    from demisto_sdk.commands.common.constants import FileType
    from demisto_sdk.scripts.validate_deleted_files import (
        is_file_allowed_to_be_deleted_by_file_type,
    )

    # Mock File.read_from_git_path to fail on first call (remote) and succeed on second (local)
    mock_read_from_git = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.File.read_from_git_path"
    )
    mock_read_from_git.side_effect = [
        FileReadError(
            "Remote read failed", Exception("Mock error")
        ),  # First call fails (remote)
        {"name": "TestPlaybook"},  # Second call succeeds (local)
    ]

    # Mock find_type to return a file type
    mock_find_type = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.find_type"
    )
    mock_find_type.return_value = FileType.PLAYBOOK

    mock_logger_debug = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.debug"
    )
    mock_logger_warning = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.warning"
    )

    file_path = Path("Packs/Test/TestPlaybooks/TestPlaybook.yml")

    with ChangeCWD(git_repo.path):
        result = is_file_allowed_to_be_deleted_by_file_type(file_path)

    # Verify debug was called (not warning) for the fallback messages
    assert mock_logger_debug.call_count == 2
    assert "Could not retrieve" in mock_logger_debug.call_args_list[0][0][0]
    assert "Retrieving" in mock_logger_debug.call_args_list[1][0][0]

    # Verify warning was NOT called for the first fallback
    assert mock_logger_warning.call_count == 0

    # Verify the function succeeded (playbook is not in FileType_ALLOWED_TO_DELETE)
    assert result is False


def test_is_file_allowed_to_be_deleted_logging_fallback_to_github(
    git_repo: Repo, mocker
):
    """
    Given:
        - A deleted file that cannot be read from remote or local branch
        - The file can be read from GitHub API

    When:
        - running is_file_allowed_to_be_deleted_by_file_type function

    Then:
        - Verify that debug messages are logged for first fallback
        - Verify that warning message is logged for second fallback to GitHub
        - Verify the file content is successfully read from GitHub API
    """
    from demisto_sdk.commands.common.constants import FileType
    from demisto_sdk.scripts.validate_deleted_files import (
        is_file_allowed_to_be_deleted_by_file_type,
    )

    # Mock File.read_from_git_path to fail on both calls
    mock_read_from_git = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.File.read_from_git_path"
    )
    mock_read_from_git.side_effect = [
        FileReadError(
            "Remote read failed", Exception("Mock error")
        ),  # First call fails (remote)
        FileReadError(
            "Local read failed", Exception("Mock error")
        ),  # Second call fails (local)
    ]

    # Mock File.read_from_github_api to succeed
    mock_read_from_github = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.File.read_from_github_api"
    )
    mock_read_from_github.return_value = {"name": "TestPlaybook"}

    # Mock find_type to return a file type
    mock_find_type = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.find_type"
    )
    mock_find_type.return_value = FileType.PLAYBOOK

    mock_logger_debug = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.debug"
    )
    mock_logger_warning = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.warning"
    )

    file_path = Path("Packs/Test/TestPlaybooks/TestPlaybook.yml")

    with ChangeCWD(git_repo.path):
        result = is_file_allowed_to_be_deleted_by_file_type(file_path)

    # Verify debug was called for the first fallback
    assert mock_logger_debug.call_count == 2
    assert "Could not retrieve" in mock_logger_debug.call_args_list[0][0][0]
    assert "Retrieving" in mock_logger_debug.call_args_list[1][0][0]

    # Verify warning was called for the second fallback to GitHub
    assert mock_logger_warning.call_count == 1
    assert "Could not read file" in mock_logger_warning.call_args_list[0][0][0]
    assert "trying to read" in mock_logger_warning.call_args_list[0][0][0]
    assert "from github" in mock_logger_warning.call_args_list[0][0][0]

    # Verify the function succeeded (playbook is not in FileType_ALLOWED_TO_DELETE)
    assert result is False


def test_is_file_allowed_to_be_deleted_no_fallback_needed(git_repo: Repo, mocker):
    """
    Given:
        - A deleted file that can be read from remote branch on first attempt

    When:
        - running is_file_allowed_to_be_deleted_by_file_type function

    Then:
        - Verify that no debug or warning messages are logged
        - Verify the file content is successfully read from remote branch
    """
    from demisto_sdk.commands.common.constants import FileType
    from demisto_sdk.scripts.validate_deleted_files import (
        is_file_allowed_to_be_deleted_by_file_type,
    )

    # Mock File.read_from_git_path to succeed on first call
    mock_read_from_git = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.File.read_from_git_path"
    )
    mock_read_from_git.return_value = {"name": "TestPlaybook"}

    # Mock find_type to return a file type
    mock_find_type = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.find_type"
    )
    mock_find_type.return_value = FileType.PLAYBOOK

    mock_logger_debug = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.debug"
    )
    mock_logger_warning = mocker.patch(
        "demisto_sdk.scripts.validate_deleted_files.logger.warning"
    )

    file_path = Path("Packs/Test/TestPlaybooks/TestPlaybook.yml")

    with ChangeCWD(git_repo.path):
        result = is_file_allowed_to_be_deleted_by_file_type(file_path)

    # Verify no fallback logging occurred
    assert mock_logger_debug.call_count == 0
    assert mock_logger_warning.call_count == 0

    # Verify the function succeeded (playbook is not in FileType_ALLOWED_TO_DELETE)
    assert result is False

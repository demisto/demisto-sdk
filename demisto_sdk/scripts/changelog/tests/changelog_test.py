from pathlib import Path

import pytest

from demisto_sdk.commands.common.files import YmlFile
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.scripts.changelog import changelog
from demisto_sdk.scripts.changelog.changelog import (
    Changelog,
    clear_changelogs_folder,
    get_new_log_entries,
    is_log_yml_exist,
    is_release,
    read_log_files,
)
from demisto_sdk.scripts.changelog.changelog_obj import LogType
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()

DUMMY_PR_NUMBER = "12345"
DUMMY_PR_NAME = "demisto-sdk release 2.2.2"

LOG_FILE_1 = {
    "changes": [{"description": "fixed an issue where test", "type": "fix"}],
    "pr_number": DUMMY_PR_NUMBER,
}
LOG_FILE_2 = {
    "changes": [
        {"description": "added a feature that test", "type": "feature"},
        {"description": "breaking changes: test", "type": "breaking"},
    ],
    "pr_number": "43524",
}
LOG_FILE_3 = {
    "changes": [
        {"description": "added a feature that test", "type": "fix"},
        {"description": "breaking changes: test", "type": "internal"},
    ],
    "pr_number": "43524",
}


@pytest.fixture
def changelog_mock() -> Changelog:
    return Changelog(pr_name="test", pr_number=DUMMY_PR_NUMBER)


@pytest.fixture
def changelog_folder_mock(tmpdir, mocker) -> Path:
    folder_path = Path(tmpdir / ".changelog")
    folder_path.mkdir()
    mocker.patch.object(changelog, "CHANGELOG_FOLDER", folder_path)
    return folder_path


@pytest.mark.parametrize(
    "pr_name, expected_result",
    [
        ("", False),
        ("test", False),
        ("demisto-sdk release 1.10.2", True),
        ("1.2.3", False),
    ],
)
def test_is_release(pr_name: str, expected_result: bool):
    """
    Given:
        - Changelog obj with some different `pr_name`
    When:
        - run the is_release method
    Then:
        - Ensure return True only if pr_name is in vX.X.X format
    """
    assert is_release(pr_name) == expected_result


@pytest.mark.parametrize("pr_name", ("", DUMMY_PR_NUMBER))
def test_is_log_yml_exist(changelog_folder_mock: Path, pr_name: str):
    """
    Given:
        - Changelog obj and a temporary path with a .changelog folder
    When:
        - run the is_log_yml_exist method
    Then:
        - Ensure return True only if there is a yml file
          with the same name as pr_number in the .changelog folder
    """
    if pr_name:
        (changelog_folder_mock / f"{pr_name}.yml").write_text("test: test")
    assert is_log_yml_exist(pr_name) is (pr_name == DUMMY_PR_NUMBER)


def test_get_all_logs(changelog_folder_mock: Path):
    """
    Given:
        - Tow log files
    When:
        - run `get_all_logs` function
    Then:
        - Ensure all log files are return
        - Ensure that if there are two entries in the log file
          it is returned as two entries within an `LogFileObject` object
    """
    with (changelog_folder_mock / "12345.yml").open("w") as f:
        yaml.dump(LOG_FILE_1, f)
    with (changelog_folder_mock / "43524.yml").open("w") as f:
        yaml.dump(LOG_FILE_2, f)
    log_files = read_log_files()
    assert len(log_files) == 2
    assert len(log_files[0].changes) + len(log_files[1].changes) == 3


@pytest.mark.parametrize("pr_name", [DUMMY_PR_NAME, ""])
def test_validate(mocker, changelog_mock: Changelog, pr_name: str):
    """
    Given:
        - The pr name
    When:
        - run `validate` method
    Then:
        - Ensure that the function classifies the validation according to the PR name
          (for a PR name that corresponds to the release, the `_validate_release` function
          will be activated, otherwise the `_validate_branch` function will be activated)
    """
    mock_validate_branch = mocker.patch.object(changelog, "_validate_branch")
    changelog_mock.pr_name = pr_name
    changelog_mock.validate()

    assert mock_validate_branch.call_count == int(not bool(pr_name))


def test_clear_changelogs_folder(changelog_folder_mock: Path):
    """
    Given:
        - A .changelog folder with a file
    When:
        - run `clear_changelogs_folder` function
    Then:
        - Ensure the .changelog folder is empty
    """
    with (changelog_folder_mock / "12345.yml").open("w") as f:
        f.write("test: test")
    with (changelog_folder_mock / "README.md").open("w") as f:
        f.write("## Changelog folder")
    clear_changelogs_folder()
    assert len(list(changelog_folder_mock.iterdir())) == 1


def test_get_new_log_entries(changelog_folder_mock: Path):
    """
    Given:
        - list of LogFileObject with all types
    When:
        - run `get_new_log_entries` function
    Then:
        - Ensure a dictionary with all `LogType`s is returned
    """
    for i, log_file in enumerate((LOG_FILE_1, LOG_FILE_2, LOG_FILE_3)):
        with (changelog_folder_mock / f"{i}.yml").open("w") as f:
            yaml.dump(log_file, f)
    logs = read_log_files()
    results = get_new_log_entries(logs)
    for type_ in (log_type for log_type in LogType):
        assert type_ in results


def test_comment_newly_added_changelog(
    mocker, git_repo: Repo, changelog_mock: Changelog
):
    """
    Given:
        - repo with newly created change-log
    When:
        - run `Changelog.comment` method
    Then:
        - Ensure that the log is commented out to the PR.
    """
    from demisto_sdk.commands.common.logger import logger

    changelog_folder = Path(f"{git_repo.path}/.changelog")
    changelog_folder.mkdir()
    mocker.patch.object(changelog, "CHANGELOG_FOLDER", changelog_folder)

    mocker.patch.object(changelog, "GIT_UTIL", git_repo.git_util)
    github_mocker = mocker.patch("demisto_sdk.scripts.changelog.changelog.Github")
    info_logger_mocker = mocker.patch.object(logger, "info")

    changelog_path = changelog_folder / f"{DUMMY_PR_NUMBER}.yml"
    YmlFile.write(data=LOG_FILE_1, output_path=changelog_path)

    git_util = git_repo.git_util
    git_util.commit_files("Commit changelog file")

    current_commit = git_util.get_current_commit_hash()
    with ChangeCWD(git_repo.path):
        Changelog(pr_number=DUMMY_PR_NUMBER).comment(
            current_commit, github_token="1234"
        )
    assert github_mocker.called
    assert (
        info_logger_mocker.call_args_list[1].args[0]
        == "Successfully commented on PR 12345 the changelog"
    )


def test_comment_modified_changelog(mocker, git_repo: Repo, changelog_mock: Changelog):
    """
    Given:
        - repo with modified change-log
    When:
        - run `Changelog.comment` method
    Then:
        - Ensure that the log is commented out to the PR.
    """
    from demisto_sdk.commands.common.logger import logger

    changelog_folder = Path(f"{git_repo.path}/.changelog")
    changelog_folder.mkdir()
    mocker.patch.object(changelog, "CHANGELOG_FOLDER", changelog_folder)

    mocker.patch.object(changelog, "GIT_UTIL", git_repo.git_util)
    github_mocker = mocker.patch("demisto_sdk.scripts.changelog.changelog.Github")
    info_logger_mocker = mocker.patch.object(logger, "info")

    changelog_path = changelog_folder / f"{DUMMY_PR_NUMBER}.yml"
    YmlFile.write(data=LOG_FILE_1, output_path=changelog_path)

    git_util = git_repo.git_util
    git_util.commit_files("Commit changelog file")

    # modify the changelog
    YmlFile.write(data=LOG_FILE_2, output_path=changelog_path)
    git_util.commit_files("Commit changelog file")

    current_commit = git_util.get_current_commit_hash()
    with ChangeCWD(git_repo.path):
        Changelog(pr_number=DUMMY_PR_NUMBER).comment(
            current_commit, github_token="1234"
        )
    assert github_mocker.called
    assert (
        info_logger_mocker.call_args_list[1].args[0]
        == "Successfully commented on PR 12345 the changelog"
    )


def test_comment_unmodified_changelog(
    mocker, git_repo: Repo, changelog_mock: Changelog
):
    """
    Given:
        - repo with change-log that was not modified between the current and last commit
    When:
        - run `Changelog.comment` method
    Then:
        - Ensure that the log is NOT commented out to the PR.
    """
    from demisto_sdk.commands.common.logger import logger

    changelog_folder = Path(f"{git_repo.path}/.changelog")
    changelog_folder.mkdir()
    mocker.patch.object(changelog, "CHANGELOG_FOLDER", changelog_folder)

    mocker.patch.object(changelog, "GIT_UTIL", git_repo.git_util)
    github_mocker = mocker.patch("demisto_sdk.scripts.changelog.changelog.Github")
    info_logger_mocker = mocker.patch.object(logger, "info")

    changelog_path = changelog_folder / f"{DUMMY_PR_NUMBER}.yml"
    YmlFile.write(data=LOG_FILE_1, output_path=changelog_path)

    git_util = git_repo.git_util
    git_util.commit_files("Commit changelog file")

    # modify the changelog
    YmlFile.write(data="text", output_path=Path(f"{git_repo.path}/test.txt"))
    git_util.commit_files("Commit text file")

    current_commit = git_util.get_current_commit_hash()
    with ChangeCWD(git_repo.path):
        Changelog(pr_number=DUMMY_PR_NUMBER).comment(
            current_commit, github_token="1234"
        )
    assert not github_mocker.called
    assert (
        info_logger_mocker.call_args_list[0].args[0]
        == f"{changelog_path} has not been changed, not commenting on PR 12345"
    )

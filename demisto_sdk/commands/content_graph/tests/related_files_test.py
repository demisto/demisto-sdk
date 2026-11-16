from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.parsers import related_files
from demisto_sdk.commands.content_graph.parsers.related_files import (
    ReadmeRelatedFile,
    RNRelatedFile,
)

CURRENT_BRANCH = "contrib/user/feature"
LOCAL_README = "local staged README with all the commands"
GIT_README = "README of the branch tip without the new commands"


@pytest.fixture
def integration_dir(tmp_path: Path) -> Path:
    integration_path = tmp_path / "Integrations" / "MyInt"
    integration_path.mkdir(parents=True)
    (integration_path / "MyInt.yml").write_text("name: MyInt")
    (integration_path / "README.md").write_text(LOCAL_README)
    return integration_path


@pytest.fixture
def mock_git(monkeypatch) -> MagicMock:
    git_util = MagicMock()
    git_util.get_current_git_branch_or_hash.return_value = CURRENT_BRANCH
    git_util.is_file_exist_in_commit_or_branch.return_value = False
    monkeypatch.setattr(
        related_files.GitUtil, "from_content_path", lambda *_, **__: git_util
    )
    return git_util


@pytest.fixture
def read_from_git(monkeypatch) -> MagicMock:
    mock = MagicMock(return_value=GIT_README)
    monkeypatch.setattr(related_files.TextFile, "read_from_git_path", mock)
    return mock


def test_readme_is_read_from_local_tree_when_git_sha_is_current_branch(
    mock_git, read_from_git, integration_dir: Path
):
    """
    Given:
        - An integration whose README is staged locally (contribution flow).
        - A git_sha equal to the currently checked out branch, whose
          remote README is stale.
    When:
        - Reading the README content.
    Then:
        - The local README is used and nothing is read from git.
    """
    readme = ReadmeRelatedFile(
        integration_dir / "MyInt.yml",
        is_pack_readme=False,
        git_sha=CURRENT_BRANCH,
    )

    assert readme.exist
    assert readme.file_content == LOCAL_README
    read_from_git.assert_not_called()


def test_readme_is_read_from_git_when_git_sha_is_not_current_branch(
    mock_git, read_from_git, integration_dir: Path
):
    """
    Given:
        - A git_sha that is not the currently checked out branch.
    When:
        - Reading the README content.
    Then:
        - The content is read from git, as before.
    """
    mock_git.is_file_exist_in_commit_or_branch.return_value = True

    readme = ReadmeRelatedFile(
        integration_dir / "MyInt.yml",
        is_pack_readme=False,
        git_sha="origin/master",
    )

    assert readme.file_content == GIT_README
    read_from_git.assert_called_once()


def test_file_deleted_locally_is_missing_for_current_branch(
    mock_git, read_from_git, integration_dir: Path
):
    """
    Given:
        - A README deleted by the contribution (removed from the working tree)
          that still exists on the remote branch.
        - A git_sha equal to the currently checked out branch.
    When:
        - Resolving the README related file.
    Then:
        - The file is reported as missing, and git is not consulted.
    """
    (integration_dir / "README.md").unlink()
    mock_git.is_file_exist_in_commit_or_branch.return_value = True

    readme = ReadmeRelatedFile(
        integration_dir / "MyInt.yml",
        is_pack_readme=False,
        git_sha=CURRENT_BRANCH,
    )

    assert not readme.exist
    mock_git.is_file_exist_in_commit_or_branch.assert_not_called()


def test_release_notes_are_listed_from_local_tree_for_current_branch(
    mock_git, tmp_path: Path
):
    """
    Given:
        - A pack with a release note staged locally.
        - A git_sha equal to the currently checked out branch.
    When:
        - Listing all release notes.
    Then:
        - The release notes are listed from the local tree, not from git.
    """
    pack_path = tmp_path / "Packs" / "MyPack"
    rn_dir = pack_path / "ReleaseNotes"
    rn_dir.mkdir(parents=True)
    (rn_dir / "1_0_1.md").write_text("notes")

    rn = RNRelatedFile(pack_path, latest_rn="1.0.1", git_sha=CURRENT_BRANCH)

    assert rn.exist
    assert [Path(p).name for p in rn.all_rns] == ["1_0_1.md"]
    mock_git.list_files_in_dir.assert_not_called()

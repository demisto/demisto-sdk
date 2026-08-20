import stat
from datetime import datetime
from pathlib import Path

import pytest
from git import Blob

from demisto_sdk.commands.common.constants import ISO_TIMESTAMP_FORMAT
from demisto_sdk.commands.common.git_util import GitUtil
from TestSuite.repo import Repo

# ``TestSuite.repo.Repo.create_pack`` replaces ``GitUtil.get_file_creation_date``
# with a ``MagicMock`` on the class and never restores it, so a test that ran
# earlier can leak the mock into this module. Keep a reference to the real
# implementation, captured on import (before any test could patch it).
_REAL_GET_FILE_CREATION_DATE = GitUtil.get_file_creation_date


@pytest.fixture
def unmocked_get_file_creation_date(monkeypatch):
    """Ensure the real ``get_file_creation_date`` is used, not a leaked mock."""
    monkeypatch.setattr(GitUtil, "get_file_creation_date", _REAL_GET_FILE_CREATION_DATE)


def test_find_primary_branch():
    """
    Given
        - A Git repo

    When
        - Searching for the primary branch

    Then
        - Ensure ithe returned value is either 'main', 'master', or None
    """
    from demisto_sdk.commands.common.git_util import GitUtil

    assert not GitUtil.find_primary_branch(None)

    class Object:
        pass

    empty_repo = Object()
    assert not GitUtil.find_primary_branch(empty_repo)

    repo_with_empty_remotes = Object()
    repo_with_empty_remotes.remotes = []
    assert not GitUtil.find_primary_branch(repo_with_empty_remotes)

    repo_with_empty_remotes_refs = Object()
    repo_with_empty_remotes_refs.remotes = []
    empty_refs = Object()
    repo_with_empty_remotes_refs.remotes.append(empty_refs)
    assert not GitUtil.find_primary_branch(repo_with_empty_remotes_refs)

    repo_with_remotes_refs_main = Object()
    repo_with_remotes_refs_main.remotes = []
    refs_main = Object()
    refs_main.refs = ["a", "origin/main", "c"]
    repo_with_remotes_refs_main.remotes.append(refs_main)
    assert GitUtil.find_primary_branch(repo_with_remotes_refs_main) == "main"

    repo_with_remotes_refs_master = Object()
    repo_with_remotes_refs_master.remotes = []
    refs_master = Object()
    refs_master.refs = ["a", "origin/master", "c"]
    repo_with_remotes_refs_master.remotes.append(refs_master)
    assert GitUtil.find_primary_branch(repo_with_remotes_refs_master) == "master"

    repo_with_remotes_refs_other = Object()
    repo_with_remotes_refs_other.remotes = []
    refs_other = Object()
    refs_other.refs = ["a", "b"]
    repo_with_remotes_refs_other.remotes.append(refs_other)
    assert not GitUtil.find_primary_branch(repo_with_remotes_refs_other)


class TestHasFilePermissionsChanged:
    file = Path("testfile")

    def test_new_file(self, git_repo: Repo):
        """
        Check if permissions haven't changed for a newly
        and committed file.

        Given:
        - A git repo.

        When:
        - A new file is created, added and committed.

        Then:
        - The file permissions have not changed.
        """

        git_repo.make_file(self.file, "lorem ipsum")
        git_repo.git_util.commit_files(f"added {self.file}", self.file)

        (
            actual_has_changed,
            actual_old_file_permission,
            actual_new_file_permission,
        ) = git_repo.git_util.has_file_permissions_changed(self.file)

        assert not actual_has_changed
        assert not actual_old_file_permission
        assert not actual_new_file_permission

    def test_file_set_executable(self, git_repo: Repo):
        """
        Simulate a scenario where a file was set to executable.

        Given:
        - A git repo.

        When:
        - A new file is created, added and committed.
        - The file is then made executable.

        Then:
        - The file permissions have not changed.

        """

        git_repo.make_file(self.file, "lorem ipsum")
        git_repo.git_util.commit_files(f"added {self.file}", self.file)

        file_path = Path(git_repo.working_dir(), self.file)

        file_path.chmod(file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.stage_file(file_path)

        (
            actual_has_changed,
            actual_old_file_permission,
            actual_new_file_permission,
        ) = git_repo.git_util.has_file_permissions_changed(self.file)

        assert actual_has_changed
        assert actual_old_file_permission == oct(Blob.file_mode)[2:]
        assert actual_new_file_permission == oct(Blob.executable_mode)[2:]


def test_git_util_with_repo():
    """
    Given
        - A Git repo.

    When
        - Creating GitUtil object with git.Repo object.

    Then
        - Ensure the GitUtil repo path equals to the repo path.
    """
    from demisto_sdk.commands.common.git_util import GitUtil

    repo = GitUtil.REPO_CLS()

    git_util = GitUtil(repo)
    assert git_util.repo is not None
    assert git_util.repo.working_dir == repo.working_dir


def test_get_file_creation_date(git_repo: Repo, unmocked_get_file_creation_date):
    """
    Given:
    - A git repo and a file in it.

    When:
    - Retrieving the creation time of the given file.

    Then:
    - The creation time of the file is returned.
    """
    file = Path("pack_metadata.json")
    git_repo.make_file(str(file), "{}")
    git_repo.git_util.commit_files(f"added {file}", str(file))

    file_creation_date = git_repo.git_util.get_file_creation_date(file)

    datetime.strptime(file_creation_date, ISO_TIMESTAMP_FORMAT)  # raises if invalid


# Distinctive content, so git's rename detection won't match other files in the repo.
METADATA_CONTENT = '{"name": "MyPack", "support": "xsoar", "currentVersion": "1.0.0"}'

# An explicit identity, as the git CLI fails to commit when one isn't configured
# (for example, on a CI runner).
GIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "demisto-sdk-test",
    "GIT_AUTHOR_EMAIL": "demisto-sdk-test@example.com",
    "GIT_COMMITTER_NAME": "demisto-sdk-test",
    "GIT_COMMITTER_EMAIL": "demisto-sdk-test@example.com",
}


def _commit_env(date: str) -> dict:
    """The environment to commit with, using a fixed identity and commit date."""
    return {**GIT_IDENTITY_ENV, "GIT_COMMITTER_DATE": date}


def _commit_file(git_repo: Repo, file: Path, content: str, message: str, date: str):
    """Create/update `file` with `content` and commit it with a fixed author/commit date."""
    git_repo.make_file(str(file), content)
    git_repo.git_util.repo.git.add(str(file))
    git_repo.git_util.repo.git.commit(
        "-m", message, "--date", date, env=_commit_env(date)
    )


def test_get_file_creation_date_uses_add_commit_not_latest(
    git_repo: Repo, unmocked_get_file_creation_date
):
    """
    Given:
    - A file that was added in one commit and modified in a later commit.

    When:
    - Retrieving the creation time of the given file.

    Then:
    - The date of the commit that added the file is returned, not the latest one.
    """
    file = Path("pack_metadata.json")
    _commit_file(
        git_repo, file, METADATA_CONTENT, f"added {file}", "2020-11-04T10:00:00+00:00"
    )
    _commit_file(
        git_repo,
        file,
        METADATA_CONTENT.replace("1.0.0", "1.0.1"),
        f"modified {file}",
        "2025-03-29T10:00:00+00:00",
    )

    assert git_repo.git_util.get_file_creation_date(file) == "2020-11-04T10:00:00Z"


def test_get_file_creation_date_follows_renames(
    git_repo: Repo, unmocked_get_file_creation_date
):
    """
    Given:
    - A file that was added and later renamed.

    When:
    - Retrieving the creation time of the file using its new path.

    Then:
    - The date of the commit that originally added the file is returned.
    """
    original = Path("pack_metadata.json")
    renamed = Path("renamed_pack_metadata.json")
    _commit_file(
        git_repo,
        original,
        METADATA_CONTENT,
        f"added {original}",
        "2020-11-04T10:00:00+00:00",
    )

    git_repo.git_util.repo.git.mv(str(original), str(renamed))
    git_repo.git_util.repo.git.commit(
        "-m",
        f"renamed {original}",
        "--date",
        "2025-03-29T10:00:00+00:00",
        env=_commit_env("2025-03-29T10:00:00+00:00"),
    )

    assert git_repo.git_util.get_file_creation_date(renamed) == "2020-11-04T10:00:00Z"


def test_get_file_creation_date_shallow_clone_warns(
    git_repo: Repo, mocker, caplog, unmocked_get_file_creation_date
):
    """
    Given:
    - A shallow cloned repo.

    When:
    - Retrieving the creation time of a file in it.

    Then:
    - A warning is logged and the derived date is still returned.
    """
    file = Path("pack_metadata.json")
    _commit_file(
        git_repo, file, METADATA_CONTENT, f"added {file}", "2020-11-04T10:00:00+00:00"
    )
    # 'rev_parse' is resolved dynamically by GitPython, so it's patched on the class.
    mocker.patch.object(
        type(git_repo.git_util.repo.git),
        "rev_parse",
        create=True,
        return_value="true",
    )

    caplog.set_level("WARNING")
    file_creation_date = git_repo.git_util.get_file_creation_date(file)

    assert file_creation_date == "2020-11-04T10:00:00Z"
    assert "shallow clone" in caplog.text


@pytest.mark.parametrize(
    "iso_date, expected",
    [
        ("2020-11-04T10:00:00Z", "2020-11-04T10:00:00Z"),  # newer git versions
        ("2020-11-04T10:00:00+00:00", "2020-11-04T10:00:00Z"),
        ("2020-11-04T12:00:00+02:00", "2020-11-04T10:00:00Z"),
    ],
)
def test_normalize_iso_date(iso_date: str, expected: str):
    """
    Given:
    - A strict-ISO git date, with either a 'Z' or a numeric UTC offset.

    When:
    - Normalizing it.

    Then:
    - The date is converted to UTC, in the expected format.
    """
    assert GitUtil._normalize_iso_date(iso_date) == expected


def test_get_file_creation_date_no_history_returns_now(
    git_repo: Repo, unmocked_get_file_creation_date
):
    """
    Given:
    - A file path that has no git history.

    When:
    - Retrieving the creation time of the given file.

    Then:
    - The current time is returned, in the expected format.
    """
    file_creation_date = git_repo.git_util.get_file_creation_date(
        Path("no_such_file.json")
    )

    datetime.strptime(file_creation_date, ISO_TIMESTAMP_FORMAT)  # raises if invalid

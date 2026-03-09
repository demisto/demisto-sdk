import stat
from datetime import datetime
from pathlib import Path

import pytest
from git import Blob

from demisto_sdk.commands.common.constants import ISO_TIMESTAMP_FORMAT
from demisto_sdk.commands.common.git_util import CommitOrBranchNotFoundError, GitUtil
from TestSuite.repo import Repo


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


def test_get_file_creation_date(git_repo: Repo):
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


class TestGetAllChangedFiles:
    """Tests for _get_all_changed_files method."""

    def test_get_all_changed_files_raises_on_invalid_commit_sha(self):
        """
        Given:
            - A prev_ver that is a SHA1 hash not present in the local git history
              (simulating a CI shallow clone where the imported graph's commit is unavailable).

        When:
            - Calling _get_all_changed_files with the invalid SHA.

        Then:
            - A CommitOrBranchNotFoundError is raised before attempting the git diff,
              preventing the cryptic 'fatal: bad object' git error.
        """
        git_util = GitUtil()

        # A SHA1 hash that doesn't exist in the local repo history,
        # simulating the commit from an imported graph in a CI shallow clone
        nonexistent_sha = "9e303977aad72c773a365f087970c0edfafebaf0"

        with pytest.raises(CommitOrBranchNotFoundError):
            git_util._get_all_changed_files(prev_ver=nonexistent_sha)

    def test_get_all_changed_files_works_with_valid_commit(self, git_repo: Repo):
        """
        Given:
            - A valid commit SHA from the current repo.

        When:
            - Calling _get_all_changed_files with the valid SHA.

        Then:
            - No exception is raised and a set of paths is returned.
        """
        # Create a file and commit it to have a valid commit
        git_repo.make_file("test_file.txt", "content")
        git_repo.git_util.commit_files("add test file", "test_file.txt")
        valid_sha = git_repo.git_util.get_current_commit_hash()

        # This should not raise
        result = git_repo.git_util._get_all_changed_files(prev_ver=valid_sha)
        assert isinstance(result, set)

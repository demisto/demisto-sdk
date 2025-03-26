import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence, Set, Tuple, Union

import click
import gitdb
from git import (
    InvalidGitRepositoryError,
    Repo,  # noqa: TID251: required to create GitUtil
)
from git.diff import Lit_change_type
from git.exc import GitError
from git.objects import Blob, Commit
from git.remote import Remote

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    PACKS_FOLDER,
)
from demisto_sdk.commands.common.logger import logger


class CommitOrBranchNotFoundError(GitError):
    def __init__(
        self,
        commit_or_branch: str,
        from_remote: bool = True,
    ):
        if from_remote and DEMISTO_GIT_UPSTREAM not in commit_or_branch:
            commit_or_branch = f"{DEMISTO_GIT_UPSTREAM}/{commit_or_branch}"
        super().__init__(f"Commit/Branch {commit_or_branch} could not be found")


class GitFileNotFoundError(FileNotFoundError):
    def __init__(self, commit_or_branch: str, path: str, from_remote: bool = True):
        if from_remote:
            commit_or_branch = f"{DEMISTO_GIT_UPSTREAM}/{commit_or_branch}"
        super().__init__(
            f"file {path} could not be found in commit/branch {commit_or_branch}"
        )


class GitUtil:
    # in order to use Repo class/static methods
    REPO_CLS = Repo

    def __init__(
        self,
        path: Optional[Union[str, Path, Repo]] = None,
        search_parent_directories: bool = True,
    ):
        if isinstance(path, str):
            repo_path = Path(path)
        elif isinstance(path, self.REPO_CLS):
            repo_path = path.working_dir  # type: ignore
        else:
            repo_path = path or Path.cwd()

        try:
            self.repo = Repo(
                repo_path, search_parent_directories=search_parent_directories
            )
        except InvalidGitRepositoryError:
            raise InvalidGitRepositoryError(
                f"Unable to find Repository from current {repo_path.absolute()} - aborting"
            )

    @classmethod
    def from_content_path(cls, path: Optional[Path] = None) -> "GitUtil":
        if content_path := os.getenv("DEMISTO_SDK_CONTENT_PATH"):
            return cls(Path(content_path), search_parent_directories=False)
        return cls(path)

    def path_from_git_root(self, path: Union[Path, str]) -> Path:
        """
        Given an absolute path, return the path to the file/directory from the
        repo/git root. For example, `/<some_local_path>/Packs/HelloWorld/pack_metadata.json`
        will return `Packs/HelloWorld/pack_metadata.json`.

        Arguments:
        - `path` (``Path|str``): The path to the file/folder.

        Returns:
        - `Path` relative to the working directory.
        """

        try:
            return Path(path).relative_to(Path(self.repo.working_dir))
        except ValueError:
            return Path(os.path.relpath(str(path), self.git_path()))

    def get_commit(self, commit_or_branch: str, from_remote: bool = True) -> Commit:
        """
        Retrieves a commit object from a commit-hash or a branch.

        Args:
            commit_or_branch: commit sha or branch name
            from_remote: whether to retrieve the branch from a remote ref / whether to fetch commit which does not
                exist locally.

        Returns:

        """
        if from_remote:
            if self.is_valid_remote_branch(commit_or_branch):
                branch = commit_or_branch

                if DEMISTO_GIT_UPSTREAM not in branch:
                    branch = f"{DEMISTO_GIT_UPSTREAM}/{branch}"

                remote_branch = self.repo.refs[branch]  # type: ignore[index]
                return remote_branch.commit

            commit = commit_or_branch
            if not self.is_valid_commit(commit):
                # if commit does not exist locally, it might exist in remotes, hence run git fetch
                self.fetch()
                # if after git fetch, commit doesn't exist locally, it means the commit is invalid/does not exist
                if not self.is_valid_commit(commit):
                    raise CommitOrBranchNotFoundError(
                        commit_or_branch, from_remote=False
                    )

            return self.repo.commit(commit)

        else:
            if not self.is_valid_commit(
                commit_or_branch
            ) and not self.is_valid_local_branch(commit_or_branch):
                raise CommitOrBranchNotFoundError(commit_or_branch, from_remote=False)

            return self.repo.commit(commit_or_branch)

    def get_previous_commit(self, commit: Optional[str] = None) -> Commit:
        """
        Returns the previous commit of a specific commit.
        If not provided returns previous commit of the head commit.

        Args:
            commit: any commit
        """
        if commit:
            return self.get_commit(commit, from_remote=False).parents[0]

        return self.repo.head.commit.parents[0]

    def has_file_changed(
        self, file_path: Union[Path, str], commit1: str, commit2: str
    ) -> bool:
        """
        Checks if file has been changed between two commits.

        Args:
            file_path: file path
            commit1: the first commit to compare
            commit2: the second commit to compare

        Returns:
            True if file has been changed between two commits, False if not.
        """
        return bool(self.repo.git.diff(commit1, commit2, str(file_path)))

    def has_file_added(self, file_path: Union[Path, str], commit1: str, commit2: str):
        """
        Checks if a file has been added between two commits.

        Args:
            file_path: file path
            commit1: the first commit to compare
            commit2: the second commit to compare

        Returns:
            True if file has been added between two commits, False if not.
        """
        return (
            file_path
            in self.repo.git.diff(
                "--name-only", "--diff-filter=A", commit1, commit2
            ).splitlines()
        )

    def read_file_content(
        self, path: Union[Path, str], commit_or_branch: str, from_remote: bool = True
    ) -> bytes:
        commit = self.get_commit(commit_or_branch, from_remote=from_remote)
        path = (
            str(self.path_from_git_root(path))
            if Path(path).is_absolute()
            else str(path)
        )

        try:
            blob: Blob = commit.tree / path
        except KeyError:
            raise GitFileNotFoundError(
                commit_or_branch, path=path, from_remote=from_remote
            )
        return blob.data_stream.read()

    def is_file_exist_in_commit_or_branch(
        self, path: Union[Path, str], commit_or_branch: str, from_remote: bool = True
    ) -> bool:
        try:
            commit = self.get_commit(commit_or_branch, from_remote=from_remote)
        except CommitOrBranchNotFoundError:
            logger.debug(f"Could not get commit {commit_or_branch}")
            return False

        path = str(self.path_from_git_root(path))

        try:
            return commit.tree[path].path == path
        except KeyError:
            return False

    def list_files_in_dir(
        self,
        target_dir: Union[Path, str],
        git_sha: str,
    ) -> List[str]:
        """Retrieve the list of files under a given target_dir in a given commit.

        Args:
            target_dir (Union[Path, str]): The target dir to retrieve from.
            git_sha (str): The git_sha to retrieve from.

        Returns:
            list: The list of files under the given target_dir in the given git_sha.
        """
        try:
            files = []
            commit = self.repo.commit(git_sha)

            target_dir = self.path_from_git_root(target_dir)
            target_dir = str(target_dir)
            tree = commit.tree / target_dir

            def traverse_tree(tree, base_path=""):
                for item in tree:
                    item_path = f"{base_path}/{item.name}" if base_path else item.name
                    if item.type == "blob":  # File
                        files.append(item_path)
                    elif item.type == "tree":  # Directory
                        traverse_tree(item, item_path)

            traverse_tree(tree)
            return files
        except CommitOrBranchNotFoundError:
            logger.exception(f"Could not get commit {git_sha}")
        except Exception as e:
            logger.exception(
                f"Could not get files from {target_dir=} with {git_sha=}, reason: {e}"
            )
        finally:
            return files

    @lru_cache
    def get_all_files(self) -> Set[Path]:
        return set(map(Path, self.repo.git.ls_files("-z").split("\x00")))

    def modified_files(
        self,
        prev_ver: str = "",
        committed_only: bool = False,
        staged_only: bool = False,
        debug: bool = False,
        include_untracked: bool = False,
    ) -> Set[Path]:
        """Gets all the files that are recognized by git as modified against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set: A set of Paths to the modified files.
        """
        remote, branch = self.handle_prev_ver(prev_ver)
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status="M")
        if last_commit:
            self.debug_print(
                debug=debug, status="Modified", staged=set(), committed=last_commit
            )
            return last_commit

        # get all renamed files - some of these can be identified as modified by git,
        # but we want to identify them as renamed - so will remove them from the returned files.
        renamed = {
            item[0]  # type: ignore[index]
            for item in self.renamed_files(prev_ver, committed_only, staged_only)
        }

        # handle a case where a file is wrongly recognized as renamed (not 100% score) and
        # is actually of modified status
        untrue_rename_staged = self.handle_wrong_renamed_status(
            status="M", remote=remote, branch=branch, staged_only=True
        )
        untrue_rename_committed = self.handle_wrong_renamed_status(
            status="M", remote=remote, branch=branch, staged_only=False
        )

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)

        committed = set()

        if not staged_only:
            # get all committed files identified as modified which are changed from prev_ver.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {
                    Path(os.path.join(item.a_path))
                    for item in self.repo.remote(name=remote)
                    .refs[branch]
                    .commit.diff(current_branch_or_hash)
                    .iter_change_type("M")
                }.union(untrue_rename_committed)

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {
                    Path(os.path.join(item.a_path))  # type: ignore
                    for item in self.repo.commit(rev=branch)
                    .diff(current_branch_or_hash)
                    .iter_change_type("M")
                }.union(untrue_rename_committed)

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed modified files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = committed.intersection(all_branch_changed_files)

        # remove the renamed and deleted files from the committed
        committed = committed - renamed - deleted

        if committed_only:
            self.debug_print(
                debug=debug, status="Modified", staged=set(), committed=committed
            )
            return committed

        untracked: Set = set()
        if include_untracked:
            # get all untracked modified files
            untracked = self._get_untracked_files("M")

        # get all the files that are staged on the branch and identified as modified.
        staged = {
            Path(os.path.join(item.a_path))  # type: ignore
            for item in self.repo.head.commit.diff().iter_change_type("M")
        }.union(untracked).union(untrue_rename_staged)

        # If a file is Added in regards to prev_ver
        # and is then modified locally after being committed - it is identified as modified
        # but we want to identify the file as Added (its actual status against prev_ver) -
        # so will remove it from the staged modified files.
        # also remove the deleted and renamed files as well.
        if remote:
            committed_added = {
                Path(os.path.join(item.a_path))
                for item in self.repo.remote(name=remote)
                .refs[branch]
                .commit.diff(current_branch_or_hash)
                .iter_change_type("A")
            }

        # if remote does not exist we are checking against the commit sha1
        else:
            committed_added = {
                Path(os.path.join(item.a_path))  # type: ignore
                for item in self.repo.commit(rev=branch)
                .diff(current_branch_or_hash)
                .iter_change_type("A")
            }

        staged = staged - committed_added - renamed - deleted

        if staged_only:
            self.debug_print(
                debug=debug, status="Modified", staged=staged, committed=set()
            )
            return staged

        self.debug_print(
            debug=debug, status="Modified", staged=staged, committed=committed
        )

        return staged.union(committed)

    def added_files(
        self,
        prev_ver: str = "",
        committed_only: bool = False,
        staged_only: bool = False,
        debug: bool = False,
        include_untracked: bool = False,
    ) -> Set[Path]:
        """Gets all the files that are recognized by git as added against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set: A set of Paths to the added files.
        """
        remote, branch = self.handle_prev_ver(prev_ver)
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status="A")
        if last_commit:
            self.debug_print(
                debug=debug, status="Added", staged=set(), committed=last_commit
            )
            return last_commit

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)

        # handle a case where a file is wrongly recognized as renamed (not 100% score) and is actually of added status
        untrue_rename_staged = self.handle_wrong_renamed_status(
            status="A", remote=remote, branch=branch, staged_only=True
        )
        untrue_rename_committed = self.handle_wrong_renamed_status(
            status="A", remote=remote, branch=branch, staged_only=False
        )

        # get all committed files identified as added which are changed from prev_ver.
        # this can result in extra files identified which were not touched on this branch.
        if remote:
            committed = {
                Path(os.path.join(item.a_path))
                for item in self.repo.remote(name=remote)
                .refs[branch]
                .commit.diff(current_branch_or_hash)
                .iter_change_type("A")
            }.union(untrue_rename_committed)

        # if remote does not exist we are checking against the commit sha1
        else:
            committed = {
                Path(os.path.join(item.a_path))  # type: ignore
                for item in self.repo.commit(rev=branch)
                .diff(current_branch_or_hash)
                .iter_change_type("A")
            }.union(untrue_rename_committed)

        # identify all files that were touched on this branch regardless of status
        # intersect these with all the committed files to identify the committed added files.
        all_branch_changed_files = self._get_all_changed_files(prev_ver)
        committed = committed.intersection(all_branch_changed_files)

        # remove deleted files
        committed = committed - deleted

        if committed_only:
            self.debug_print(
                debug=debug, status="Added", staged=set(), committed=committed
            )
            return committed

        untracked_added: Set = set()
        untracked_modified: Set = set()
        if include_untracked:
            # get all untracked added files
            untracked_added = self._get_untracked_files("A")

            # get all untracked modified files
            untracked_modified = self._get_untracked_files("M")

        # get all the files that are staged on the branch and identified as added.
        staged = {
            Path(os.path.join(item.a_path))  # type: ignore
            for item in self.repo.head.commit.diff().iter_change_type("A")
        }.union(untrue_rename_staged)

        # If a file is Added in regards to prev_ver
        # and is then modified locally after being committed - it is identified as modified
        # but we want to identify the file as Added (its actual status against prev_ver) -
        # so will added it from the staged added files.
        # same goes to untracked files - can be identified as modified but are actually added against prev_ver
        committed_added_locally_modified = {
            Path(os.path.join(item.a_path))  # type: ignore
            for item in self.repo.head.commit.diff().iter_change_type("M")
        }.intersection(committed)
        untracked = untracked_added.union(untracked_modified.intersection(committed))

        staged = staged.union(committed_added_locally_modified).union(untracked)

        # remove deleted files.
        staged = staged - deleted

        if staged_only:
            self.debug_print(
                debug=debug, status="Added", staged=staged, committed=set()
            )
            return staged

        self.debug_print(
            debug=debug, status="Added", staged=staged, committed=committed
        )

        return staged.union(committed)

    def deleted_files(
        self,
        prev_ver: str = "",
        committed_only: bool = False,
        staged_only: bool = False,
        include_untracked: bool = False,
    ) -> Set[Path]:
        """Gets all the files that are recognized by git as deleted against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set: A set of Paths to the deleted files.
        """
        remote, branch = self.handle_prev_ver(prev_ver)
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status="D")
        if last_commit:
            return last_commit

        committed = set()

        if not staged_only:
            # get all committed files identified as added which are changed from prev_ver.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {
                    Path(os.path.join(item.a_path))
                    for item in self.repo.remote(name=remote)
                    .refs[branch]
                    .commit.diff(current_branch_or_hash)
                    .iter_change_type("D")
                }

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {
                    Path(os.path.join(item.a_path))  # type: ignore
                    for item in self.repo.commit(rev=branch)
                    .diff(current_branch_or_hash)
                    .iter_change_type("D")
                }

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed added files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = committed.intersection(all_branch_changed_files)

        if committed_only:
            return committed

        untracked: Set = set()
        if include_untracked:
            # get all untracked deleted files
            untracked = self._get_untracked_files("D")

        # get all the files that are staged on the branch and identified as added.
        staged = {
            Path(os.path.join(item.a_path))  # type: ignore
            for item in self.repo.head.commit.diff().iter_change_type("D")
        }.union(untracked)

        if staged_only:
            return staged

        return staged.union(committed)

    def renamed_files(
        self,
        prev_ver: str = "",
        committed_only: bool = False,
        staged_only: bool = False,
        debug: bool = False,
        include_untracked: bool = False,
        get_only_current_file_names: bool = False,
    ) -> Union[Set[Tuple[Path, Path]], Set[Path]]:
        """Gets all the files that are recognized by git as renamed against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
            get_only_current_file_names (bool): Whether to get only the current file names and not the old file names.
        Returns:
            Set: A set of Tuples of Paths to the renamed files -
            first element being the old file path and the second is the new.
        """
        remote, branch = self.handle_prev_ver(prev_ver)
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status="R")
        if last_commit:
            self.debug_print(
                debug=debug, status="Renamed", staged=set(), committed=last_commit
            )
            return last_commit

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)
        committed = set()

        if not staged_only:
            # get all committed files identified as renamed which are changed from prev_ver and are with 100% score.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {
                    (Path(item.a_path), Path(item.b_path))
                    for item in self.repo.remote(name=remote)
                    .refs[branch]
                    .commit.diff(current_branch_or_hash)
                    .iter_change_type("R")
                    if item.score == 100
                }

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {
                    (Path(item.a_path), Path(item.b_path))  # type: ignore
                    for item in self.repo.commit(rev=branch)
                    .diff(current_branch_or_hash)
                    .iter_change_type("R")
                    if item.score == 100
                }

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed added files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = {
                tuple_item
                for tuple_item in committed
                if (
                    tuple_item[1] in all_branch_changed_files
                    and tuple_item[1] not in deleted
                )
            }

        if committed_only:
            self.debug_print(
                debug=debug, status="Renamed", staged=set(), committed=committed
            )
            if get_only_current_file_names:
                committed_only_new = {file[1] for file in committed}
                return committed_only_new

            return committed

        untracked: Set = set()
        if include_untracked:
            # get all untracked renamed files
            untracked = self._get_untracked_files("R")

        # get all the files that are staged on the branch and identified as renamed and are with 100% score.
        staged = {
            (Path(item.a_path), Path(item.b_path))  # type: ignore
            for item in self.repo.head.commit.diff().iter_change_type("R")
            if item.score == 100
        }.union(untracked)

        if staged_only:
            self.debug_print(
                debug=debug, status="Renamed", staged=staged, committed=set()
            )
            if get_only_current_file_names:
                staged_only_new = {file[1] for file in staged}
                return staged_only_new

            return staged

        self.debug_print(
            debug=debug, status="Renamed", staged=staged, committed=committed
        )

        all_renamed_files = staged.union(committed)
        if get_only_current_file_names:
            all_renamed_files_only_new = {file[1] for file in all_renamed_files}
            return all_renamed_files_only_new

        return all_renamed_files

    def get_all_changed_pack_ids(self, prev_ver: str) -> Set[str]:
        return {
            file.parts[1]
            for file in self._get_all_changed_files(prev_ver) | self._get_staged_files()
            if file.parts[0] == PACKS_FOLDER
        }

    def _get_untracked_files(self, requested_status: str) -> set:
        """return all untracked files of the given requested status.
        Args:
            requested_status (str): M, A, R, D - the git status to return
        Returns:
            Set: of path strings which include the untracked files of a certain status.
        """
        git_status = self.repo.git.status("--short", "-u").split("\n")

        # in case there are no local changes - return
        if git_status == [""]:
            return set()

        extracted_paths = set()
        for line in git_status:
            line = line.strip()
            file_status = line.split()[0].upper() if not line.startswith("?") else "A"
            if file_status.startswith(requested_status):
                if requested_status == "R":
                    if file_status == "R100":
                        extracted_paths.add(
                            (Path(line.split()[-2]), Path(line.split()[-1]))
                        )
                else:
                    extracted_paths.add(Path(line.split()[-1]))  # type: ignore

        return extracted_paths

    @lru_cache
    def _get_staged_files(self) -> Set[Path]:
        """Get only staged files

        Returns:
            Set[Path]: The staged files to return
        """
        return {
            Path(item)
            for item in self.repo.git.diff("--cached", "--name-only").split("\n")
            if item
        }

    def _get_all_changed_files(self, prev_ver: Optional[str] = None) -> Set[Path]:
        """
        Get all the files changed in the current branch without status distinction.

        Args:
            prev_ver (str): The base branch against which the comparison is made.

        Returns:
            Set[Path]: of Paths to files changed in the current branch.
        """

        self.fetch()
        remote, branch = self.handle_prev_ver(prev_ver)
        current_hash = self.get_current_commit_hash()

        if remote:
            return {
                Path(os.path.join(item))
                for item in self.repo.git.diff(
                    "--name-only", f"{remote}/{branch}...{current_hash}"
                ).split("\n")
                if item
            }

        # if remote does not exist we are checking against the commit sha1
        else:
            return {
                Path(os.path.join(item))
                for item in self.repo.git.diff(
                    "--name-only", f"{branch}...{current_hash}"
                ).split("\n")
                if item
            }

    def _only_last_commit(
        self, prev_ver: str, requested_status: Lit_change_type
    ) -> Set:  # pragma: no cover
        """Get all the files that were changed in the last commit of a given type when checking a branch against itself.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            requested_status (Lit_change_type): M(odified), A(dded), R(enamed), D(eleted) - the git status to return
        Returns:
            Set: of Paths to files changed in the the last commit or an empty set if not
            running on master against master.
        """
        # when checking branch against itself only return the last commit.
        if self.get_current_git_branch_or_hash() != self.handle_prev_ver(prev_ver)[1]:
            return set()

        try:
            if requested_status != "R":
                return {
                    Path(os.path.join(item.a_path))  # type: ignore
                    for item in self.repo.commit("HEAD~1")
                    .diff()
                    .iter_change_type(requested_status)
                    if item.score == 100
                }
            else:
                return {
                    (Path(item.a_path), Path(item.b_path))  # type: ignore
                    for item in self.repo.commit("HEAD~1")
                    .diff()
                    .iter_change_type(requested_status)
                }
        except gitdb.exc.BadName:
            # in case no last commit exists - just pass
            pass

        return set()

    def check_if_remote_exists(self, remote: str) -> bool:
        if "/" in remote:
            remote = remote.split("/")[0]

        return remote in self.repo.remotes

    @staticmethod
    def find_primary_branch(repo: Repo) -> str:
        # Try to get the main branch
        if not repo:
            # Null input
            return ""
        if not hasattr(repo, "remotes"):
            # No remotes
            return ""
        for current_remote in repo.remotes:
            # No refs in this remote
            if not hasattr(current_remote, "refs"):
                return ""
            for current_remote_ref in current_remote.refs:
                current_remote_ref_str = str(current_remote_ref)
                if current_remote_ref_str == f"{DEMISTO_GIT_UPSTREAM}/main":
                    return "main"
                elif current_remote_ref_str == f"{DEMISTO_GIT_UPSTREAM}/master":
                    return "master"
                elif (
                    current_remote_ref_str
                    == f"{DEMISTO_GIT_UPSTREAM}/{DEMISTO_GIT_PRIMARY_BRANCH}"
                ):
                    return DEMISTO_GIT_PRIMARY_BRANCH
        return ""

    def handle_prev_ver(self, prev_ver: Optional[str] = None):
        # check for sha1 in regex
        sha1_pattern = re.compile(r"\b[0-9a-f]{40}\b", flags=re.IGNORECASE)
        if prev_ver and sha1_pattern.match(prev_ver):
            return None, prev_ver

        if prev_ver and "/" in prev_ver:
            remote, branch = prev_ver.split("/", 1)
            remote = (
                remote
                if self.check_if_remote_exists(remote)
                else str(self.repo.remote())
            )

        else:
            remote = str(self.repo.remote())
            if prev_ver:
                branch = prev_ver
            else:
                branch = self.find_primary_branch(repo=self.repo)
                if not branch:
                    raise Exception(
                        "Unable to find main or master branch from current working directory - aborting."
                    )
        return remote, branch

    def get_current_git_branch_or_hash(self) -> str:
        try:
            return self.get_current_working_branch()
        except TypeError:
            return self.get_current_commit_hash()

    def is_valid_local_branch(self, branch_name: str) -> bool:
        return branch_name in self.repo.heads

    def is_valid_remote_branch(self, branch_name: str) -> bool:
        if DEMISTO_GIT_UPSTREAM not in branch_name:
            branch_name = f"{DEMISTO_GIT_UPSTREAM}/{branch_name}"
        return branch_name in self.repo.refs  # type: ignore[operator]

    def is_valid_commit(self, commit_hash: str) -> bool:
        """
        Returns True if the commit hash provided is indeed a valid commit (and not a branch!)

        if commit_hash is a branch / commit is invalid, will return False
        """
        try:
            commit = self.repo.commit(commit_hash)
            return commit.hexsha == commit_hash
        except (ValueError, gitdb.exc.BadName):
            return False

    def get_current_working_branch(self) -> str:
        return str(self.repo.active_branch)

    def get_current_commit_hash(self) -> str:
        return self.repo.head.object.hexsha

    def git_path(self) -> str:
        git_path = self.repo.git.rev_parse("--show-toplevel")
        return git_path.replace("\n", "")

    def debug_print(
        self, debug: bool, status: str, staged: Set, committed: Set
    ) -> None:
        if not debug:
            return

        def sort_paths(paths: Set) -> Sequence:
            return sorted((str(path) for path in paths))

        if staged:
            click.echo(f"######## - {status} staged:")
            click.echo(", ".join(sort_paths(staged)))
            click.echo("\n")
        if committed:
            click.echo(f"######## - {status} committed:")
            click.echo(", ".join(sort_paths(committed)))
            click.echo("\n")

    def handle_wrong_renamed_status(
        self, status: str, remote: str, branch: str, staged_only: bool
    ) -> Set[Path]:
        """Get all the files that are recognized as non-100% rename in a given file status.
        Args:
            status (str): the requested file status
            remote (str): the used git remote
            branch (str): the used git branch
            staged_only (bool): whether to bring only staged files
        Returns:
            Set: of Paths to non 100% renamed files which are of a given status.
        """
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        if staged_only:
            return {
                Path(item.b_path)  # type: ignore
                for item in self.repo.head.commit.diff().iter_change_type("R")
                if item.score < 100  # type: ignore
                and self._check_file_status(
                    file_path=str(item.b_path), remote=remote, branch=branch
                )
                == status
            }

        if remote:
            return {
                Path(item.b_path)
                for item in self.repo.remote(name=remote)
                .refs[branch]
                .commit.diff(current_branch_or_hash)
                .iter_change_type("R")
                if item.score < 100
                and self._check_file_status(
                    file_path=str(item.b_path), remote=remote, branch=branch
                )
                == status
            }

        # if remote does not exist we are checking against the commit sha1
        return {
            Path(item.b_path)  # type: ignore
            for item in self.repo.commit(rev=branch)
            .diff(current_branch_or_hash)
            .iter_change_type("R")
            if item.score < 100  # type: ignore
            and self._check_file_status(
                file_path=str(item.b_path), remote=remote, branch=branch
            )
            == status
        }

    def _check_file_status(
        self,
        file_path: str,
        remote: str,
        branch: str,
        feature_branch_or_hash: Optional[str] = None,
    ) -> str:
        """Get the git status of a given file path
        Args:
            file_path (str): the file path to check
            remote (str): the used git remote
            branch (str): the used git branch
            feature_branch_or_hash (str | None): compare against a specific branch or commit
        Returns:
            str: the git status of the file (M, A, R, D).
        """
        if not feature_branch_or_hash:
            feature_branch_or_hash = self.get_current_git_branch_or_hash()

        if remote:
            diff_line = self.repo.git.diff(
                "--name-status",
                f"{remote}/{branch}...{feature_branch_or_hash}",
                "--",
                file_path,
            )

        # if remote does not exist we are checking against the commit sha1
        else:
            diff_line = self.repo.git.diff(
                "--name-status", f"{branch}...{feature_branch_or_hash}", "--", file_path
            )

        if not diff_line:
            return ""

        return diff_line.split()[0].upper() if not diff_line.startswith("?") else "A"

    def get_local_remote_file_content(self, git_file_path: str) -> str:
        """Get local file content from remote branch. For example get origin/master:README.md

        Args:
            git_file_path: The git file path. For example get origin/master:README.md

        Returns:
            The fetched file content.
        """
        file_content = self.repo.git.show(git_file_path)
        return file_content

    def get_local_remote_file_path(
        self, full_file_path: str, tag: str, from_remote: bool = True
    ) -> str:
        """Get local file path of remote branch. For example get origin/master:README.md

        Args:
            full_file_path: The file path to fetch. For example 'content/README.md'
            tag: The tag of the branch. For example 'master'
            from_remote: whether to build the file path for remote branch or local branch

        Returns:
            The git file path. For example get origin/master:README.md
        """
        git_file_path = f"{tag}:{self.path_from_git_root(full_file_path)}"

        if from_remote:
            try:
                remote_name: Union[Remote, str] = self.repo.remote()
            except ValueError as exc:
                if "Remote named 'origin' didn't exist" in str(exc):
                    remote_name = "origin"
                else:
                    raise exc
            return f"{remote_name}/{git_file_path}"

        return git_file_path

    def get_all_changed_files(
        self,
        prev_ver: str = "",
        committed_only: bool = False,
        staged_only: bool = False,
        debug: bool = False,
        include_untracked: bool = False,
    ) -> Set[Path]:
        """
        Get a set of all changed files in the branch (modified, added and renamed)

        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set[Path]: A set of all the changed files in the given branch when comparing to prev_ver
        """
        self.fetch()
        modified_files: Set[Path] = self.modified_files(
            prev_ver=prev_ver,
            committed_only=committed_only,
            staged_only=staged_only,
            debug=debug,
            include_untracked=include_untracked,
        )
        added_files: Set[Path] = self.added_files(
            prev_ver=prev_ver,
            committed_only=committed_only,
            staged_only=staged_only,
            debug=debug,
            include_untracked=include_untracked,
        )
        renamed_files: Set[Path] = self.renamed_files(
            prev_ver=prev_ver,
            committed_only=committed_only,  # type: ignore[assignment]
            staged_only=staged_only,
            debug=debug,
            include_untracked=include_untracked,
            get_only_current_file_names=True,
        )
        return modified_files.union(added_files).union(renamed_files)

    def _is_file_git_ignored(self, file_path: str) -> bool:
        """return wether the file is in .gitignore file or not.
        Args:
            file_path (str): the file to check.
        Returns:
            bool: True if the file is ignored. Otherwise, return False.
        """
        return bool(self.repo.ignored(file_path))

    def fetch(self):
        try:
            self.repo.remote(DEMISTO_GIT_UPSTREAM).fetch(verbose=False)
        except Exception as e:
            logger.warning(
                f"Failed to fetch branch '{self.get_current_working_branch()}' "
                f"from remote '{self.repo.remote().name}' ({self.repo.remote().url}). Continuing without fetching."
            )
            logger.debug(f"Error: {e}")

    def fetch_all(self):
        for remote in self.repo.remotes:
            remote.fetch()

    def commit_files(self, commit_message: str, files: Union[List, str] = "."):
        self.repo.git.add(files)
        self.repo.index.commit(commit_message)

    def has_file_permissions_changed(
        self, file_path: str, ci: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check whether the supplied file permissions have changed.
        If we're in a CI environment, we check for changes against
        the remote base branch. If not, we assume we're running in a local
        environment the commit was made.

        Args:
        - `file_path` (``str``): The path to the file to check for
        permission changes.
        - `ci` (``bool``): Whether we're running in a CI environment.

        Returns:
        - `bool` indicating whether the file permissions have changed.
        - `str` with the old permissions.
        - `str` with the new permissions.
        """

        # If we're in a CI environment, we need to get the
        # remote (e.g. origin), base branch and current branch since
        # the local branches are unavailable
        if ci:
            branch = os.getenv("BRANCH_NAME", self.get_current_git_branch_or_hash())
            base_branch = (
                self.find_primary_branch(self.repo)
                if self.find_primary_branch(self.repo)
                else DEMISTO_GIT_PRIMARY_BRANCH
            )
            upstream = (
                self.repo.remote().name if self.repo.remote() else DEMISTO_GIT_UPSTREAM
            )
            summary_output = self.repo.git.diff(
                "--summary",
                f"{upstream}/{base_branch}...{upstream}/{branch}",
                file_path,
            )
        else:
            summary_output = self.repo.git.diff("--summary", "--staged", file_path)

        pattern = r"mode change (\d{6}) => (\d{6}) (.+)"

        match = re.search(pattern, summary_output)

        if match:
            old_permissions = match.group(1)
            new_permissions = match.group(2)

            return True, old_permissions, new_permissions
        else:
            return False, None, None

    def stage_file(self, file_path: Union[Path, str]):
        """
        Stage a file.

        Args:
        - `file_path` (``Path | str``): The file path to add.
        """

        if isinstance(file_path, str):
            file_path = Path(file_path)

        if file_path.exists():
            self.repo.git.add(str(file_path))
            logger.debug(f"Staged file '{file_path}'")
        else:
            logger.error(f"File '{file_path}' doesn't exist. Not adding.")

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

import click
import gitdb
from git import (
    InvalidGitRepositoryError,
    Repo,  # noqa: TID251: required to create GitUtil
)
from git.diff import Lit_change_type
from git.exc import GitError, NoSuchPathError
from git.objects import Blob, Commit
from git.remote import Remote

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    PACKS_FOLDER,
)


class CommitOrBranchNotFoundError(GitError):
    def __init__(
        self, commit_or_branch: str, exception: Exception, from_remote: bool = True
    ):
        if from_remote:
            commit_or_branch = f"{DEMISTO_GIT_UPSTREAM}/{commit_or_branch}"
        super().__init__(
            f"Commit/Branch {commit_or_branch} could not be found, error: {exception}"
        )


class GitFileNotFoundError(NoSuchPathError):
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
        path: Optional[Union[str, Path]] = None,
        search_parent_directories: bool = True,
    ):

        if isinstance(path, str):
            repo_path = Path(path)
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
        try:
            return Path(path).relative_to(Path(self.repo.working_dir))
        except ValueError:
            return Path(os.path.relpath(str(path), self.git_path()))

    def get_commit(self, commit_or_branch: str, from_remote: bool = True) -> Commit:
        if from_remote:
            # check if file exist in remote branch
            try:
                remote_branch = self.repo.refs[  # type: ignore[index]
                    f"{DEMISTO_GIT_UPSTREAM}/{commit_or_branch}"
                ]
                return remote_branch.commit
            except IndexError as e:
                # there isn't remote branch like this
                raise CommitOrBranchNotFoundError(
                    commit_or_branch, from_remote=from_remote, exception=e
                )
        else:
            # check if file exist in a local branch/commit
            try:
                return self.repo.commit(commit_or_branch)
            except ValueError as e:
                # commit/branch does not exist
                raise CommitOrBranchNotFoundError(
                    commit_or_branch, from_remote=from_remote, exception=e
                )

    def read_file_content(
        self, path: Union[Path, str], commit_or_branch: str, from_remote: bool = True
    ) -> bytes:

        commit = self.get_commit(commit_or_branch, from_remote=from_remote)
        path = str(self.path_from_git_root(path))

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
            return False

        path = str(self.path_from_git_root(path))

        try:
            return commit.tree[path].path == path
        except KeyError:
            return False

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
        renamed = {item[0] for item in self.renamed_files(prev_ver, committed_only, staged_only)}  # type: ignore[index]

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
                    Path(os.path.join(item.a_path))
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
        staged = (
            {
                Path(os.path.join(item.a_path))
                for item in self.repo.head.commit.diff().iter_change_type("M")
            }
            .union(untracked)
            .union(untrue_rename_staged)
        )

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
                Path(os.path.join(item.a_path))
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
                Path(os.path.join(item.a_path))
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
            Path(os.path.join(item.a_path))
            for item in self.repo.head.commit.diff().iter_change_type("A")
        }.union(untrue_rename_staged)

        # If a file is Added in regards to prev_ver
        # and is then modified locally after being committed - it is identified as modified
        # but we want to identify the file as Added (its actual status against prev_ver) -
        # so will added it from the staged added files.
        # same goes to untracked files - can be identified as modified but are actually added against prev_ver
        committed_added_locally_modified = {
            Path(os.path.join(item.a_path))
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
                    Path(os.path.join(item.a_path))
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
            Path(os.path.join(item.a_path))
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
                    (Path(item.a_path), Path(item.b_path))
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
            (Path(item.a_path), Path(item.b_path))
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

    def _get_all_changed_files(self, prev_ver: str = "") -> Set[Path]:
        """Get all the files changed in the current branch without status distinction.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
        Returns:
            Set: of Paths to files changed in the current branch.
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
                    Path(os.path.join(item.a_path))
                    for item in self.repo.commit("HEAD~1")
                    .diff()
                    .iter_change_type(requested_status)
                    if item.score == 100
                }
            else:
                return {
                    (Path(item.a_path), Path(item.b_path))
                    for item in self.repo.commit("HEAD~1")
                    .diff()
                    .iter_change_type(requested_status)
                }
        except gitdb.exc.BadName:
            # in case no last commit exists - just pass
            pass

        return set()

    def check_if_remote_exists(self, remote):
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

    def handle_prev_ver(self, prev_ver: str = ""):
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
            branch = ""
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

    def get_current_working_branch(self) -> str:
        return str(self.repo.active_branch)

    def get_current_commit_hash(self) -> str:
        return str(self.repo.head.object.hexsha)

    def git_path(self) -> str:
        git_path = self.repo.git.rev_parse("--show-toplevel")
        return git_path.replace("\n", "")

    def debug_print(
        self, debug: bool, status: str, staged: Set, committed: Set
    ) -> None:
        if debug:
            click.echo(f"######## - {status} staged:")
            click.echo(staged)
            click.echo("\n")
            click.echo(f"######## - {status} committed:")
            click.echo(committed)
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
                Path(item.b_path)
                for item in self.repo.head.commit.diff().iter_change_type("R")
                if item.score < 100
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
            Path(item.b_path)
            for item in self.repo.commit(rev=branch)
            .diff(current_branch_or_hash)
            .iter_change_type("R")
            if item.score < 100
            and self._check_file_status(
                file_path=str(item.b_path), remote=remote, branch=branch
            )
            == status
        }

    def _check_file_status(self, file_path: str, remote: str, branch: str) -> str:
        """Get the git status of a given file path
        Args:
            file_path (str): the file path to check
            remote (str): the used git remote
            branch (str): the used git branch
        Returns:
            str: the git status of the file (M, A, R, D).
        """
        current_branch_or_hash = self.get_current_git_branch_or_hash()

        if remote:
            diff_line = self.repo.git.diff(
                "--name-status",
                f"{remote}/{branch}...{current_branch_or_hash}",
                "--",
                file_path,
            )

        # if remote does not exist we are checking against the commit sha1
        else:
            diff_line = self.repo.git.diff(
                "--name-status", f"{branch}...{current_branch_or_hash}", "--", file_path
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
        """Get a set of all changed files in the branch (modified, added and renamed)

        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set. A set of all the changed files in the given branch when comparing to prev_ver
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

    @lru_cache
    def fetch(self):
        self.repo.remote().fetch()

    @lru_cache
    def fetch_all(self):
        for remote in self.repo.remotes:
            remote.fetch()

    def commit_files(self, commit_message: str, files: Union[List, str] = "."):
        self.repo.git.add(files)
        self.repo.index.commit(commit_message)

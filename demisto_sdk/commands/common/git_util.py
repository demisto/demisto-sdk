import os
import re
from pathlib import Path
from typing import Set, Tuple

import click
import gitdb
from git import InvalidGitRepositoryError, Repo


class GitUtil:
    repo: Repo

    def __init__(self, repo: Repo = None):
        if not repo:
            try:
                self.repo = Repo(Path.cwd(), search_parent_directories=True)
            except InvalidGitRepositoryError:
                raise InvalidGitRepositoryError("Unable to find Repository from current working directory - aborting")
        else:
            self.repo = repo

    def modified_files(self, prev_ver: str = 'master', committed_only: bool = False,
                       staged_only: bool = False, debug: bool = False, include_untracked: bool = False) -> Set[Path]:
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
        remote, branch = self._handle_prev_ver(prev_ver)

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status='M')
        if last_commit:
            self.debug_print(debug=debug, status='Modified', staged=set(), committed=last_commit)
            return last_commit

        # get all renamed files - some of these can be identified as modified by git,
        # but we want to identify them as renamed - so will remove them from the returned files.
        renamed = {item[0] for item in self.renamed_files(prev_ver, committed_only, staged_only)}

        # handle a case where a file is wrongly recognized as renamed (not 100% score) and
        # is actually of modified status
        untrue_rename_staged = self.handle_wrong_renamed_status(status='M', remote=remote, branch=branch,
                                                                staged_only=True)
        untrue_rename_committed = self.handle_wrong_renamed_status(status='M', remote=remote, branch=branch,
                                                                   staged_only=False)

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)

        committed = set()

        if not staged_only:
            # get all committed files identified as modified which are changed from prev_ver.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {Path(os.path.join(item.a_path)) for item
                             in self.repo.remote(name=remote).refs[branch].commit.diff(
                    self.repo.active_branch).iter_change_type('M')}.union(untrue_rename_committed)

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {Path(os.path.join(item.a_path)) for item in self.repo.commit(rev=prev_ver).diff(
                    self.repo.active_branch).iter_change_type('M')}.union(untrue_rename_committed)

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed modified files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = committed.intersection(all_branch_changed_files)

        # remove the renamed and deleted files from the committed
        committed = committed - renamed - deleted

        if committed_only:
            self.debug_print(debug=debug, status='Modified', staged=set(), committed=committed)
            return committed

        untracked = set()  # type: Set
        if include_untracked:
            # get all untracked modified files
            untracked = self._get_untracked_files('M')

        # get all the files that are staged on the branch and identified as modified.
        staged = {Path(os.path.join(item.a_path)) for item
                  in self.repo.head.commit.diff().iter_change_type('M')}.union(untracked).union(untrue_rename_staged)

        # If a file is Added in regards to prev_ver
        # and is then modified locally after being committed - it is identified as modified
        # but we want to identify the file as Added (its actual status against prev_ver) -
        # so will remove it from the staged modified files.
        # also remove the deleted and renamed files as well.
        if remote:
            committed_added = {Path(os.path.join(item.a_path)) for item in
                               self.repo.remote(name=remote).refs[branch].commit.
                               diff(self.repo.active_branch).iter_change_type('A')}

        # if remote does not exist we are checking against the commit sha1
        else:
            committed_added = {Path(os.path.join(item.a_path)) for item in
                               self.repo.commit(rev=prev_ver).diff(self.repo.active_branch).iter_change_type('A')}

        staged = staged - committed_added - renamed - deleted

        if staged_only:
            self.debug_print(debug=debug, status='Modified', staged=staged, committed=set())
            return staged

        self.debug_print(debug=debug, status='Modified', staged=staged, committed=committed)

        return staged.union(committed)

    def added_files(self, prev_ver: str = 'master', committed_only: bool = False,
                    staged_only: bool = False, debug: bool = False, include_untracked: bool = False) -> Set[Path]:
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
        remote, branch = self._handle_prev_ver(prev_ver)

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status='A')
        if last_commit:
            self.debug_print(debug=debug, status='Added', staged=set(), committed=last_commit)
            return last_commit

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)

        # handle a case where a file is wrongly recognized as renamed (not 100% score) and is actually of added status
        untrue_rename_staged = self.handle_wrong_renamed_status(status='A', remote=remote, branch=branch,
                                                                staged_only=True)
        untrue_rename_committed = self.handle_wrong_renamed_status(status='A', remote=remote, branch=branch,
                                                                   staged_only=False)

        # get all committed files identified as added which are changed from prev_ver.
        # this can result in extra files identified which were not touched on this branch.
        if remote:
            committed = {Path(os.path.join(item.a_path)) for item
                         in self.repo.remote(name=remote).refs[branch].commit.diff(
                self.repo.active_branch).iter_change_type('A')}.union(untrue_rename_committed)

        # if remote does not exist we are checking against the commit sha1
        else:
            committed = {Path(os.path.join(item.a_path)) for item
                         in self.repo.commit(rev=prev_ver).diff(
                self.repo.active_branch).iter_change_type('A')}.union(untrue_rename_committed)

        # identify all files that were touched on this branch regardless of status
        # intersect these with all the committed files to identify the committed added files.
        all_branch_changed_files = self._get_all_changed_files(prev_ver)
        committed = committed.intersection(all_branch_changed_files)

        # remove deleted files
        committed = committed - deleted

        if committed_only:
            self.debug_print(debug=debug, status='Added', staged=set(), committed=committed)
            return committed

        untracked_added = set()  # type: Set
        untracked_modified = set()  # type: Set
        if include_untracked:
            # get all untracked added files
            untracked_added = self._get_untracked_files('A')

            # get all untracked modified files
            untracked_modified = self._get_untracked_files('M')

        # get all the files that are staged on the branch and identified as added.
        staged = {Path(os.path.join(item.a_path)) for item in
                  self.repo.head.commit.diff().iter_change_type('A')}.union(untrue_rename_staged)

        # If a file is Added in regards to prev_ver
        # and is then modified locally after being committed - it is identified as modified
        # but we want to identify the file as Added (its actual status against prev_ver) -
        # so will added it from the staged added files.
        # same goes to untracked files - can be identified as modified but are actually added against prev_ver
        committed_added_locally_modified = {Path(os.path.join(item.a_path)) for item in
                                            self.repo.head.commit.diff().iter_change_type('M')}.intersection(committed)
        untracked = untracked_added.union(untracked_modified.intersection(committed))

        staged = staged.union(committed_added_locally_modified).union(untracked)

        # remove deleted files.
        staged = staged - deleted

        if staged_only:
            self.debug_print(debug=debug, status='Added', staged=staged, committed=set())
            return staged

        self.debug_print(debug=debug, status='Added', staged=staged, committed=committed)

        return staged.union(committed)

    def deleted_files(self, prev_ver: str = 'master', committed_only: bool = False,
                      staged_only: bool = False, include_untracked: bool = False) -> Set[Path]:
        """Gets all the files that are recognized by git as deleted against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set: A set of Paths to the deleted files.
        """
        remote, branch = self._handle_prev_ver(prev_ver)

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status='D')
        if last_commit:
            return last_commit

        committed = set()

        if not staged_only:
            # get all committed files identified as added which are changed from prev_ver.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {Path(os.path.join(item.a_path)) for item
                             in self.repo.remote(name=remote).refs[branch].commit.diff(
                    self.repo.active_branch).iter_change_type('D')}

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {Path(os.path.join(item.a_path)) for item
                             in self.repo.commit(rev=prev_ver).diff(
                    self.repo.active_branch).iter_change_type('D')}

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed added files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = committed.intersection(all_branch_changed_files)

        if committed_only:
            return committed

        untracked = set()  # type: Set
        if include_untracked:
            # get all untracked deleted files
            untracked = self._get_untracked_files('D')

        # get all the files that are staged on the branch and identified as added.
        staged = {Path(os.path.join(item.a_path)) for item in
                  self.repo.head.commit.diff().iter_change_type('D')}.union(untracked)

        if staged_only:
            return staged

        return staged.union(committed)

    def renamed_files(self, prev_ver: str = 'master', committed_only: bool = False,
                      staged_only: bool = False, debug: bool = False,
                      include_untracked: bool = False) -> Set[Tuple[Path, Path]]:
        """Gets all the files that are recognized by git as renamed against the prev_ver.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            committed_only (bool): Whether to return only committed files.
            staged_only (bool): Whether to return only staged files.
            debug (bool): Whether to print the debug logs.
            include_untracked (bool): Whether to include untracked files.
        Returns:
            Set: A set of Tuples of Paths to the renamed files -
            first element being the old file path and the second is the new.
        """
        remote, branch = self._handle_prev_ver(prev_ver)

        # when checking branch against itself only return the last commit.
        last_commit = self._only_last_commit(prev_ver, requested_status='R')
        if last_commit:
            self.debug_print(debug=debug, status='Renamed', staged=set(), committed=last_commit)
            return last_commit

        deleted = self.deleted_files(prev_ver, committed_only, staged_only)
        committed = set()

        if not staged_only:
            # get all committed files identified as renamed which are changed from prev_ver and are with 100% score.
            # this can result in extra files identified which were not touched on this branch.
            if remote:
                committed = {(Path(item.a_path), Path(item.b_path)) for item
                             in self.repo.remote(name=remote).refs[branch].commit.diff(
                    self.repo.active_branch).iter_change_type('R') if item.score == 100}

            # if remote does not exist we are checking against the commit sha1
            else:
                committed = {(Path(item.a_path), Path(item.b_path)) for item
                             in self.repo.commit(rev=prev_ver).diff(
                    self.repo.active_branch).iter_change_type('R') if item.score == 100}

            # identify all files that were touched on this branch regardless of status
            # intersect these with all the committed files to identify the committed added files.
            all_branch_changed_files = self._get_all_changed_files(prev_ver)
            committed = {tuple_item for tuple_item in committed
                         if (tuple_item[1] in all_branch_changed_files and tuple_item[1] not in deleted)}

        if committed_only:
            self.debug_print(debug=debug, status='Renamed', staged=set(), committed=committed)
            return committed

        untracked = set()  # type:Set
        if include_untracked:
            # get all untracked renamed files
            untracked = self._get_untracked_files('R')

        # get all the files that are staged on the branch and identified as renamed and are with 100% score.
        staged = {(Path(item.a_path), Path(item.b_path)) for item
                  in self.repo.head.commit.diff().iter_change_type('R') if item.score == 100}.union(untracked)

        if staged_only:
            self.debug_print(debug=debug, status='Renamed', staged=staged, committed=set())
            return staged

        self.debug_print(debug=debug, status='Renamed', staged=staged, committed=committed)

        return staged.union(committed)

    def _get_untracked_files(self, requested_status: str) -> set:
        """return all untracked files of the given requested status.
        Args:
            requested_status (str): M, A, R, D - the git status to return
        Returns:
            Set: of path strings which include the untracked files of a certain status.
        """
        git_status = self.repo.git.status('--short', '-u').split('\n')

        # in case there are no local changes - return
        if git_status == ['']:
            return set()

        extracted_paths = set()
        for line in git_status:
            line = line.strip()
            file_status = line.split()[0].upper() if not line.startswith('?') else 'A'
            if file_status.startswith(requested_status):
                if requested_status == 'R':
                    if file_status == 'R100':
                        extracted_paths.add((Path(line.split()[-2]), Path(line.split()[-1])))
                else:
                    extracted_paths.add(Path(line.split()[-1]))  # type: ignore

        return extracted_paths

    def _get_all_changed_files(self, prev_ver: str) -> Set[Path]:
        """Get all the files changed in the current branch without status distinction.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
        Returns:
            Set: of Paths to files changed in the current branch.
        """
        remote, branch = self._handle_prev_ver(prev_ver)

        if remote:
            return {Path(os.path.join(item)) for item
                    in self.repo.git.diff('--name-only',
                                          f'{remote}/{branch}...{self.repo.active_branch}').split('\n')}

        # if remote does not exist we are checking against the commit sha1
        else:
            return {Path(os.path.join(item)) for item
                    in self.repo.git.diff('--name-only',
                                          f'{prev_ver}...{self.repo.active_branch}').split('\n')}

    def _only_last_commit(self, prev_ver: str, requested_status: str) -> Set:
        """Get all the files that were changed in the last commit of a given type when checking a branch against itself.
        Args:
            prev_ver (str): The base branch against which the comparison is made.
            requested_status (str): M, A, R, D - the git status to return
        Returns:
            Set: of Paths to files changed in the the last commit or an empty set if not
            running on master against master.
        """
        # when checking branch against itself only return the last commit.
        if self.get_current_working_branch() != prev_ver:
            return set()

        try:
            if requested_status != 'R':
                return {Path(os.path.join(item.a_path)) for item in
                        self.repo.commit('HEAD~1').diff().iter_change_type(requested_status) if item.score == 100}
            else:
                return {(Path(item.a_path), Path(item.b_path)) for item in
                        self.repo.commit('HEAD~1').diff().iter_change_type(requested_status)}
        except gitdb.exc.BadName:
            # in case no last commit exists - just pass
            pass

        return set()

    def check_if_remote_exists(self, remote):
        if '/' in remote:
            remote = remote.split('/')[0]

        return remote in self.repo.remotes

    def _handle_prev_ver(self, prev_ver):
        # check for sha1 in regex
        sha1_pattern = re.compile(r'\b[0-9a-f]{40}\b', flags=re.IGNORECASE)
        if sha1_pattern.match(prev_ver):
            return None, prev_ver

        if '/' in prev_ver:
            remote = prev_ver.split('/')[0]
            remote = remote if self.check_if_remote_exists(remote) else str(self.repo.remote())
            branch = prev_ver.split('/')[1]

        else:
            remote = str(self.repo.remote())
            branch = prev_ver

        return remote, branch

    def get_current_working_branch(self) -> str:
        return str(self.repo.active_branch)

    def git_path(self) -> str:
        git_path = self.repo.git.rev_parse('--show-toplevel')
        return git_path.replace('\n', '')

    def debug_print(self, debug: bool, status: str, staged: Set, committed: Set) -> None:
        if debug:
            click.echo(f'######## - {status} staged:')
            click.echo(staged)
            click.echo('\n')
            click.echo(f'######## - {status} committed:')
            click.echo(committed)
            click.echo('\n')

    def handle_wrong_renamed_status(self, status: str, remote: str, branch: str, staged_only: bool) -> Set[Path]:
        """Get all the files that are recognized as non-100% rename in a given file status.
        Args:
            status (str): the requested file status
            remote (str): the used git remote
            branch (str): the used git branch
            staged_only (bool): whether to bring only staged files
        Returns:
            Set: of Paths to non 100% renamed files which are of a given status.
        """
        if staged_only:
            return {Path(item.b_path) for item
                    in self.repo.head.commit.diff().iter_change_type('R') if item.score < 100 and
                    self._check_file_status(file_path=str(item.b_path), remote=remote, branch=branch) == status}

        if remote:
            return {Path(item.b_path) for item in self.repo.remote(name=remote).refs[branch].commit.diff(
                self.repo.active_branch).iter_change_type('R') if item.score < 100 and
                self._check_file_status(file_path=str(item.b_path), remote=remote, branch=branch) == status}

        # if remote does not exist we are checking against the commit sha1
        return {Path(item.b_path) for item in self.repo.commit(rev=branch).diff(
                self.repo.active_branch).iter_change_type('R') if item.score < 100 and
                self._check_file_status(file_path=str(item.b_path), remote=remote, branch=branch) == status}

    def _check_file_status(self, file_path: str, remote: str, branch: str) -> str:
        """Get the git status of a given file path
        Args:
            file_path (str): the file path to check
            remote (str): the used git remote
            branch (str): the used git branch
        Returns:
            str: the git status of the file (M, A, R, D).
        """
        if remote:
            diff_line = self.repo.git.diff('--name-status',
                                           f'{remote}/{branch}...{self.repo.active_branch}',
                                           '--', file_path)

        # if remote does not exist we are checking against the commit sha1
        else:
            diff_line = self.repo.git.diff('--name-status',
                                           f'{branch}...{self.repo.active_branch}',
                                           '--', file_path)

        if not diff_line:
            return ''

        return diff_line.split()[0].upper() if not diff_line.startswith('?') else 'A'

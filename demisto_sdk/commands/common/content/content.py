from __future__ import annotations

import os
from typing import Any, Dict, Iterator, Optional, Set, Tuple, Union

from demisto_sdk.commands.common.constants import (DOCUMENTATION,
                                                   DOCUMENTATION_DIR,
                                                   PACKS_DIR,
                                                   TEST_PLAYBOOKS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects.pack_objects.playbook.playbook import \
    Playbook
from demisto_sdk.commands.common.content.objects.pack_objects.script.script import \
    Script
from demisto_sdk.commands.common.content.objects.root_objects import (
    ContentDescriptor, Documentation)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import find_type
from git import GitCommandError, InvalidGitRepositoryError, Repo
from wcmatch.pathlib import Path


class Content:
    def __init__(self, path: Union[str, Path]):
        """ Content object.

        Args:
            path: Path to content.

       Notes:
            1. No validation to path validity.

        TODO:
            1. Add attribute which init only changed objects by git.
        """
        self._path = Path(path)

    @classmethod
    def from_cwd(cls) -> Content:
        """ Generate Content object from git or from current path.

        Notes:
            1. First try to get it from git -> If not succeed use current path.
            2. No validation to path validity.

        TODO:
            1. Add attribute which init only changed objects by git.
        """
        repo = cls.git()
        if repo:
            content = Content(repo.working_tree_dir)
        else:
            content = Content(Path.cwd())

        return content

    @staticmethod
    def git() -> Optional[Repo]:
        """ Git repository object.

        Returns:
            Repo: Repo object of content repo if exists else retun None.

        References:
            1. GitPython - https://github.com/gitpython-developers/GitPython

        Notes:
            1. Should be called when cwd inside content repository.
        """
        try:
            repo = Repo(Path.cwd(), search_parent_directories=True)
        except InvalidGitRepositoryError:
            repo = None

        return repo

    @property
    def path(self) -> Path:
        return self._path

    def _content_files_list_generator_factory(self, dir_name: str, prefix: str = "*", suffix: str = "*") -> Iterator[
            Any]:
        """Generic content objcets iterable generator

        Args:
            dir_name: Directory name, for example: Integrations, Documentations etc.
            prefix: file prefix to search for, if not supplied then any prefix.
            suffix: file suffix to search for, if not supplied then any suffix.

        Returns:
            object: Any valid content object found in the given directory.
        """
        objects_path = (self._path / dir_name).glob(patterns=[f"{prefix}*.{suffix}", f"*/*.{suffix}"])
        for object_path in objects_path:
            yield path_to_pack_object(object_path)

    @property
    def packs(self) -> Dict[str, Pack]:
        """Packs dictionary as follow:
            1. Key - Name.
            2. Value - Pack object.

        Notes:
            1. Could be accessed by Pack id.
            2. Itrate over all packs.
            3. Only Pack stripped object created not on demend, In order to allow access to pack by id.
        """
        return {path.name: Pack(path) for path in (self._path / PACKS_DIR).glob("*/")}

    @property
    def test_playbooks(self) -> Iterator[Union[Playbook, Script]]:
        """<content>/TestPlaybooks directory"""
        return self._content_files_list_generator_factory(dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix='yml')

    @property
    def documentations(self) -> Iterator[Documentation]:
        """<content>/Documentation directory"""
        return self._content_files_list_generator_factory(dir_name=DOCUMENTATION_DIR,
                                                          prefix=DOCUMENTATION,
                                                          suffix="json")

    @property
    def content_descriptor(self) -> Optional[ContentDescriptor]:
        """<content>/content-descriptor.json file"""
        descriptor_object = None
        path = self._path / 'content-descriptor.json'
        if path.exists():
            descriptor_object = ContentDescriptor(path)

        return descriptor_object

    def modified_packs(self, prev_ver='master', committed_only=False, staged_only=False) -> Dict[str, Pack]:
        content_repo: Repo = self.git()

        # staging all local changes
        self._stage_files(content_repo)

        committed_set = {Path(os.path.join(*Path(item.a_path).parts[:Path(item.a_path).parts.index('Packs') + 2]))
                         for item in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('M')}

        committed: Dict = {path.name: Pack(path) for path in committed_set}

        if committed_only:
            return committed

        staged_set = {Path(os.path.join(*Path(item.a_path).parts[:Path(item.a_path).parts.index('Packs') + 2])) for item
                      in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('M')}

        staged: Dict = {path.name: Pack(path) for path in staged_set}

        if staged_only:
            return staged

        staged.update(committed)

        return staged

    def added_packs(self, prev_ver='master', committed_only=False, staged_only=False) -> Dict[str, Pack]:
        content_repo: Repo = self.git()

        # staging all local changes
        self._stage_files(content_repo)

        committed_set = {Path(os.path.join(*Path(item.a_path).parts[:Path(item.a_path).parts.index('Packs') + 2]))
                         for item in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('A')}

        committed: Dict = {path.name: Pack(path) for path in committed_set}

        if committed_only:
            return committed

        staged_set = {Path(os.path.join(*Path(item.a_path).parts[:Path(item.a_path).parts.index('Packs') + 2])) for item
                      in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('A')}

        staged: Dict = {path.name: Pack(path) for path in staged_set}

        if staged_only:
            return staged

        staged.update(committed)

        return staged

    def modified_files(self, prev_ver='master', committed_only=False, staged_only=False,
                       no_auto_stage=False) -> Set[Path]:
        prev_ver = prev_ver.replace('origin/', '')
        content_repo: Repo = self.git()

        # staging all local changes
        if not no_auto_stage:
            self._stage_files(content_repo)

        renamed = {item[0] for item in self.renamed_files(prev_ver, committed_only, staged_only)}

        committed = {Path(os.path.join(item.a_path)) for item
                     in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('M')}

        all_branch_changed_files = {Path(os.path.join(item)) for item in
                                    content_repo.git.diff(f'{prev_ver}...HEAD', '--name-only').split('\n')}

        committed = committed.intersection(all_branch_changed_files)

        if committed_only:
            return committed - renamed

        staged = {Path(os.path.join(item.a_path)) for item
                  in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('M')}

        committed_added = {Path(os.path.join(item.a_path)) for item in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('A')}

        staged = staged - committed_added

        if staged_only:
            return staged - renamed

        return staged.union(committed) - renamed

    def added_files(self, prev_ver='master', committed_only=False, staged_only=False, no_auto_stage=False) -> Set[Path]:
        prev_ver = prev_ver.replace('origin/', '')
        content_repo: Repo = self.git()

        # staging all local changes
        if not no_auto_stage:
            self._stage_files(content_repo)

        committed = {Path(os.path.join(item.a_path)) for item
                     in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('A')}

        all_branch_changed_files = {Path(os.path.join(item)) for item in
                                    content_repo.git.diff(f'{prev_ver}...HEAD', '--name-only').split('\n')}

        committed = committed.intersection(all_branch_changed_files)

        if committed_only:
            return committed

        staged = {Path(os.path.join(item.a_path)) for item in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('A')}

        committed_added_locally_modified = {Path(os.path.join(item.a_path)) for item in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('M')}.intersection(committed)

        staged = staged.union(committed_added_locally_modified)

        if staged_only:
            return staged

        return staged.union(committed)

    def renamed_files(self, prev_ver='master', committed_only=False, staged_only=False,
                      no_auto_stage=False) -> Set[Tuple[Path, Path]]:
        prev_ver = prev_ver.replace('origin/', '')
        content_repo: Repo = self.git()

        # staging all local changes
        if not no_auto_stage:
            self._stage_files(content_repo)

        committed = {(Path(item.a_path), Path(item.b_path)) for item
                     in content_repo.remote().refs[prev_ver].commit.diff(
            content_repo.active_branch).iter_change_type('R')}

        all_branch_changed_files = {Path(os.path.join(item)) for item in
                                    content_repo.git.diff(f'{prev_ver}...HEAD', '--name-only').split('\n')}

        committed = {tuple_item for tuple_item in committed if tuple_item[1] in all_branch_changed_files}

        if committed_only:
            return committed

        staged = {(Path(item.a_path), Path(item.b_path)) for item
                  in content_repo.head.commit.diff(
            paths=list((Path().cwd() / 'Packs').glob('*/'))).iter_change_type('R')}

        if staged_only:
            return staged

        return staged.union(committed)

    def _stage_files(self, content_repo):
        git_status = content_repo.git.status('--short', '-u').split('\n')

        # in case there are no local changes - return
        if git_status == ['']:
            return

        all_paths = self._extract_existing_paths(git_status)
        for file_path in all_paths:
            if find_type(file_path):
                try:
                    content_repo.git.add(file_path)
                except GitCommandError:
                    continue

    @staticmethod
    def _extract_existing_paths(git_status):
        extracted_paths = []
        for line in git_status:
            extracted_paths.append(line.split()[-1])

        return extracted_paths

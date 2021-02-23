from __future__ import annotations

from typing import Any, Dict, Iterator, Optional, Union

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
from git import InvalidGitRepositoryError, Repo
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

from __future__ import annotations

from typing import Union, Tuple, Iterator, Dict, Optional
import git
from wcmatch.pathlib import Path
from demisto_sdk.commands.common.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.content import Playbook, ContentDescriptor, Documentation
from demisto_sdk.commands.common.content.pack import Pack
from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR, PACKS_DIR, DOCUMENTATION_DIR, DOCUMENTATION


class Content:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    @classmethod
    def from_cwd(cls) -> Content:
        return Content(cls.git().working_tree_dir)

    @staticmethod
    def git() -> git.Repo:
        return git.Repo(Path.cwd(),
                        search_parent_directories=True)

    @property
    def path(self) -> Path:
        return self._path

    def _content_dirs_dict_generator_factory(self, content_object, dir_name) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob("*/")
        for object_path in objects_path:
            yield object_path.name, content_object(object_path)

    def _content_files_list_generator_factory(self, dir_name, prefix: str = "*", suffix: str = "*") -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob(patterns=[f"{prefix}*.{suffix}", f"*/*.{suffix}"])
        for object_path in objects_path:
            yield ContentObjectFacotry.from_path(object_path)

    @property
    def packs(self) -> Dict[str, Pack]:
        return dict(self._content_dirs_dict_generator_factory(content_object=Pack,
                                                              dir_name=PACKS_DIR))

    @property
    def test_playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix='yml')

    @property
    def documentations(self) -> Iterator[Documentation]:
        return self._content_files_list_generator_factory(dir_name=DOCUMENTATION_DIR,
                                                          prefix=DOCUMENTATION,
                                                          suffix="json")

    @property
    def content_descriptor(self) -> Optional[ContentDescriptor]:
        descriptor_object = None
        path = self._path / 'content-descriptor.json'
        if path.exists():
            descriptor_object = ContentDescriptor(path)

        return descriptor_object

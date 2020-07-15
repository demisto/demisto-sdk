from __future__ import annotations

from typing import Union, Tuple, Generator, Iterator, Dict
import git
from wcmatch.pathlib import Path
from demisto_sdk.commands.common.content.pack import Pack
from objects import Playbook
from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR, PACKS_DIR


class Content:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    @staticmethod
    def from_cwd() -> Content:
        git_repo = git.Repo(Path.cwd(),
                            search_parent_directories=True)
        return Content(git_repo.working_tree_dir)

    @property
    def path(self) -> Path:
        return self._path

    def _content_dirs_dict_generator_factory(self, content_object, dir_name) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob("*/")
        for object_path in objects_path:
            yield object_path.name, content_object(object_path)

    def _content_files_list_generator_factory(self, content_object, dir_name, suffix: str) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).rglob(f"*.{suffix}")
        for object_path in objects_path:
            yield content_object(object_path)

    @property
    def packs(self) -> Dict[str, Pack]:
        return dict(self._content_dirs_dict_generator_factory(content_object=Pack,
                                                              dir_name=PACKS_DIR))

    @property
    def test_playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(content_object=Playbook,
                                                          dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix='yml')

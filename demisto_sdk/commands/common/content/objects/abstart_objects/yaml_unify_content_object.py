import copy
import os
import sys
from contextlib import contextmanager
from shutil import copyfile, move, copytree, rmtree
from typing import Union, Optional, Callable, List
from abc import abstractmethod

from wcmatch.pathlib import Path, EXTMATCH

from demisto_sdk.commands.common.content.objects.abstart_objects.yaml_content_object import YAMLConentObject
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.common.constants import FileType, SCRIPTS_DIR, INTEGRATIONS_DIR, TEST_PLAYBOOKS_DIR


class YAMLUnfiedObject(YAMLConentObject):
    def __init__(self, path: Union[Path, str], content_type: FileType, file_name_prefix: str):
        super().__init__(path, file_name_prefix)
        self._content_type = content_type

    @property
    def code_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}.@(ps1|js|py)"]
        return next(self._path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    @property
    def unittest_path(self) -> Optional[Path]:
        patterns = ["test_*.py", f"*_test.py"]
        return next(self._path.parent.glob(patterns=patterns))

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}.md"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def script(self):
        return {}

    def is_unify(self) -> bool:
        return self.code_path is None

    def unify(self, dest_dir) -> List[Path]:
        unify_dir = SCRIPTS_DIR if self._content_type == FileType.SCRIPT else INTEGRATIONS_DIR
        try:
            unifier = Unifier(input=str(self.path.parent), dir_name=unify_dir, output=dest_dir, force=True)
            unified_files_path: str = unifier.merge_script_package_to_yml()
        except Exception as e:
            raise BaseException(f"Unable to unify integration {self.path}, Full error: {e}")

        return [Path(path) for path in unified_files_path]

    def _split_yaml_4_5_0(self, dest_dir):
        unify_dir = SCRIPTS_DIR if self._content_type == FileType.SCRIPT else INTEGRATIONS_DIR
        try:
            unifier = Unifier(input=str(self.path.parent), dir_name=unify_dir, output=str(dest_dir / self.path.name),
                              force=True)
            yaml_dict = self.to_dict()
            yaml_dict_copy = copy.deepcopy(yaml_dict)
            script_object = self.script
            created_files = [Path(path) for path in
                             unifier.write_yaml_with_docker(yaml_dict_copy, yaml_dict, script_object).keys()]
        except Exception as e:
            raise BaseException(f"Unable to unify integration {self.path}, Full error: {e}")

        return created_files

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, change_log: Optional[bool] = True,
             readme: Optional[bool] = True, unify: bool = True):
        created_files = []
        if unify:
            self._create_target_dump_dir(dest_dir)
            if not self.is_unify():
                # Creating temp directory for unify
                temp_directory = self.path.parent / '.temp_content'
                copytree(src=self.path.parent,
                         dst=temp_directory,
                         dirs_exist_ok=True)
                # Serialize if changed
                if self._changed:
                    self._serialize(temp_directory)
                # Unify object
                created_files.extend(self.unify(dest_dir))
                # Temp change path
                rmtree(temp_directory)
            elif TEST_PLAYBOOKS_DIR not in self.path.parts:
                created_files.extend(self._split_yaml_4_5_0(dest_dir))
            else:
                # Copy it regularly
                created_files.extend(super().dump(dest_dir=dest_dir,
                                                  readme=readme))
        else:
            # Copy all folder structure
            created_files.extend(copytree(src=self.path.parent,
                                          dst=dest_dir,
                                          dirs_exist_ok=True))

        return created_files

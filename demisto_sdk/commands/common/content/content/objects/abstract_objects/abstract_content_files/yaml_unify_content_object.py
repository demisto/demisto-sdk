import copy
from shutil import copytree
from typing import Union, Optional, List
from abc import abstractmethod

from wcmatch.pathlib import Path, EXTMATCH
from .. import YAMLContentObject
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.common.constants import FileType, SCRIPTS_DIR, INTEGRATIONS_DIR


class YAMLUnfiedObject(YAMLContentObject):
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
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_image.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_description.md"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    @abstractmethod
    def script(self) -> dict:
        pass

    @property
    def docker_image(self) -> str:
        return self.script.get('dockerimage')

    @property
    def docker_image_4_5(self) -> str:
        return self.script.get('dockerimage45')

    def is_unify(self) -> bool:
        return self.code_path is None

    def unify(self, dest_dir) -> List[Path]:
        unify_dir = SCRIPTS_DIR if self._content_type == FileType.SCRIPT else INTEGRATIONS_DIR
        try:
            unifier = Unifier(input=str(self.path.parent), dir_name=unify_dir, output=dest_dir, force=True)
            unified_files_path: str = unifier.merge_script_package_to_yml()
        except Exception as e:
            raise BaseException(f"Unable to unify {self.path}, Full error: {e}")

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
            raise BaseException(f"Unable to Split to *_4_5.yml {self.path}, Full error: {e}")

        return created_files

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, change_log: Optional[bool] = False,
             readme: Optional[bool] = False, unify: bool = True):
        created_files = []
        dest_dir = self._create_target_dump_dir(dest_dir)
        if unify:
            if not self.is_unify():
                # Unify only if requested and
                created_files.extend(self.unify(dest_dir))
                created_files.extend(super().dump(dest_dir=dest_dir, yaml=False,
                                                  readme=readme, change_log=change_log))
            elif self.docker_image_4_5:
                # Try to split if dockerimages45 exists
                created_files.extend(self._split_yaml_4_5_0(dest_dir))
                created_files.extend(super().dump(dest_dir=dest_dir, yaml=False,
                                                  readme=readme, change_log=change_log))
            else:
                created_files.extend(super().dump(dest_dir=dest_dir, readme=readme,
                                                  change_log=change_log))
        else:
            # Copy all folder structure
            created_files.extend(copytree(src=self.path.parent,
                                          dst=dest_dir,
                                          dirs_exist_ok=True))

        return created_files

from typing import Optional, Union

from ruamel.yaml.scanner import ScannerError
from wcmatch.pathlib import EXTGLOB, NEGATE, Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.handlers import YAML_Handler

from .dictionary_based_object import DictionaryBasedObject

yaml = YAML_Handler(width=50000)


class YAMLObject(DictionaryBasedObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path=path, file_name_prefix=file_name_prefix)

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        """Find and validate object path is valid.

        Rules:
            1. Path exists.
            2. One of the following options:
                a. Path is a file.
                b. Path is directory and file with a yml/yaml suffix exists in the given directory.
            3. File suffix equal "yml" or "yaml".

        Returns:
            Path: valid file path.

        Raises:
            ContentInitializeError: If path not valid.
        """
        path = Path(path)
        if path.is_dir():
            try:
                path = next(path.glob(patterns=r'@(*.yml|*yaml|!*unified*)', flags=EXTGLOB | NEGATE))
            except StopIteration:
                raise exc.ContentInitializeError(path, path, "Can't find yaml or yml file in path (excluding unified).")
        elif not (path.is_file() and path.suffix in [".yaml", ".yml"]):
            raise exc.ContentInitializeError(path, path, "file suffix isn't yaml or yml.")

        return path

    def _deserialize(self):
        """Load yaml to dictionary"""
        try:
            self._as_dict = yaml.load(self.path)
        except ScannerError as e:
            raise exc.ContentSerializeError(self, self.path, e.problem)

    def _serialize(self, dest_dir: Path):
        """Dump dictionary to yml file
         """
        dest_file = self._create_target_dump_dir(dest_dir) / self.normalize_file_name()
        with open(dest_file, 'w') as file:
            yaml.dump(self._as_dict, file)
        return [dest_file]

    def dump(self, dest_dir: Optional[Union[Path, str]] = None):
        if self.modified:
            return self._serialize(dest_dir)
        else:
            return super().dump(dest_dir)

from __future__ import annotations

from shutil import copytree
from typing import AnyStr, Union

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.content.objects.base_objects.common import \
    DictBaseFileMixin
from ruamel.yaml import YAML
from wcmatch.pathlib import Path
from yaml.scanner import ScannerError

RUYAML = YAML(typ='rt')
RUYAML.preserve_quotes = True  # type: ignore
RUYAML.width = 50000  # type: ignore


class YamlFile(DictBaseFileMixin):
    def __init__(self, path: Union[Path, str], prefix: str = ''):
        self._path = Path(path)
        self._prefix = prefix
        self._loaded_data: Union[AnyStr, dict, list] = None
        self._data_changed: bool = False

    def _serialize(self, dest_file: Path) -> Path:
        """Load json to dictionary"""
        try:
            if self._data_changed:
                with dest_file.open("w", encoding='utf-8') as file:
                    RUYAML.dump(self._unserialize(),
                                stream=file)
            else:
                copytree(self.path, dest_file)
        except Exception as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

        return dest_file

    def _unserialize(self):
        """Load json to dictionary"""
        if not self._loaded_data:
            try:
                self._loaded_data = RUYAML.load(self.path)
            except ScannerError as e:
                raise exc.ContentSerializeError(self, self.path, e.problem)

        return self._loaded_data

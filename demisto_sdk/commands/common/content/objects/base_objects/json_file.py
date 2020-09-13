from __future__ import annotations

from shutil import copytree
from typing import AnyStr, Union

import demisto_sdk.commands.common.content.errors as exc
import ujson
from demisto_sdk.commands.common.content.objects.base_objects.common import \
    DictBaseFileMixin
from wcmatch.pathlib import Path


class JsonFile(DictBaseFileMixin):
    def __init__(self, path: Union[Path, str], prefix: str = ''):
        self._path = Path(path)
        self._prefix = prefix
        self._loaded_data: Union[AnyStr, dict, list] = None
        self._data_changed: bool = False

    def _serialize(self, dest_file: Path) -> Path:
        """Load json to dictionary"""
        try:
            if self._data_changed:
                with dest_file.open("w") as file:
                    ujson.dumps(self._unserialize(),
                                file,
                                indent=4,
                                encode_html_chars=True,
                                escape_forward_slashes=False,
                                ensure_ascii=False)
            else:
                copytree(self.path, dest_file)
        except Exception as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

        return dest_file

    def _unserialize(self):
        """Load json to dictionary"""
        if not self._loaded_data:
            try:
                self._loaded_data = ujson.load(self._path.open())
            except Exception as e:
                raise exc.ContentSerializeError(self, self.path, str(e))

        return self._loaded_data

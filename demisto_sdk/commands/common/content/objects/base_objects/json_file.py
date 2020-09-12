from __future__ import annotations

from typing import Union, AnyStr
import ujson
from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc


class JsonFile:
    def __init__(self, path: Union[Path, str], prefix: str = ''):
        self._path = Path(path)
        self._prefix = prefix
        self._loaded_data: Union[AnyStr, dict, list] = None

    def _serialize(self: Union[JsonFile, DictBaseFileMixin], dest_file: Path) -> Path:
        """Load json to dictionary"""
        try:
            with dest_file.open("w") as file:
                ujson.dumps(self._unserialize(),
                            file,
                            indent=4,
                            encode_html_chars=True,
                            escape_forward_slashes=False,
                            ensure_ascii=False)
        except Exception as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

        return dest_file

    def _unserialize(self: Union[JsonFile, DictBaseFileMixin]):
        """Load json to dictionary"""
        if not self._loaded_data:
            try:
                self._loaded_data = ujson.load(self._path.open())
            except Exception as e:
                raise exc.ContentSerializeError(self, self.path, str(e))

        return self._loaded_data




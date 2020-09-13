from shutil import copytree
from typing import Optional, Union

import demisto_sdk.commands.common.content.errors as exc
from wcmatch.pathlib import Path


class BytesFile:
    def __init__(self, path: Union[Path, str], prefix: str = ''):
        self._path = Path(path)
        self._prefix = prefix
        self._loaded_data: Optional[bytes] = None
        self._data_changed: bool = False

    @property
    def path(self):
        return self._path

    def _serialize(self, dest_file: Path):
        try:
            if self._data_changed:
                dest_file.write_bytes(self._unserialize())
            else:
                copytree(self.path, dest_file)
        except Exception as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

    def _unserialize(self):
        if not self._loaded_data:
            try:
                self.path.read_bytes()
            except Exception as e:
                raise exc.ContentSerializeError(self, self.path, str(e))

        return self._loaded_data

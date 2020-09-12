from typing import Union, Optional

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc


class BytesFile:
    def __init__(self, path: Union[Path, str], prefix: str = ''):
        self._path = Path(path)
        self._prefix = prefix
        self._loaded_data: Optional[bytes] = None

    @property
    def path(self):
        return self._path

    def _serialize(self, dest_file: Path):
        try:
            dest_file.write_bytes(self._unserialize())
        except Exception as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

    def _unserialize(self):
        if not self._loaded_data:
            try:
                self.path.read_bytes()
            except Exception as e:
                raise exc.ContentSerializeError(self, self.path, str(e))

        return self._loaded_data




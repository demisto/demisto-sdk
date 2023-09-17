from typing import Optional, Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.tools import (
    get_file,
    write_dict,
)

from .dictionary_based_object import DictionaryBasedObject


class JSONObject(DictionaryBasedObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path=path, file_name_prefix=file_name_prefix)

    @staticmethod
    def _fix_path(path: Union[Path, str]) -> Path:
        """Find and validate object path is valid.

        Rules:
            1. Path exists.
            2. One of the following options:
                a. Path is a file.
                b. Path is directory and file with a json suffix exists in the given directory.
            3. File suffix equal ".json".

        Returns:
            Path: valid file path.

        Raises:
            ContentInitializeError: If path not valid.
        """
        path = Path(path)  # type: ignore
        if path.is_dir():
            try:
                path = next(path.glob(["*.json"]))  # type: ignore
            except StopIteration:
                raise exc.ContentInitializeError(JSONObject, path)
        elif (
            not (path.is_file() and path.suffix in [".json"])
            and path.name != "metadata.json"
        ):
            raise exc.ContentInitializeError(JSONObject, path)

        return path

    def _deserialize(self) -> None:
        """Load json to dictionary"""
        try:
            self._as_dict = get_file(self._path, raise_on_error=True)
        except ValueError as e:
            raise exc.ContentSerializeError(self, self.path, str(e))

    def _serialize(self, dest_dir: Path):
        """Dump dictionary to json file"""
        dest_file = self._create_target_dump_dir(dest_dir) / self.normalize_file_name()
        write_dict(dest_file, data=self.to_dict())
        return [dest_file]

    def dump(self, dest_dir: Optional[Union[Path, str]] = None):
        if self.modified:
            return self._serialize(dest_dir)  # type: ignore
        else:
            return super().dump(dest_dir)

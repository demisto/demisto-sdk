from typing import List, Optional, Union

from demisto_sdk.commands.common.content.objects.base_objects import TextObject
from wcmatch.pathlib import Path


class SecretIgnore:
    def __init__(self, path: Union[Path, str]):
        self._object_type = TextObject(path)

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "<prefix>-hello-world.yml"

        Returns:
            str: Normalize file name.
        """
        return self._object_type.normalize_file_name()

    @property
    def path(self) -> Path:
        return self._object_type.path

    def to_str(self):
        """File content as string.

        Returns:
            str: file content.
        """
        return self._object_type.to_str()

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Dump unmodified object.

        Args:
            dest_dir: destination directory to dump object

        Returns:
            List[Path]: List of path created in given directory.
        """
        return self._object_type.dump(dest_dir)

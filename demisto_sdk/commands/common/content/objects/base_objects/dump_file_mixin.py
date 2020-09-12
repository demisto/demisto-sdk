from typing import Union, Optional, List

from wcmatch.pathlib import Path

from ..utils import normalize_file_name
from demisto_sdk.commands.common.content.objects.base_objects.bytes_file import BytesFile
from demisto_sdk.commands.common.content.objects.base_objects.json_file import JsonFile
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import YamlFile


class FileDumpMixin:
    def dump(self: Union[JsonFile, YamlFile, BytesFile], dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Dump unmodified object.

        Args:
            dest_dir: destination directory to dump object

        Returns:
            List[Path]: List of path created in given directory.
        """
        created_files: List[Path] = []
        if not dest_dir:
            dest_dir = self.path
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_dir /= normalize_file_name(file_name=self.path.name, file_prefix=self._prefix)

        created_files.append(self._serialize(dest_dir))

        return created_files

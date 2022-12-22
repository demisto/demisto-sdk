import shutil
from typing import List, Optional, Union

import demisto_client
from packaging.version import Version
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import XSIAM_LAYOUT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class XSIAMLayout(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.XSIAM_LAYOUT)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, XSIAM_LAYOUT)

    def upload(self, client: demisto_client):
        """
        Upload the xsiam_layout to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_parsing_rules(file=self.path)
        pass

    def type(self):
        return FileType.XSIAM_LAYOUT

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        created_files: List[Path] = []
        created_files.extend(super().dump(dest_dir=dest_dir))

        new_file_path = created_files[0]

        # export XSIAM 1.3 items only with the external prefix
        if not new_file_path.name.startswith('external-'):
            move_to_path = new_file_path.parent / self.normalize_file_name()
            shutil.move(new_file_path.as_posix(), move_to_path)
            created_files.remove(new_file_path)
            created_files.append(move_to_path)

        return created_files

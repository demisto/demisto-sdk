import shutil
from typing import List, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import TRIGGER, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class Trigger(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, TRIGGER)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, TRIGGER)

    def upload(self, client: demisto_client):
        """
        Upload the trigger to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_triggers(file=self.path)
        pass

    def type(self):
        return FileType.TRIGGER

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        created_files: List[Path] = []
        created_files.extend(super().dump(dest_dir=dest_dir))
        new_file_path = created_files[0]
        if new_file_path.name.startswith('external-'):
            copy_to_path = str(new_file_path).replace('external-', '')
        else:
            copy_to_path = f'{new_file_path.parent}/{self.normalize_file_name()}'
        shutil.copyfile(new_file_path, copy_to_path)
        return created_files

import shutil
from typing import List, Optional, Union

import demisto_client
from packaging.version import Version
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import TRIGGER, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
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
        # after XSIAM 1.2 is obsolete, we can clear this block and only export the file with the `external-` prefix.
        # Issue: CIAC-4349

        created_files: List[Path] = []
        created_files.extend(super().dump(dest_dir=dest_dir))
        new_file_path = created_files[0]

        if Version(self.get("fromVersion", "0.0.0")) >= Version("6.10.0"):
            # export XSIAM 1.3 items only with the external prefix
            if not new_file_path.name.startswith("external-"):
                move_to_path = new_file_path.parent / self.normalize_file_name()
                shutil.move(new_file_path.as_posix(), move_to_path)
                created_files.remove(new_file_path)
                created_files.append(move_to_path)

        elif Version(self.get("toVersion", "99.99.99")) < Version("6.10.0"):
            # export XSIAM 1.2 items only without the external prefix
            if new_file_path.name.startswith("external-"):
                move_to_path = Path(str(new_file_path).replace("external-", ""))
                shutil.move(new_file_path.as_posix(), move_to_path)
                created_files.remove(new_file_path)
                created_files.append(move_to_path)

        else:
            # export 2 versions of the file, with/without the external prefix.
            if new_file_path.name.startswith("external-"):
                copy_to_path = str(new_file_path).replace("external-", "")
            else:
                copy_to_path = f"{new_file_path.parent}/{self.normalize_file_name()}"

            shutil.copyfile(new_file_path, copy_to_path)

        return created_files

import shutil
from typing import List, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import XSIAM_REPORT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class XSIAMReport(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, XSIAM_REPORT)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, XSIAM_REPORT)

    def upload(self, client: demisto_client):
        """
        Upload the xsiam_report to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_xsiam_reports(file=self.path)
        pass

    def type(self):
        return FileType.XSIAM_REPORT

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        created_files: List[Path] = []
        created_files.extend(super().dump(dest_dir=dest_dir))
        new_file_path = str(created_files[0])
        shutil.copyfile(new_file_path, new_file_path.replace('external-', ''))
        return created_files

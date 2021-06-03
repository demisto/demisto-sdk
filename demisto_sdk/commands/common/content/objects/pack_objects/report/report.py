from typing import Union

from demisto_sdk.commands.common.constants import REPORT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import SCRIPT, FileType
from wcmatch.pathlib import Path

class Report(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, REPORT)

    def type(self):
        return FileType.REPORT

    def upload(self, client: demisto_client):
        """
        Upload the report to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.upload_report(file=self.path)



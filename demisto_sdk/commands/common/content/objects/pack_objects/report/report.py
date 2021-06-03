from typing import Union

from demisto_sdk.commands.common.constants import REPORT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path

import tempfile
from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import SCRIPT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.tools import get_demisto_version
from packaging.version import parse
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
        return client.import_widget(file=self.path)



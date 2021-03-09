from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import PLAYBOOK, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class Playbook(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, PLAYBOOK)

    def upload(self, client: demisto_client):
        """
        Upload the playbook to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_playbook(file=self.path)

    def type(self):
        return FileType.PLAYBOOK

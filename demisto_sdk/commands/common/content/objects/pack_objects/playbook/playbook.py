import demisto_client
from typing import Union

from demisto_sdk.commands.common.constants import PLAYBOOK, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path
from demisto_sdk.commands.common.tools import unlock_entity


class Playbook(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, PLAYBOOK)

    def upload(self, client: demisto_client, override: bool = False):
        """
        Upload the playbook to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.
            override: Whether to unlock the playbook if it is a locked system playbook.

        Returns:
            The result of the upload command from demisto_client
        """
        try:
            return client.import_playbook(file=self.file)
        except Exception as e:
            if 'Item is system' in e.body and override:
                playbook_id = self.__getitem__('id')
                unlock_entity(client, FileType.PLAYBOOK, playbook_id)
                return client.import_playbook(file=self.file)
            else:
                raise

        return client.import_playbook(file=self.path)

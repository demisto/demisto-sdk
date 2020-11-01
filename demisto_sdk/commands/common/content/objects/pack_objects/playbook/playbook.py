from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import PLAYBOOK, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from demisto_sdk.commands.common.tools import unlock_entity
from wcmatch.pathlib import Path


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
            return client.import_playbook(file=self.path)
        except Exception as e:
            if ('Can not override system playbook yaml' in e.body or 'already exists' in e.body) and override:  # type: ignore
                playbook_id = self.__getitem__('id')
                unlock_entity(client, FileType.PLAYBOOK, playbook_id)
                return client.import_playbook(file=self.path)
            else:
                raise

        return client.import_playbook(file=self.path)

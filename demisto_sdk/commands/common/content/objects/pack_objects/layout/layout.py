from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import (LAYOUT, LAYOUTS_CONTAINER,
                                                   FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class Layout(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, LAYOUT)

    def upload(self, client: demisto_client):
        return client.import_layout(file=self.path)

    def type(self):
        return FileType.LAYOUT


class LayoutsContainer(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, LAYOUTS_CONTAINER)

    def upload(self, client: demisto_client):
        """
        Upload the Layouts Container to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_layout(file=self.path)

    def type(self):
        return FileType.LAYOUTS_CONTAINER

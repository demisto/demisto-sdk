from abc import abstractmethod
from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from typing import Optional


class LayoutObject(JSONContentObject):
    def __init__(self, path: Union[Path, str], layout_type: FileType):
        self.layout_type = layout_type
        super().__init__(path, layout_type.value)

    def upload(self, client: demisto_client):
        """
        Upload the Layout object to demisto_client.
        Args:
            client (demisto_client): The Demisto client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client.
        """
        return client.import_layout(file=self.path)

    @abstractmethod
    def get_layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        Returns:
            (str): ID of the layout.
        """
        pass

    def type(self) -> FileType:
        return self.layout_type


class Layout(LayoutObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.LAYOUT)

    def get_layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        In layouts of versions below 6.0.0, the ID field resides inside layout field.
        Returns:
            (str): ID of the layout.
        """
        return self.get('layout', dict()).get('id')


class LayoutsContainer(LayoutObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.LAYOUTS_CONTAINER)

    def get_layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        In layouts of versions 6.0.0 and above, the ID field is a simple 'id' entry in the layout fields.
        Returns:
            (str): ID of the layout.
        """
        return self.get('id')

import tempfile
from abc import abstractmethod
from typing import List, Optional, Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)


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
        if self.layout_type == FileType.LAYOUTS_CONTAINER:
            with tempfile.TemporaryDirectory() as _dir:
                return client.import_layout(file=self._unify(_dir)[0])

        return client.import_layout(file=self.path)

    @abstractmethod
    def layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        Returns:
            (str): ID of the layout.
        """
        pass

    @abstractmethod
    def get_layout_sections(self) -> Optional[List]:
        """
        Returns the layout sections of the given layout.
        Returns:
            (Optional[List]): Sections of layout if exists.
        """
        pass

    @abstractmethod
    def get_layout_tabs(self) -> Optional[List]:
        """
        Returns the layout tabs of the given layout.
        Returns:
            (Optional[List]): Sections of tabs if exists.
        """
        pass

    def type(self) -> FileType:
        return self.layout_type


class Layout(LayoutObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.LAYOUT)

    def layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        In layouts of versions below 6.0.0, the ID field resides inside layout field.
        Returns:
            (Optional[str]): ID of the layout.
        """
        return self.get("layout", dict()).get("id")

    def get_layout_sections(self) -> Optional[List]:
        """
        Returns the layout sections of the given layout.
        In layouts of versions below 6.0.0, the sections field resides inside layout field.
        Returns:
            (Optional[List]): Sections of the layout if exists.
        """
        return self.get("layout", dict()).get("sections")

    def get_layout_tabs(self) -> Optional[List]:
        """
        Returns the layout tabs of the given layout.
        In layouts of versions below 6.0.0, the tabs field resides inside layout field.
        Returns:
            (Optional[List]): Tabs of the layout if exists.
        """
        return self.get("layout", dict()).get("tabs")


class LayoutsContainer(LayoutObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.LAYOUTS_CONTAINER)

    def layout_id(self) -> Optional[str]:
        """
        Returns the layout ID of the given layout.
        In layouts of versions 6.0.0 and above, the ID field is a simple 'id' entry in the layout fields.
        Returns:
            (str): ID of the layout.
        """
        return self.get("id")

    def get_layout_sections(self) -> Optional[List]:
        """
        Returns the layout sections of the given layout.
        In layouts of versions 6.0.0 and above, the ID field is a simple 'sections' entry in the layout fields.
        Returns:
            (Optional[List]): ID of the layout.
        """
        return self.get("sections")

    def get_layout_tabs(self) -> Optional[List]:
        """
        Returns the layout tabs of the given layout.
        In layouts of versions 6.0.0 and above, the ID field is a simple 'tabs' entry in the layout fields.
        Returns:
            (Optional[List]): ID of the layout.
        """
        return self.get("tabs")

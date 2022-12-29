import pprint
from typing import Union

from demisto_client.demisto_api import DefaultApi
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import LISTS, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


class Lists(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, LISTS)

    def upload(self, client: DefaultApi):
        """
        Upload the lists item to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        response = client.generic_request(
            method="POST",
            path="lists/save",
            body=self.to_dict(),
            response_type="object",
        )[0]

        return pprint.pformat(response)

    def type(self):
        return FileType.LISTS

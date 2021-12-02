from pathlib import Path
from typing import Union

from demisto_client.demisto_api import DefaultApi

from demisto_sdk.commands.common.constants import JOB, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject


class Job(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, JOB)

    def upload(self, client: DefaultApi):
        """
        Upload the job item to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.
        Returns:
            The result of the upload command from demisto_client
        """
        return client.generic_request(
            method='POST',
            path='jobs/import',
            files={'file': str(self.path)},
            content_type='multipart/form-data'
        )

    def type(self):
        return FileType.JOB

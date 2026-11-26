from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)

JOB_CENTER = "jobcenter"


class JobCenter(YAMLContentObject):
    """Legacy content object for an AgentiX Job Center job."""

    def __init__(self, path: Union[Path, str]):
        super().__init__(path, JOB_CENTER)

    def upload(self, client: demisto_client):
        """No-op: Job Center jobs are uploaded via the content-graph pack zip flow."""
        pass

    def type(self):
        return FileType.JOB_CENTER

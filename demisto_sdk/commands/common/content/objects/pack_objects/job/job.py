import tempfile
from typing import Optional, Union

import demisto_client
from packaging.version import parse
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import JOB, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import get_demisto_version


class Job(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, JOB)

    def upload(self, client: demisto_client):
        # return client.job_upload() # todo
        raise NotImplementedError()

    def download(self, client: demisto_client):
        # return demisto_client.download_job('??') # todo
        raise NotImplementedError()

    def type(self):
        return FileType.JOB


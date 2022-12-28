import tempfile
from typing import Union

import demisto_client
from packaging.version import parse
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import SCRIPT, TEST_PLAYBOOKS_DIR, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.tools import get_demisto_version


class Script(YAMLContentUnifiedObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.SCRIPT, SCRIPT)

    def upload(self, client: demisto_client):
        """
        Upload the integration to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if self.is_unify():
            return client.import_script(file=self.path)
        else:
            with tempfile.TemporaryDirectory() as dir:
                unified_files = self._unify(dir)
                for file in unified_files:
                    if (str(file)[-7:] == "_45.yml") == (
                        get_demisto_version(client) < parse("4.6.0")
                    ):
                        # The above condition checks that the file ends in `_45.yml' and the version is 4.5 or less
                        # or that the file doesn't end in `_45.yml` and the version is higher than 4.5
                        return client.import_script(file=file)

    def type(self):
        if TEST_PLAYBOOKS_DIR in self.path.parts:
            return FileType.TEST_SCRIPT

        return FileType.SCRIPT

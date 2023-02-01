from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)

PRE_PROCESS_RULES_PREFIX = "preprocessrule"


class PreProcessRule(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, PRE_PROCESS_RULES_PREFIX)

    def upload(self, client: demisto_client):
        """
        Upload the pre_process_rules to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_pre_process_rules(file=self.path)
        pass

    def type(self):
        return FileType.PRE_PROCESS_RULES

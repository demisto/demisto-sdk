from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import CORRELATION_RULE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject


class CorrelationRule(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CORRELATION_RULE)

    def upload(self, client: demisto_client):
        """
        Upload the correlation_rule to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # return client.import_correlation_rules(file=self.path)
        pass

    def type(self):
        return FileType.CORRELATION_RULE

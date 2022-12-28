from tempfile import NamedTemporaryFile
from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (
    INDICATOR_TYPE,
    OLD_INDICATOR_TYPE,
    FileType,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


class IndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_TYPE)

    def upload(self, client: demisto_client):
        """
        Upload the incident type Container to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if isinstance(self._as_dict, dict):
            indicator_type_unified_data = [self._as_dict]
        else:
            indicator_type_unified_data = self._as_dict

        with NamedTemporaryFile(suffix=".json") as indicator_type_unified_file:
            indicator_type_unified_file.write(
                bytes(json.dumps(indicator_type_unified_data), "utf-8")
            )
            indicator_type_unified_file.seek(0)
            return client.import_reputation_handler(
                file=indicator_type_unified_file.name
            )

    def type(self):
        return FileType.REPUTATION


class OldIndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, OLD_INDICATOR_TYPE)

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "reputations.json"
            2. "reputations.json" -> "reputations.json"

        Returns:
            str: Normalize file name.
        """
        return "reputations.json"

    def type(self):
        return FileType.REPUTATION

from pathlib import Path
from typing import Callable, Optional

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Mapper(ContentItem, content_type=ContentType.MAPPER):  # type: ignore[call-arg]
    type: Optional[str]
    version: Optional[int] = 0

    definition_id: Optional[str] = Field(
        alias="definitionId"
    )  # TODO decide if this should be optional or not

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_classifier

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            ("transformer" in _dict and "keyTypeMap" in _dict)
            or "mapping" in _dict
            and path.suffix == ".json"
        ):
            if (
                not (_dict.get("type") and _dict.get("type") == "classification")
                and _dict.get("type")
                and "mapping" in _dict.get("type", {})
            ):
                return True
        return False

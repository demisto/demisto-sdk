from pathlib import Path
from typing import Callable, Optional

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Classifier(ContentItem, content_type=ContentType.CLASSIFIER):  # type: ignore[call-arg]
    type: Optional[str]
    definition_id: Optional[str] = Field(alias="definitionId")
    version: Optional[int] = 0

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_classifier

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if ("transformer" in _dict and "keyTypeMap" in _dict) or "mapping" in _dict:
            if (
                _dict.get("type")
                and _dict.get("type") == "classification"
                and path.suffix == ".json"
            ):
                return True
        return False

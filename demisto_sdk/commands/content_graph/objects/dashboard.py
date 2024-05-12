from pathlib import Path
from typing import Callable, Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Dashboard(ContentItem, content_type=ContentType.DASHBOARD):  # type: ignore[call-arg]
    version: Optional[int] = 0
    data_dict: dict = Field({}, exclude=True)
    layout: list = Field([], exclude=True)

    def metadata_fields(self) -> Set[str]:
        return {"object_id", "name", "fromversion", "toversion", "deprecated"}

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_dashboard

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            ("layout" in _dict or "kind" in _dict)
            and "typeId" not in _dict
            and "color" not in _dict
            and "regex" not in _dict
            and path.suffix == ".json"
        ):
            return True
        return False

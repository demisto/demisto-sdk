from typing import Callable, Optional

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Mapper(ContentItem, content_type=ContentType.MAPPER):  # type: ignore[call-arg]
    type: Optional[str]
    definition_id: Optional[str] = Field(
        alias="definitionId"
    )  # TODO decide if this should be optional or not

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_classifier

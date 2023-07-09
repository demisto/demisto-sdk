from typing import Callable, Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Classifier(ContentItem, content_type=ContentType.CLASSIFIER):  # type: ignore[call-arg]
    type: Optional[str]
    definition_id: Optional[str] = Field(alias="definitionId")

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_classifier

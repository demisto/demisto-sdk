from typing import List, Optional, Set

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GenericModule(ContentItem, content_type=ContentType.GENERIC_MODULE):  # type: ignore[call-arg]
    definition_ids: Optional[List[str]] = Field(alias="definitionIds")

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

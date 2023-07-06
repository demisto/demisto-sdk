from typing import Optional

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
    UnknownContent,
    content_type_to_model,
)
from demisto_sdk.commands.content_graph.objects.pack import PackContentItems
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO


class RelationshipData(BaseModel):
    relationship_type: RelationshipType

    # These are the database ids of the relationships
    source_id: int
    target_id: int

    # this is the attribute we're interested in when querying
    content_item_to: BaseContent

    is_direct: bool = True

    # USES, DEPENDS_ON relationship properties
    mandatorily: bool = False

    # DEPENDS_ON relationship properties
    is_test: bool = False

    # HAS_COMMAND relationship properties
    description: Optional[str] = None
    deprecated: bool = False

    def __hash__(self):
        """This is the unique identifier of the relationship"""

        return hash(
            (
                self.source_id,
                self.target_id,
                self.relationship_type,
            )
        )

    def __eq__(self, __o: object) -> bool:
        """This is needed to check if the relationship already exists"""
        return hash(self) == hash(__o)


# we need to rebuild the models, as the relationship model is not known at the time of the first build
PackContentItems.model_rebuild()
BaseContent.model_rebuild()
UnknownContent.model_rebuild()
ContentDTO.model_rebuild()
for content_type in ContentType:
    if model := content_type_to_model.get(content_type):
        model.model_rebuild()

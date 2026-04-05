from typing import Optional

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseNode


class RelationshipData(BaseModel):
    relationship_type: RelationshipType

    # These are the database ids of the relationships
    source_id: str
    target_id: str

    # this is the attribute we're interested in when querying
    content_item_to: BaseNode

    is_direct: bool = True

    # USES, DEPENDS_ON relationship properties
    mandatorily: bool = False

    # DEPENDS_ON relationship properties
    is_test: bool = False
    target_min_version: Optional[str] = None

    # HAS_COMMAND relationship properties
    description: Optional[str] = None
    deprecated: bool = False
    supportedModules: Optional[list[str]] = []

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


# Rebuild BaseNode and all its subclasses now that RelationshipData is defined,
# resolving the forward reference.
# This is needed for pydantic v2 which requires forward references to be resolved before model use.
BaseNode.model_rebuild()

# UnknownContent is a subclass of BaseNode defined in base_content.py and also
# needs rebuilding since it inherits the RelationshipData forward reference.
from demisto_sdk.commands.content_graph.objects.base_content import (  # noqa: E402
    BaseContent,
    UnknownContent,
)

BaseContent.model_rebuild()
UnknownContent.model_rebuild()

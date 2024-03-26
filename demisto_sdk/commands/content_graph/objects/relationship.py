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

from typing import Optional

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class RelationshipData(BaseModel):
    relationship_type: RelationshipType
    source: BaseContent
    target: BaseContent

    # this is the attribute we're interested in when querying
    content_item: BaseContent

    is_direct: bool = True

    # USES, DEPENDS_ON relationship properties
    mandatorily: bool = False

    # HAS_COMMAND relationship properties
    description: Optional[str] = None
    deprecated: bool = False

    def __hash__(self):
        """This is the unique identifier of the relationship"""

        return hash(
            (
                self.source.database_id,
                self.target.database_id,
                self.relationship_type,
                self.source.content_type,
                self.target.content_type,
            )
        )

    def __eq__(self, __o: object) -> bool:
        """This is needed to check if the relationship already exists"""
        return hash(self) == hash(__o)

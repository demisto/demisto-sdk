from typing import Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Command


class RelationshipData(BaseModel):
    relationship_type: RelationshipType
    source: Union[BaseContent, Command]
    target: Union[BaseContent, Command]

    # this is the attribute we're interested in when querying
    content_item: Union[BaseContent, Command]

    is_direct: bool = True

    # USES, DEPENDS_ON relationship properties
    mandatorily: bool = False

    # HAS_COMMAND relationship properties
    description: Optional[str] = None
    deprecated: bool = False

    def __hash__(self):
        """This is the unique identifier of the relationship"""
        return hash(
            (self.source.object_id, self.target.object_id, self.relationship_type,
             self.source.content_type, self.target.content_type)
        )

    def __eq__(self, __o: object) -> bool:
        """This is needed to check if the relationship already exists"""
        return hash(self) == hash(__o)

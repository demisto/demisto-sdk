from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    # pydantic dataclass uses the same API as the official dataclass
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Command


@dataclass
class RelationshipData:
    relationship_type: RelationshipType
    source: Union[BaseContent, Command]
    target: Union[BaseContent, Command]

    related_to: Union[BaseContent, Command]
    is_direct: bool = True

    mandatorily: bool = False

    # HAS_COMMAND relationship properties
    description: Optional[str] = None
    deprecated: bool = False

    def __hash__(self):
        return hash(
            (self.source.object_id, self.target.object_id, self.relationship_type)
        )

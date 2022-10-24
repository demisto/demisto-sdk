from typing import Optional, Union

from pydantic.dataclasses import dataclass

from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import BaseCommand


@dataclass
class RelationshipData:
    relationship_type: RelationshipType
    source = Union[BaseContent, BaseCommand]
    target = Union[BaseContent, BaseCommand]

    related_to: Union[BaseContent, BaseCommand]
    is_nested: bool = False

    mandatorily: bool = False
    description: Optional[str] = None
    deprecated: bool = False

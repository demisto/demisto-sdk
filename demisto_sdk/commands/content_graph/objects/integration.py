from typing import List
from uuid import uuid4

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class BaseCommand(BaseModel):
    name: str
    element_id: int = Field(default_factory=uuid4)

    class Config:
        orm_mode = True


class Command(BaseCommand):
    name: str
    deprecated: bool = False
    description: str


class Integration(IntegrationScript, content_type=ContentType.INTEGRATION):
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_feed: bool = False
    category: str

    @property
    def commands(self):
        return [
            Command(
                # the related to has to be a command
                name=r.related_to.name,  # type: ignore[union-attr]
                deprecated=r.deprecated,
                description=r.description,
            )
            for r in self.relationshipss
            if not r.is_nested and r.relationship_type == RelationshipType.HAS_COMMAND
        ]

    def included_in_metadata(self):
        return {"name", "description", "category", "commands"}

    def summary(self) -> dict:
        summary = super().summary()
        summary["commands"] = [{"name": command.name, "description": command.description} for command in self.commands]
        return summary

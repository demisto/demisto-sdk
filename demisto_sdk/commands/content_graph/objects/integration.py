from typing import TYPE_CHECKING, List, Optional, Set

if TYPE_CHECKING:
    # avoid circular imports
    from demisto_sdk.commands.content_graph.objects.script import Script
    from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData

from pydantic import BaseModel, Field, validator

from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.objects.integration_script import \
    IntegrationScript


class BaseCommand(BaseModel):
    name: str
    object_id: str = ""  # objects sets up in the validator
    relationships_data: Set["RelationshipData"] = Field(
        set(), exclude=True, repr=False
    )  # too much data in the repr

    @validator("object_id", always=True)
    def validate_object_id(cls, v, values):
        return values["name"]

    class Config:
        orm_mode = True


class Command(BaseCommand):
    name: str
    deprecated: bool = False
    description: str


class Integration(IntegrationScript, content_type=ContentType.INTEGRATION):  # type: ignore[call-arg]
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_feed: bool = False
    category: str
    commands: List[Command] = Field([], exclude=True)

    @property
    def imports(self) -> Optional["Script"]:
        for r in self.relationships_data:
            if r.relationship_type == RelationshipType.IMPORTS:
                return r.related_to  # type: ignore[return-value]
        return None

    def set_commands(self):
        commands = [
            Command(
                # the related to has to be a command
                name=r.related_to.name,  # type: ignore[union-attr]
                deprecated=r.deprecated,
                description=r.description,
            )
            for r in self.relationships_data
            if not r.is_nested and r.relationship_type == RelationshipType.HAS_COMMAND
        ]
        self.commands = commands

    def metadata_fields(self):
        return {
            "name": True,
            "description": True,
            "category": True,
            "commands": {"name": True, "description": True},
        }

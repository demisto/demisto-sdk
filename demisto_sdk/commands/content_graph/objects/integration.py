from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # avoid circular imports
    from demisto_sdk.commands.content_graph.objects.pack import BasePack


from pydantic import BaseModel, Field, validator

from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class BaseCommand(BaseModel):
    name: str

    class Config:
        orm_mode = True


class Command(BaseCommand):
    name: str
    deprecated: bool = False
    description: str


class BaseIntegration(IntegrationScript):
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_feed: bool = False
    category: str

    
    @property
    def in_pack(self) -> Optional["BasePack"]:
        for r in self.relationships_data:
            if r.relationship_type == RelationshipType.IN_PACK:
                return r.related_to  # type: ignore[return-value]
        return None
                
    # @property
    # def commands(self):
    #     return [
    #         Command(
    #             # the related to has to be a command
    #             name=r.related_to.name,  # type: ignore[union-attr]
    #             deprecated=r.deprecated,
    #             description=r.description,
    #         )
    #         for r in self.relationshipss
    #         if not r.is_nested and r.relationship_type == RelationshipType.HAS_COMMAND
    #     ]

    def to_integration_with_commands(self) -> "Integration":

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
        return Integration(**self.dict(), commands=commands)
    
    def included_in_metadata(self):
        return {"name", "description", "category"}  # move back

    # def summary(self) -> dict:
    #     summary = super().summary()
    #     summary["commands"] = [{"name": command.name, "description": command.description} for command in self.commands]
    #     return summary


class Integration(BaseIntegration, content_type=ContentType.INTEGRATION):
    commands: List[Command] = Field([], exclude=True)  # todo: override exclusion when loading from database

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

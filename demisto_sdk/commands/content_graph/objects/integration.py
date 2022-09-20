from typing import List

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.objects.integration_script import \
    IntegrationScript


class Command(BaseModel):
    name: str
    deprecated: bool = False
    description: str

    class Config:
        orm_mode = True


class Integration(IntegrationScript):
    is_fetch: bool = False
    is_fetch_events: bool = False
    is_feed: bool = False
    category: str
    commands: List[Command] = Field([], exclude=True)  # todo: override exclusion when loading from database

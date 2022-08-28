from pydantic import BaseModel, Field
from typing import List

from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


class Command(BaseModel):
    name: str
    deprecated: bool = False
    description: str

    class Config:
        orm_mode = True


class Integration(IntegrationScript):
    display_name: str = ''
    is_fetch: bool = False
    is_feed: bool = False
    category: str
    commands: List[Command] = Field([], exclude=True)  # todo: override exclusion when loading from database

    def included_in_metadata(self):
        return {'name': True,
                'description': True,
                'category': True,
                'commands':
                {
                    'name': True,
                    'description': True
                }
                }

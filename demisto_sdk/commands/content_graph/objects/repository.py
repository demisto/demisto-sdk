from pathlib import Path
from typing import List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from pydantic import BaseModel


class Repository(BaseModel):
    path: Path
    packs: List[Pack]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

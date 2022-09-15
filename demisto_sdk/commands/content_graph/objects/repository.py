from pathlib import Path
from typing import List

from pydantic import BaseModel

from demisto_sdk.commands.content_graph.objects.pack import Pack


class Repository(BaseModel):
    path: Path
    packs: List[Pack]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

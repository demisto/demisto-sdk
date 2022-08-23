from pathlib import Path
from pydantic import BaseModel
from typing import List

from demisto_sdk.commands.content_graph.objects.pack import Pack


class Repository(BaseModel):
    path: Path
    packs: List[Pack]

    def dump(self, path: Path, marketplace):
        for pack in self.packs:
            pack.dump(path / pack.name)
        # save everything in zip
        # sign zip
                    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

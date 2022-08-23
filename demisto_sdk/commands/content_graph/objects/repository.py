from pathlib import Path
from pydantic import BaseModel, DirectoryPath
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.objects.pack import Pack


class Repository(BaseModel):
    path: Path
    packs: List[Pack]

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions):
        for pack in self.packs:
            pack.dump(dir / pack.name, marketplace)
        # save everything in zip
        # sign zip
                    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

import logging
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List

from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.objects.pack import Pack

logger = logging.getLogger("demisto-sdk")

USE_FUTURE = True  # toggle this for better debugging


class ContentDTO(BaseModel):
    path: DirectoryPath = Path(get_content_path())
    packs: List[Pack]

    def dump(
        self, dir: DirectoryPath, marketplace: MarketplaceVersions, zip: bool = True
    ):
        logger.info("starting repo dump")
        start_time = time.time()
        if USE_FUTURE:
            with ProcessPoolExecutor() as executer:
                for pack in self.packs:
                    executer.submit(pack.dump, dir / pack.path.name, marketplace)
        else:
            for pack in self.packs:
                pack.dump(dir / pack.path.name, marketplace)

        time_taken = time.time() - start_time
        logger.info(f"ending repo dump. Took {time_taken} seconds")

        if zip:
            shutil.make_archive(str(dir.parent / "content_packs"), "zip", dir)
            shutil.rmtree(dir)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

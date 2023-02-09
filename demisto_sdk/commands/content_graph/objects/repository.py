import logging
import shutil
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List

from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.objects.pack import Pack

logger = logging.getLogger("demisto-sdk")

USE_FUTURE = True  # toggle this for better debugging


class ContentDTO(BaseModel):
    path: DirectoryPath = Path(get_content_path())  # type: ignore
    packs: List[Pack]

    def dump(
        self, dir: DirectoryPath, marketplace: MarketplaceVersions, zip: bool = True
    ):
        dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Starting repository dump")
        start_time = time.time()
        if USE_FUTURE:
            with Pool(processes=cpu_count()) as pool:
                pool.starmap(
                    Pack.dump,
                    ((pack, dir / pack.path.name, marketplace) for pack in self.packs),
                )

        else:
            for pack in self.packs:
                pack.dump(dir / pack.path.name, marketplace)

        time_taken = time.time() - start_time
        logger.debug(f"Repository dump ended. Took {time_taken} seconds")

        if zip:
            shutil.make_archive(str(dir.parent / "content_packs"), "zip", dir)
            shutil.rmtree(dir)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

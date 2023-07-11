import shutil
import time
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List

from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack

USE_MULTIPROCESSING = False  # toggle this for better debugging


class ContentDTO(BaseModel):
    path: DirectoryPath = Path(CONTENT_PATH)  # type: ignore
    packs: List[Pack]

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
        zip: bool = True,
        output_stem: str = "content_packs",  # without extension
    ):
        dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Starting repository dump")
        start_time = time.time()
        if USE_MULTIPROCESSING:
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
            shutil.make_archive(str(dir.parent / output_stem), "zip", dir)
            shutil.rmtree(dir)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

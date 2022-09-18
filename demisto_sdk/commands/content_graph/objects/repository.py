from pathlib import Path
import shutil
from pydantic import BaseModel, DirectoryPath
from typing import List
from demisto_sdk.commands.common.constants import MarketplaceVersions

from demisto_sdk.commands.content_graph.objects.pack import Pack
import time
import logging

logger = logging.getLogger('demisto-sdk')


class Repository(BaseModel):
    path: Path
    packs: List[Pack]
    
    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions):
        # TODO understand why multiprocessing is not working
        from multiprocessing.pool import ThreadPool
        logger.info('starting repo dump')
        start_time = time.time()
        with ThreadPool() as pool:
            pool.map(lambda pack: pack.dump(dir / pack.name, marketplace), self.packs)
        time_taken = time.time() - start_time
        logger.info(f'ending repo dump. Took {time_taken} seconds')

        # zip all packs
        shutil.make_archive(str(dir.parent / 'content_packs'), 'zip', dir)

        shutil.rmtree(dir)

        # save everything in zip
        # sign zip

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

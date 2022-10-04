from concurrent.futures import ProcessPoolExecutor
import glob
import os
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
    path: DirectoryPath
    packs: List[Pack]
    
    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions, no_zip: bool = False):
        # TODO understand why multiprocessing is not working
    
        logger.info('starting repo dump')
        start_time = time.time()
        with ProcessPoolExecutor() as executer:
            {executer.submit(pack.dump, dir / pack.path.name, marketplace): pack for pack in self.packs}
        time_taken = time.time() - start_time
        logger.info(f'ending repo dump. Took {time_taken} seconds')

        if not no_zip:
            shutil.make_archive(str(dir.parent / 'content_packs'), 'zip', dir)
            shutil.rmtree(dir)
        else:
            shutil.move(str(dir), dir.parent / 'content_packs')
                
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

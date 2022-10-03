from concurrent.futures import ProcessPoolExecutor
import glob
import os
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
    
    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions):
        # TODO understand why multiprocessing is not working
    
        logger.info('starting repo dump')
        start_time = time.time()
        with ProcessPoolExecutor() as executer:
            {executer.submit(pack.dump, dir / pack.path.name, marketplace): pack for pack in self.packs}
        time_taken = time.time() - start_time
        logger.info(f'ending repo dump. Took {time_taken} seconds')
        # if mpv2 we need to replace XSOAR to PRODUCT_NAME
        if marketplace == MarketplaceVersions.MarketplaceV2:
            # glob for all files in dir recursively      
            for filepath in glob.iglob(f'{dir}/**', recursive=True):
                if 'ReleaseNotes' in filepath:
                    continue
                with open(filepath) as file:
                    s = file.read()
                s = s.replace('Cortex XSOAR', os.getenv('PRODUCT_NAME', 'Cortex XSOAR'))
                with open(filepath, "w") as file:
                    file.write(s)

        # zip all packs
        shutil.make_archive(str(dir.parent / 'content_packs'), 'zip', dir)

        shutil.rmtree(dir)
                
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

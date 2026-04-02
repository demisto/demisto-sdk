import shutil
import time
from functools import lru_cache
from multiprocessing.pool import Pool
from pathlib import Path
from typing import List, Optional, Tuple

import tqdm
from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.repository import RepositoryParser

USE_MULTIPROCESSING = False  # toggle this for better debugging


@lru_cache
def from_path(path: Path = CONTENT_PATH, packs_to_parse: Optional[Tuple[str]] = None):
    """
    Returns a ContentDTO object with all the packs of the content repository.

    This function is outside of the class for better caching.
    The class function uses this function so the behavior is the same.
    """
    repo_parser = RepositoryParser(path)
    packs = tuple(repo_parser.iter_packs(packs_to_parse))
    with tqdm.tqdm(
        total=len(packs),
        unit="packs",
        desc="Parsing packs",
        position=0,
        leave=True,
    ) as progress_bar:
        repo_parser.parse(packs_to_parse=packs, progress_bar=progress_bar)
    return ContentDTO.from_orm(repo_parser)


class ContentDTO(BaseModel):
    path: DirectoryPath = Path(CONTENT_PATH)  # type: ignore
    packs: List[Pack]

    @staticmethod
    def from_path(
        path: Path = CONTENT_PATH, packs_to_parse: Optional[Tuple[str, ...]] = None
    ):
        """
        Returns a ContentDTO object with all the packs of the content repository.
        """
        return from_path(path, packs_to_parse)

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
        zip: bool = True,
        packs_to_dump: Optional[list] = None,
        output_stem: str = "content_packs",  # without extension
    ):
        dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Got packs to dump: {packs_to_dump}")
        packs_to_dump = (
            [pack for pack in self.packs if pack.object_id in packs_to_dump]
            if packs_to_dump is not None
            else self.packs
        )

        if not packs_to_dump:
            logger.debug("didn't got packs to dump, skipping")
            return

        logger.debug(
            f"Starting repository dump for packs: {[pack.object_id for pack in packs_to_dump]}"
        )
        start_time = time.time()
        if USE_MULTIPROCESSING:
            with Pool(processes=cpu_count()) as pool:
                pool.starmap(
                    Pack.dump,
                    (
                        (pack, dir / pack.path.name, marketplace)
                        for pack in packs_to_dump
                    ),
                )

        else:
            for pack in packs_to_dump:
                pack.dump(dir / pack.path.name, marketplace)

        time_taken = time.time() - start_time
        logger.debug(f"Repository dump ended. Took {time_taken} seconds")

        if zip:
            shutil.make_archive(str(dir.parent / output_stem), "zip", dir)
            shutil.rmtree(dir)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

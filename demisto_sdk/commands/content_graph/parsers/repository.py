import multiprocessing
import traceback
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from tqdm import tqdm

from demisto_sdk.commands.common.constants import PACKS_FOLDER
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.parsers.content_item import (
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser

IGNORED_PACKS_FOR_PARSING = ["NonSupported"]


class RepositoryParser:
    """
    Attributes:
        path (Path): The repository path.
        packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        packs (List[PackParser]): A list of the repository's packs parser objects.
    """

    def __init__(self, path: Path) -> None:
        """Parsing all repository packs.

        Args:
            path (Path): The repository path.
            packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        """
        self.path: Path = path
        self.packs: List[PackParser] = []

    def parse(
        self,
        packs_to_parse: Optional[Tuple[Path, ...]] = None,
        progress_bar: Optional[tqdm] = None,
    ):
        if not packs_to_parse:
            # if no packs to parse were provided, parse all packs
            packs_to_parse = tuple(self.iter_packs())
        try:
            logger.debug("Parsing packs...")
            with multiprocessing.Pool(processes=cpu_count()) as pool:
                for pack in pool.imap_unordered(
                    RepositoryParser.parse_pack, packs_to_parse
                ):
                    if pack:
                        self.packs.append(pack)
                        if progress_bar:
                            progress_bar.update(1)
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def parse_pack(pack_path: Path) -> Optional[PackParser]:
        try:
            return PackParser(pack_path)
        except (NotAContentItemException, FileNotFoundError):
            logger.warning(f"Pack {pack_path.name} is not a valid pack. Skipping")
            return None

    @staticmethod
    def should_parse_pack(path: Path) -> bool:
        return (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in IGNORED_PACKS_FOR_PARSING
        )

    def iter_packs(
        self, packs_to_parse: Optional[Tuple[str, ...]] = None
    ) -> Iterator[Path]:
        """Iterates all packs in the repository.

        Yields:
            Iterator[Path]: A pack path.
        """
        packs_folder: Path = self.path / PACKS_FOLDER
        if packs_to_parse:
            for pack in packs_to_parse:
                path = packs_folder / pack
                if not path.is_dir():
                    raise FileNotFoundError(f"Pack {pack} does not exist.")
                if self.should_parse_pack(path):
                    yield path

        else:
            for path in packs_folder.iterdir():
                if self.should_parse_pack(path):
                    yield path

    def clear(self):
        self.packs = []

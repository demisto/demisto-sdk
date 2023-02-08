import logging
import multiprocessing
import traceback
from pathlib import Path
from typing import Iterator, List, Optional

from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.content_graph.common import PACKS_FOLDER
from demisto_sdk.commands.content_graph.parsers.pack import PackParser

IGNORED_PACKS_FOR_PARSING = ["NonSupported"]


logger = logging.getLogger("demisto-sdk")


class RepositoryParser:
    """
    Attributes:
        path (Path): The repository path.
        packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        packs (List[PackParser]): A list of the repository's packs parser objects.
    """

    def __init__(self, path: Path, packs_to_parse: Optional[List[str]] = None) -> None:
        """Parsing all repository packs.

        Args:
            path (Path): The repository path.
            packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        """
        self.path: Path = path

        self.packs_to_parse: Optional[List[str]] = packs_to_parse
        try:
            logger.info("Parsing packs...")
            with multiprocessing.Pool(processes=cpu_count()) as pool:
                self.packs: List[PackParser] = list(
                    pool.map(PackParser, self.iter_packs())
                )
        except Exception:
            logger.error(traceback.format_exc())
            raise

    def should_parse_pack(self, path: Path) -> bool:
        return (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in IGNORED_PACKS_FOR_PARSING
        )

    def iter_packs(self) -> Iterator[Path]:
        """Iterates all packs in the repository.

        Yields:
            Iterator[Path]: A pack path.
        """
        packs_folder: Path = self.path / PACKS_FOLDER
        if self.packs_to_parse:
            for pack in self.packs_to_parse:
                path = packs_folder / pack
                if not path.is_dir():
                    raise FileNotFoundError(f"Pack {pack} does not exist.")
                if self.should_parse_pack(path):
                    yield path

        else:
            for path in packs_folder.iterdir():
                if self.should_parse_pack(path):
                    yield path

import multiprocessing
from pathlib import Path
from typing import Iterator, List

from demisto_sdk.commands.content_graph.common import PACKS_FOLDER
from demisto_sdk.commands.content_graph.parsers.pack import PackParser

IGNORED_PACKS_FOR_PARSING = ["NonSupported"]


class RepositoryParser:
    """
    Attributes:
        path (Path): The repository path.
        packs (List[PackParser]): A list of the repository's packs parser objects.
    """

    def __init__(self, path: Path) -> None:
        """Parsing all repository packs.

        Args:
            path (Path): The repository path.
        """
        self.path: Path = path
        pool = multiprocessing.Pool()
        self.packs: List[PackParser] = list(pool.map(PackParser, self.iter_packs()))

    def iter_packs(self) -> Iterator[Path]:
        """Iterates all packs in the repository.

        Yields:
            Iterator[Path]: A pack path.
        """
        packs_folder: Path = self.path / PACKS_FOLDER
        for path in packs_folder.iterdir():
            if (
                path.is_dir() and
                not path.name.startswith(".") and
                path.name not in IGNORED_PACKS_FOR_PARSING
            ):
                yield path

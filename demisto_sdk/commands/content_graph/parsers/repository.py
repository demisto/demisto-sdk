

import multiprocessing
from pathlib import Path
from typing import Iterator, List
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.constants import PACKS_FOLDER


IGNORED_PACKS_FOR_PARSING = ['NonSupported']

class RepositoryParser:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        pool = multiprocessing.Pool()
        self.packs: List[PackParser] = list(pool.map(PackParser, self.iter_packs()))
    
    def iter_packs(self) -> Iterator[Path]:
        packs_folder: Path = self.path / PACKS_FOLDER
        for path in packs_folder.iterdir():  # todo: handle repo path is invalid
            if path.is_dir() and not path.name.startswith('.') and path.name not in IGNORED_PACKS_FOR_PARSING:
                yield path
            
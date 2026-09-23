import multiprocessing
import traceback
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from tqdm import tqdm

from demisto_sdk.commands.common.constants import CONNECTORS_FOLDER, PACKS_FOLDER
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.parsers.connector import ConnectorParser
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
        connectors (List[ConnectorParser]): A list of the repository's connector parser objects
            (top-level ``connectors/<connector-name>`` directories, outside of ``Packs/``).
    """

    def __init__(self, path: Path) -> None:
        """Parsing all repository packs.

        Args:
            path (Path): The repository path.
            packs_to_parse (Optional[List[str]]): A list of packs to parse. If not provided, parses all packs.
        """
        self.path: Path = path
        self.packs: List[PackParser] = []
        self.connectors: List[ConnectorParser] = []

    def parse(
        self,
        packs_to_parse: Optional[Tuple[Path, ...]] = None,
        progress_bar: Optional[tqdm] = None,
        connectors_to_parse: Optional[Tuple[Path, ...]] = None,
    ):
        if packs_to_parse is None:
            # No caller intent provided -> default to parsing every pack.
            # Mirror the ``connectors_to_parse is None`` check below so an
            # explicit empty tuple (caller-says-"none") is honored instead
            # of being silently re-expanded to a full scan.
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

        # Connectors live outside of Packs/ and are parsed sequentially.
        # They are typically few in number (tens, not thousands) so the cost
        # of multiprocessing setup is not worth it here.
        if connectors_to_parse is None:
            connectors_to_parse = tuple(self.iter_connectors())
        if connectors_to_parse:
            logger.debug("Parsing connectors...")
            for connector_path in connectors_to_parse:
                connector = RepositoryParser.parse_connector(connector_path)
                if connector:
                    self.connectors.append(connector)
                    if progress_bar:
                        progress_bar.update(1)

    @staticmethod
    def parse_pack(pack_path: Path) -> Optional[PackParser]:
        try:
            return PackParser(pack_path)
        except (NotAContentItemException, FileNotFoundError):
            logger.warning(f"Pack {pack_path.name} is not a valid pack. Skipping")
            return None

    @staticmethod
    def parse_connector(connector_path: Path) -> Optional[ConnectorParser]:
        """Parse a single connector directory into a :class:`ConnectorParser`.

        Returns ``None`` when the directory is not a valid connector (missing
        ``connector.yaml``, malformed YAML, etc.) so iteration over the
        ``connectors/`` folder is resilient to partially-broken items.
        """
        try:
            return ConnectorParser(connector_path)
        except (NotAContentItemException, FileNotFoundError):
            logger.warning(
                f"Connector {connector_path.name} is not a valid connector. Skipping"
            )
            return None
        except Exception:
            # Connector parsing pulls in many sub-files; surface unexpected
            # failures as a warning rather than aborting the whole repo parse.
            logger.exception(
                f"Failed to parse connector {connector_path.name}. Skipping"
            )
            return None

    @staticmethod
    def should_parse_pack(path: Path) -> bool:
        return (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in IGNORED_PACKS_FOR_PARSING
        )

    @staticmethod
    def should_parse_connector(path: Path) -> bool:
        """A connector dir must contain a ``connector.yaml`` to be parsable."""
        return (
            path.is_dir()
            and not path.name.startswith(".")
            and (path / "connector.yaml").exists()
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

    def iter_connectors(
        self, connectors_to_parse: Optional[Tuple[str, ...]] = None
    ) -> Iterator[Path]:
        """Iterates over connector directories under ``connectors/`` at repo root.

        Args:
            connectors_to_parse: Optional explicit list of connector directory
                names to parse. When provided, missing directories raise
                ``FileNotFoundError``. When omitted, all connectors under
                ``connectors/`` are yielded.

        Yields:
            Iterator[Path]: Each valid connector directory path.
        """
        connectors_folder: Path = self.path / CONNECTORS_FOLDER
        if not connectors_folder.is_dir():
            # The connectors folder is optional - most repos won't have one.
            return
        if connectors_to_parse:
            for connector in connectors_to_parse:
                path = connectors_folder / connector
                if not path.is_dir():
                    raise FileNotFoundError(f"Connector {connector} does not exist.")
                if self.should_parse_connector(path):
                    yield path
        else:
            for path in connectors_folder.iterdir():
                if self.should_parse_connector(path):
                    yield path

    def clear(self):
        self.packs = []
        self.connectors = []

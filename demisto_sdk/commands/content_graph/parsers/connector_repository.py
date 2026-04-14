"""Repository-level parser for unified-connectors-content.

Analogous to ``RepositoryParser`` for the content repo, this parser
iterates all connector directories under ``connectors/`` and parses
each one into a ``ConnectorParser``.
"""

from pathlib import Path
from typing import Iterator, List, Optional

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.parsers.connector import ConnectorParser


CONNECTORS_FOLDER = "connectors"


class ConnectorRepositoryParser:
    """Parses all connectors in a unified-connectors-content repository.

    Attributes:
        path: The repository root path.
        connectors: Parsed connector objects.
    """

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.connectors: List[ConnectorParser] = []

    def parse(self) -> None:
        """Parse all connector directories."""
        for connector_path in self.iter_connectors():
            try:
                connector = ConnectorParser(connector_path)
                self.connectors.append(connector)
                logger.debug(f"Parsed connector: {connector.object_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to parse connector at {connector_path}: {e}"
                )

    def iter_connectors(self) -> Iterator[Path]:
        """Iterate all valid connector directories.

        Yields:
            Path: A connector directory path.
        """
        connectors_dir = self.path / CONNECTORS_FOLDER
        if not connectors_dir.exists():
            logger.debug(f"No connectors directory found at {connectors_dir}")
            return

        for path in sorted(connectors_dir.iterdir()):
            if self.should_parse_connector(path):
                yield path

    @staticmethod
    def should_parse_connector(path: Path) -> bool:
        """Check if a directory is a valid connector."""
        return (
            path.is_dir()
            and not path.name.startswith(".")
            and (path / "connector.yaml").exists()
        )

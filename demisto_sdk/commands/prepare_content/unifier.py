from abc import ABC, abstractmethod
from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions


class Unifier(ABC):
    """Interface to objects that need to be unified into YAML"""

    @staticmethod
    @abstractmethod
    def unify(
        path: Path,
        data: dict,
        marketplace: MarketplaceVersions = None,
        **kwargs,
    ) -> dict:
        """Merges the various components to create a unified output yml file."""
        ...

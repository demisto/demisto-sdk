from pathlib import Path
from typing import List, Optional

from TestSuite.integration import Integration
from TestSuite.script import Script
from TestSuite.secrets import Secrets


class Pack:
    """A class that mocks a pack inside to content repo

    Note:
        Do not include the `self` parameter in the ``Args`` section.

    Args:
        packs_dir: A Path to the root of Packs dir
        name: name of the pack to create

    Attributes:
        path (str): A path to the content pack.
        secrets (Secrets): Exception error code.
        integrations: A list contains any created integration
        scripts:  A list contains any created Script

    """

    def __init__(self, packs_dir: Path, name: str):
        # Initiate lists:
        self.integrations: List[Integration] = list()
        self.scripts: List[Script] = list()
        # Create base pack
        self._pack_path = packs_dir / name
        self._pack_path.mkdir()
        self.path = str(self._pack_path)
        # Create repo structure
        self._integrations_path = packs_dir / 'Integrations'
        self._integrations_path.mkdir()
        self._scripts_path = packs_dir / 'Scripts'
        self._scripts_path.mkdir()
        self._playbooks_path = packs_dir / 'Playbooks'
        self._playbooks_path.mkdir()
        self.secrets = Secrets(self._pack_path)

    def create_integration(self, name: Optional[str] = None):
        if not name:
            name = f'integration_{len(self.integrations)}'
        integration = Integration(self._integrations_path, name)
        self.integrations.append(integration)
        return integration

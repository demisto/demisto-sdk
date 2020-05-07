from pathlib import Path
from typing import List, Optional

from TestSuite.global_secrets import GlobalSecrets
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

    def __init__(self, packs_dir: Path, name: str, repo_path: str, global_secrets: GlobalSecrets):
        # Initiate lists:
        self.integrations: List[Integration] = list()
        self.scripts: List[Script] = list()
        # Create base pack
        self.global_secrets = global_secrets
        self.repo_path = repo_path
        self._pack_path = packs_dir / name
        self._pack_path.mkdir()
        self.path = str(self._pack_path)
        # Create repo structure
        self._integrations_path = self._pack_path / 'Integrations'
        self._integrations_path.mkdir()
        self._scripts_path = self._pack_path / 'Scripts'
        self._scripts_path.mkdir()
        self._playbooks_path = self._pack_path / 'Playbooks'
        self._playbooks_path.mkdir()
        self.secrets = Secrets(self._pack_path)
        self.secrets.write_secrets([])

    def create_integration(
            self,
            name: Optional[str] = None,
            yml: Optional[dict] = None,
            code: str = '',
            readme: str = '',
            description: str = '',
            changelog: str = '',
            image: bytes = b''):
        if name is None:
            name = f'integration_{len(self.integrations)}'
        if yml is None:
            yml = {}
        integration = Integration(self._integrations_path, name, self.repo_path, self.global_secrets)
        integration.build(
            code,
            yml,
            readme,
            description,
            changelog,
            image
        )
        self.integrations.append(integration)
        return integration

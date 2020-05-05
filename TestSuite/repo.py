"""

"""
from pathlib import Path
from typing import List, Optional

from TestSuite.pack import Pack
from TestSuite.secrets import Secrets


class Repo:
    """A class that mocks a content repo

    Note:
        Do not include the `self` parameter in the ``Args`` section.

    Args:
        tmpdir: A Path to the root of the repo

    Attributes:
        path: A path to the content pack.
        secrets: Exception error code.
        packs: A list of created packs
    """

    def __init__(self, tmpdir: Path):
        self.packs: List[Pack] = list()
        self._tmpdir = tmpdir
        self._packs_path = tmpdir / 'Packs'
        self._packs_path.mkdir()
        self.path = str(self._tmpdir)
        self.secrets = Secrets(tmpdir, 'Tests/secrets_white_list_json')

    def create_pack(self, name: Optional[str] = None):
        if not name:
            name = f'pack_{len(self.packs)}'
        pack = Pack(self._packs_path, name)
        self.packs.append(pack)
        return pack

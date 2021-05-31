import os
from typing import List, Optional, Union

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject
from wcmatch.pathlib import Path


class Readme(TextObject):
    def __init__(self, path: Union[Path, str], pack_path: Union[Path, str] = ''):
        self._path = path
        self._pack_path = pack_path
        super().__init__(path)

    def type(self):
        return FileType.README

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Mention contributors in pack readme"""
        contributors_file_path = os.path.join(self._pack_path, "CONTRIBUTORS.md")
        try:
            if os.path.exists(contributors_file_path):
                with open(contributors_file_path, 'r') as contributors_file:
                    contributor_data = contributors_file.read()
                with open(self._path, 'a+') as readme_file:
                    readme_file.write("<br>---<br>")
                    readme_file.write(contributor_data)
        except Exception as e:
            print(e)

        return super().dump(dest_dir)

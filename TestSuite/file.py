import os
from pathlib import Path


class File:
    def __init__(self, tmp_path: Path, repo_path: str, txt: str = ''):
        self._tmp_path = tmp_path
        self._repo_path = repo_path
        self.path = str(self._tmp_path)
        self.rel_path = os.path.relpath(self.path, self._repo_path)
        self.write(txt)

    def write(self, txt: str):
        self._tmp_path.write_text(txt)

    def write_bytes(self, txt: bytes):
        self._tmp_path.write_bytes(txt)

    def read(self) -> str:
        return self._tmp_path.read_text()

    def read_bytes(self) -> bytes:
        return self._tmp_path.read_bytes()

    def write_list(self, lst: list):
        self.write('\n'.join(lst))

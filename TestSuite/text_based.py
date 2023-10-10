from pathlib import Path


class TextBased:
    def __init__(self, dir_path: Path, name: str):
        self._dir_path = dir_path
        self.name = name
        self._file_path = dir_path / name
        self.path = str(self._file_path)
        self.write_text()

    def write_text(self, text: str = ""):
        self._file_path.write_text(data=text, encoding=None)

    def write_list(self, lst: list):
        self._file_path.write_text(data="\n".join(lst), encoding=None)

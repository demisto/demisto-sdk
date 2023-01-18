from pathlib import Path
from typing import Dict, List


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

    def write_validations(self, file_names_and_validations: Dict[str, List[str]]):
        """
        Writes validations into the .pack-ignore.

        Args:
            file_names_and_validations (dict): a mapping between file name and validations that should be ignored.

        Input Example:
            {'IntegrationTest.yml': ['IN122', 'RM110']}
        """
        pack_ignore_validations = []

        for file_name, validations in file_names_and_validations.items():
            pack_ignore_validations.append(
                f'[file:{file_name}]\nignore={",".join(validations)}'
            )

        self.write_list(pack_ignore_validations)

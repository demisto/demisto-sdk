import csv
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

from demisto_sdk.commands.content_graph.common import NEO4J_FOLDER


class Neo4jImportHandler:
    def __init__(self, repo_path: Path, external_import_paths: Optional[List[Path]] = None) -> None:
        self.repo_path = repo_path
        self.repo_import_path: Path = repo_path / NEO4J_FOLDER / "import"
        self.all_import_paths: List[Path] = self._validate_and_retrieve_import_paths(external_import_paths or [])

    def _validate_and_retrieve_import_paths(self, external_import_paths: List[Path]) -> List[Path]:
        all_import_paths = []
        if not self.repo_import_path.is_dir():
            err = f'Did not find a valid import path for the repository, expected a directory: {self.repo_import_path}'
            raise NotADirectoryError(err)
        all_import_paths.append(self.repo_import_path)

        for import_path in external_import_paths:
            if not import_path.is_dir():
                raise NotADirectoryError(f'Invalid external import path: {import_path}')
            all_import_paths.append(import_path)
        return all_import_paths

    def get_nodes_files(self) -> List[str]:
        return [file.name for file in self.repo_import_path.iterdir() if '.nodes.' in file.name]

    def get_relationships_files(self) -> List[str]:
        return [file.name for file in self.repo_import_path.iterdir() if '.relationships.' in file.name]

    def clean_import_dir_before_export(self) -> None:
        for file in self.repo_import_path.iterdir():
            os.remove(file)

    def ensure_data_uniqueness(self) -> None:
        if len(self.all_import_paths) > 1:
            for idx, import_path in enumerate(self.all_import_paths, 1):
                self._set_unique_ids_for_import_directory(import_path, str(idx))

    def _set_unique_ids_for_import_directory(self, import_path: Path, prefix: str) -> None:
        for filename in import_path.iterdir():
            if filename.suffix == '.csv':
                tempfile = NamedTemporaryFile(mode='w', delete=False)
                with open(filename, 'r') as csv_file, tempfile:
                    reader = csv.reader(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    writer = csv.writer(tempfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(next(reader))  # skip headers row
                    for row in reader:
                        row[0] = f'{prefix}{row[0]}'
                        row[1] = f'{prefix}{row[1]}' if 'relationships' in filename.name else row[1]
                        writer.writerow(row)
                shutil.move(tempfile.name, (self.repo_import_path / filename.name).as_posix())

    def _get_indexes_to_exclude(self, headers: List[str]) -> List[int]:
        return [
            idx for idx, x in enumerate(headers)
            if x in ['__csv_id', '__csv_type']
        ]

    def _remove_items_by_index(self, row, indexes_to_skip: List[int]) -> List[str]:
        return [x for idx, x in enumerate(row) if idx not in indexes_to_skip]

    def fix_csv_files_after_export(self) -> None:
        for filename in self.repo_import_path.iterdir():
            if filename.suffix == '.csv':
                tempfile = NamedTemporaryFile(mode='w', delete=False)
                with open(filename, 'r') as csv_file, tempfile:
                    reader = csv.reader(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    writer = csv.writer(tempfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    headers = [x.strip() for x in next(reader)]
                    indexes_to_exclude = self._get_indexes_to_exclude(headers)
                    writer.writerow(self._remove_items_by_index(headers, indexes_to_exclude))
                    for row in reader:
                        writer.writerow(self._remove_items_by_index(row, indexes_to_exclude))

                shutil.move(tempfile.name, filename.as_posix())

import csv
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import NEO4J_IMPORT_PATH


def clean_import_dir_before_export() -> None:
    for file in NEO4J_IMPORT_PATH.iterdir():
        os.remove(file)


def prepare_csv_files_for_import(import_path: Path, prefix: str) -> None:
    for filename in import_path.iterdir():
        if filename.suffix == '.csv':
            tempfile = NamedTemporaryFile(mode='w', delete=False)
            with open(filename, 'r') as csv_file, tempfile:
                reader = csv.reader(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer = csv.writer(tempfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                headers = next(reader)
                writer.writerow(headers)
                for row in reader:
                    row[0] = prefix + row[0]
                    row[1] = prefix + row[1] if 'relationships' in filename.name else row[1]
                    writer.writerow(row)

            new_file_path = NEO4J_IMPORT_PATH / filename.name if not filename.name.startswith('content.') else filename
            shutil.move(tempfile.name, new_file_path.as_posix())


def get_indexes_to_exclude(headers: List[str]) -> List[int]:
    return [
        idx for idx, x in enumerate(headers)
        if x in ['__csv_id', '__csv_type']
    ]


def remove_items_by_index(row, indexes_to_skip: List[int]) -> List:
    return [x for idx, x in enumerate(row) if idx not in indexes_to_skip]


def fix_csv_files_after_export() -> None:
    for filename in NEO4J_IMPORT_PATH.iterdir():
        if filename.suffix == '.csv':
            tempfile = NamedTemporaryFile(mode='w', delete=False)
            with open(filename, 'r') as csv_file, tempfile:
                reader = csv.reader(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer = csv.writer(tempfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                headers = [x.strip() for x in next(reader)]
                indexes_to_exclude = get_indexes_to_exclude(headers)
                writer.writerow(remove_items_by_index(headers, indexes_to_exclude))
                for row in reader:
                    writer.writerow(remove_items_by_index(row, indexes_to_exclude))

            shutil.move(tempfile.name, filename.as_posix())

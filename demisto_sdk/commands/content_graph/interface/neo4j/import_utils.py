import csv
import logging
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List, Set
from zipfile import ZipFile

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import download_content_graph
from demisto_sdk.commands.content_graph.neo4j_service import get_neo4j_import_path

logger = logging.getLogger("demisto-sdk")


class Neo4jImportHandler:
    def __init__(self) -> None:
        self.import_path: Path = get_neo4j_import_path()
        logger.debug(f"Import path: {self.import_path}")

    def clean_import_dir(self) -> None:
        for file in self.import_path.iterdir():
            os.remove(file)

    def get_nodes_files(self) -> List[str]:
        return [
            file.name for file in self.import_path.iterdir() if ".nodes." in file.name
        ]

    def get_relationships_files(self) -> List[str]:
        return [
            file.name
            for file in self.import_path.iterdir()
            if ".relationships." in file.name
        ]

    def ensure_data_uniqueness(self) -> None:
        if len(sources := self._get_import_sources()) > 1:
            for idx, source in enumerate(sources, 1):
                self._set_unique_ids_for_source(source, str(idx))

    def _get_import_sources(self) -> Set[str]:
        sources: Set[str] = set()
        for filename in self.import_path.iterdir():
            # csv filenames are in the format <source>.<nodes/relationships>.<labels/type>.csv
            if source := filename.name.split(".")[0]:
                sources.add(source)
        return sources

    def _set_unique_ids_for_source(self, source: str, prefix: str) -> None:
        for filename in self.import_path.iterdir():
            if filename.name.startswith(f"{source}.") and filename.suffix == ".csv":
                tempfile = NamedTemporaryFile(mode="w", delete=False)
                with open(filename) as csv_file, tempfile:
                    reader = csv.reader(
                        csv_file,
                        delimiter=",",
                        quotechar='"',
                        quoting=csv.QUOTE_MINIMAL,
                    )
                    writer = csv.writer(
                        tempfile,
                        delimiter=",",
                        quotechar='"',
                        quoting=csv.QUOTE_MINIMAL,
                    )
                    writer.writerow(next(reader))  # skip headers row
                    for row in reader:
                        row[0] = f"{prefix}{row[0]}"
                        row[1] = (
                            f"{prefix}{row[1]}"
                            if "relationships" in filename.name
                            else row[1]
                        )
                        writer.writerow(row)
                shutil.move(
                    tempfile.name, (self.import_path / filename.name).as_posix()
                )

    def zip_import_dir(self, output_file: Path) -> None:
        output_file = output_file.with_suffix(".zip")
        shutil.make_archive(str(output_file), "zip", self.import_path)

    def download_from_bucket(self):
        logger.info("Downloading content graph from bucket")
        with TemporaryDirectory() as temp_dir:
            download_content_graph(Path(temp_dir))
            # TODO handle different marketplace versions in the future
            with ZipFile(
                Path(temp_dir) / MarketplaceVersions.XSOAR.value, "r"
            ) as zip_obj:
                zip_obj.extractall(str(self.import_path))

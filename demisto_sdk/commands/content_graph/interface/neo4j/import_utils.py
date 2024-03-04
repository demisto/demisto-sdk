import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Set
from zipfile import ZipFile

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.singleton import SingletonMeta
from demisto_sdk.commands.content_graph.neo4j_service import get_neo4j_import_path

GRAPHML_FILE_SUFFIX = ".graphml"


class Neo4jImportHandler(metaclass=SingletonMeta):
    def __init__(self) -> None:
        """This class handles the import of data to neo4j.
        import_path is the path to the directory where the data is located.


        Args:
            imported_path (Optional[Path], optional): A zip file path to import the graph from. Defaults to None.
                                                      If not given, the graph will use the content in the `import_path` directory.
        """
        self.import_path: Path = get_neo4j_import_path()
        self.import_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Import path: {self.import_path}")

    def extract_files_from_path(self, imported_path: Optional[Path] = None) -> None:
        if not imported_path:
            return None
        with ZipFile(imported_path, "r") as zip_obj:
            zip_obj.extractall(self.import_path)

    def clean_import_dir(self) -> None:
        for file in self.import_path.iterdir():
            Path(file).unlink()

    def get_graphml_filenames(self) -> List[str]:
        return [
            file.name
            for file in self.import_path.iterdir()
            if file.suffix == GRAPHML_FILE_SUFFIX
        ]

    def ensure_data_uniqueness(self) -> None:
        if len(sources := self._get_import_sources()) > 1:
            for idx, source in enumerate(sources, 1):
                self._set_unique_ids_for_source(source, str(idx))

    def _get_import_sources(self) -> Set[str]:
        sources: Set[str] = set()
        for filename in self.import_path.iterdir():
            if filename.suffix == GRAPHML_FILE_SUFFIX:
                sources.add(filename.as_posix())
        return sources

    def _set_unique_ids_for_source(self, source: str, prefix: str) -> None:
        xml_namespace: str = "http://graphml.graphdrawing.org/xmlns"
        ET.register_namespace("", xml_namespace)
        # Load the graphml file
        tree: ET.ElementTree = ET.parse(source)
        root: ET.Element = tree.getroot()

        # Set the prefix for each node
        for node in root.findall(f".//{{{xml_namespace}}}node"):
            node.attrib["id"] = f"n{prefix}{node.attrib['id'][1:]}"

        # Set the prefix for each edge
        for edge in root.findall(f".//{{{xml_namespace}}}edge"):
            edge.attrib["id"] = f"e{prefix}{edge.attrib['id'][1:]}"
            edge.attrib["source"] = f"n{prefix}{edge.attrib['source'][1:]}"
            edge.attrib["target"] = f"n{prefix}{edge.attrib['target'][1:]}"

        # Write the updated graphml file
        tree.write(source)

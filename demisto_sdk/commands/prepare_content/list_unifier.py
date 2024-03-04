import copy
from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.constants import LISTS_DIR, MarketplaceVersions
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier

LIST_DATA_SUFFIXES = (".txt", ".json", ".html", ".css", ".csv", ".md")


class ListUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path, data: Dict, marketplace: MarketplaceVersions = None, **kwargs
    ) -> Dict:
        logger.debug(f"Unifying {path}...")
        if path.parent.name == LISTS_DIR:
            # if the file is in the lists directory, we assume it is already unified
            logger.debug(f"File is already unified: {path.name}")
            return data
        package_path = path.parent
        file_content_data_path = ListUnifier.find_data_file(
            package_path / (package_path.name + "_data")
        )
        if not file_content_data_path:
            logger.warning(
                f"No data file found for '{path}', assuming file is already unified."
            )
            return data

        json_unified = copy.deepcopy(data)
        json_unified = ListUnifier.insert_data_to_json(
            json_unified, file_content_data_path
        )
        logger.debug(f"[green]Created unified json: {path.name}[/green]")
        return json_unified

    @staticmethod
    def insert_data_to_json(json_unified: Dict, file_content_data_path: Path):
        if json_unified.get("data", "") not in ("", "-"):
            logger.warning(
                "data section is not empty in "
                f"{file_content_data_path.with_name(f'{file_content_data_path.parent.name}.json')} file. "
                "It should be blank or a dash(-)."
            )
        json_unified["data"] = TextFile.read_from_local_path(file_content_data_path)

        return json_unified

    @staticmethod
    def find_data_file(list_path: Path) -> Optional[Path]:
        """
        To unify, we need to find the file with the actual list data.
        """
        for suffix in LIST_DATA_SUFFIXES:
            if (path_file_data := list_path.with_suffix(suffix)).exists():
                return path_file_data
        return None

import copy
from pathlib import Path

from demisto_sdk.commands.common.constants import LISTS_DIR, MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier


class ListUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path, data: dict, marketplace: MarketplaceVersions = None, **kwargs
    ) -> dict:
        logger.info(f"Unifying {path}...")
        if path.parent.name == LISTS_DIR:
            return data
        package_path = path.parent
        path_file_data = ListUnifier.find_file_content_data(
            package_path / (package_path.name + "_data")
        )
        if not path_file_data:
            logger.warning(
                f"No data file found for '{path}', assuming file is already unified."
            )
            return data

        json_unified = copy.deepcopy(data)
        json_unified = ListUnifier.insert_data_to_json(json_unified, path_file_data)
        logger.debug(f"[green]Created unified json: {path.name}[/green]")
        return json_unified

    @staticmethod
    def insert_data_to_json(json_unified: dict, file_content_data: Path):
        if json_unified.get("data", "") not in ("", "-"):
            logger.warning(
                "data section is not empty in "
                f"{file_content_data.with_name(f'{file_content_data.parent.name}.json')} file. "
                "It should be blank or a dash(-)."
            )
        json_unified["data"] = file_content_data.read_text()

        return json_unified

    @staticmethod
    def find_file_content_data(list_path: Path) -> Path | None:
        for suffix in (".txt", ".json", ".html", ".css", ".csv", ".md"):
            if (path_file_data := list_path.with_suffix(suffix)).exists():
                return path_file_data
        return None

from pathlib import Path

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import JSON_Handler


class JsonFile(StructuredFile):

    default_handler: JSON_Handler = json

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() == ".json"

from pathlib import Path

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.handlers import JSON5_Handler


class Json5File(StructuredFile):
    default_handler: JSON5_Handler = json5

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() == ".json5"

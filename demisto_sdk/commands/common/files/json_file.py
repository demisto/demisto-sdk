from pathlib import Path

from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType


class JsonFile(StructuredFile):
    handler: JSON_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: JSON_Handler) -> JSON_Handler:
        return v or json

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() == ".json" or super().is_model_type_by_path(path)

    @classmethod
    def is_model_type_by_content_type(cls, content_type: ContentType) -> bool:
        return content_type in (
            ContentType.INDICATOR_TYPE,
            ContentType.INDICATOR_FIELD,
            ContentType.INCIDENT_TYPE,
            ContentType.INCIDENT_FIELD,
            ContentType.CLASSIFIER,
            ContentType.DASHBOARD,
            ContentType.GENERIC_DEFINITION,
            ContentType.GENERIC_FIELD,
            ContentType.GENERIC_MODULE,
            ContentType.GENERIC_TYPE,
            ContentType.JOB,
            ContentType.LAYOUT,
            ContentType.LAYOUT_RULE,
            ContentType.LIST,
            ContentType.MAPPER,
            ContentType.PREPROCESS_RULE,
            ContentType.REPORT,
            ContentType.TRIGGER,
            ContentType.WIDGET,
            ContentType.WIZARD,
            ContentType.XDRC_TEMPLATE,
            ContentType.XSIAM_DASHBOARD,
            ContentType.XSIAM_REPORT,
        )

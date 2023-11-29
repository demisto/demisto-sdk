from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.content_graph.common import ContentType


class YmlFile(StructuredFile):
    handler: YAML_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: YAML_Handler) -> YAML_Handler:
        return v or yaml

    @classmethod
    def is_class_type_by_content_type(cls, content_type: ContentType) -> bool:
        return content_type in (
            ContentType.BASE_PLAYBOOK,
            ContentType.BASE_SCRIPT,
            ContentType.CORRELATION_RULE,
            ContentType.INTEGRATION,
            ContentType.MODELING_RULE,
            ContentType.PARSING_RULE,
            ContentType.PLAYBOOK,
            ContentType.SCRIPT,
            ContentType.TEST_PLAYBOOK,
            ContentType.TEST_SCRIPT,
        )

from enum import Enum
from typing import List

from pydantic import BaseModel, validator

from demisto_sdk.commands.common.logger import logger

INITIAL_LOG = {
    "logs": [
        {
            "description": "enter description about this PR",
            "type": "<fix|feature|breaking>",
        }
    ]
}

class logType(str, Enum):
    fix = "fix"
    feature = "feature"
    breaking = "breaking"
    initial = "<fix|feature|breaking>"


class Log(BaseModel):
    description: str
    type: logType

    class Config:
        """Pydantic config class"""

        use_enum_values = True

    @validator("type")
    def is_type_initial_mode(cls, value):
        if value == "<fix|feature|breaking>":
            logger.error("One of the types is still not different from the initial value, please edit it")
        return value

    @validator("description")
    def is_description_initial_mode(cls, value):
        if value == "enter description about this PR":
            logger.error("One of the descriptions is still not different from the initial value, please edit it")
        return value

class LogObject(BaseModel):
    logs: List[Log]

    def build_log(cls) -> List[str]:
        built_logs: List[str] = []
        for log in cls.logs:
            if log.type == logType.breaking:
                type_msg = ""
            elif log.type == logType.feature:
                type_msg = ""
            elif log.type == logType.fix:
                type_msg = ""
            built_logs.append(f"* {type_msg}: {log.description}\n")
        return built_logs

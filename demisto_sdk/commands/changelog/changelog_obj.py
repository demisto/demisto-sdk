from enum import Enum
from typing import List
from demisto_sdk.commands.common.logger import logger

from pydantic import BaseModel, validator

INITIAL_LOG = {
    "log": [
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
            logger.error("type initial msg")
        return value

    @validator("description")
    def is_description_initial_mode(cls, value):
        if value == "enter description about this PR":
            logger.error("description is initial msg")
        return value

class LogObject(BaseModel):
    log: List[Log]


from enum import Enum
from typing import List

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


class Log(BaseModel):
    description: str
    type: logType


class LogObject(BaseModel):
    log: List[Log]

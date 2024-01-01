from enum import Enum
from typing import Dict, List, Union

from pydantic import BaseModel, validator, root_validator

INITIAL_DESCRIPTION = "enter description about this PR"
INITIAL_TYPE = "<breaking|feature|fix|internal>"

INITIAL_LOG: Dict[str, Union[int, List[dict]]] = {
    "changes": [
        {
            "description": INITIAL_DESCRIPTION,
            "type": INITIAL_TYPE,
        }
    ]
}


class LogType(str, Enum):
    breaking = "breaking"
    feature = "feature"
    fix = "fix"
    internal = "internal"

    @staticmethod
    def list():
        return [value.value for value in LogType]


class LogLine:
    def __init__(self, description: str, pr_number: str, type_: LogType) -> None:
        self.description = description
        self.pr_number = pr_number
        self.type = type_

    def to_string(self):
        return f"* {self.description} [#{self.pr_number}](https://github.com/demisto/demisto-sdk/pull/{self.pr_number})"


class LogEntry(BaseModel):
    description: str
    type: LogType

    class Config:
        """Pydantic config class"""

        use_enum_values = True

    @root_validator(pre=True)
    def validate(cls, values):
        if values["type"] == INITIAL_TYPE:
            raise ValueError(
                "One of the types is still not different from the initial value, please edit it"
            )
        elif values["type"] not in LogType.list():
            raise ValueError(
                f"The type {values['type']} is not supported, please use one of the following: {LogType.list()}"
            )
        if values["description"] == INITIAL_DESCRIPTION:
            raise ValueError(
                "One of the descriptions is still not different from the initial value, please edit it"
            )
        
        return values


class LogFileObject(BaseModel):
    changes: List[LogEntry]
    pr_number: int

    def get_log_entries(self) -> List[LogLine]:
        return [
            LogLine(log_entry.description, str(self.pr_number), log_entry.type)
            for log_entry in self.changes
        ]

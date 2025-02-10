from typing import Dict, List, Union

from pydantic import BaseModel, ConfigDict, field_validator

from demisto_sdk.commands.common.StrEnum import StrEnum

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


class LogType(StrEnum):
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
    model_config = ConfigDict(use_enum_values=True)

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, value):
        if value == INITIAL_TYPE:
            raise ValueError(
                "The type is still not different from the initial value, please edit it"
            )
        elif value not in LogType.list():
            raise ValueError(
                f"The type {value} is not supported, please use one of the following: {LogType.list()}"
            )

        return value

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value):
        if value == INITIAL_DESCRIPTION:
            raise ValueError(
                "The description is still not different from the initial value, please edit it"
            )
        return value


class LogFileObject(BaseModel):
    changes: List[LogEntry]
    pr_number: int

    def get_log_entries(self) -> List[LogLine]:
        return [
            LogLine(log_entry.description, str(self.pr_number), log_entry.type)
            for log_entry in self.changes
        ]

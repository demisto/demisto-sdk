from enum import Enum
from typing import Dict, List, Tuple, Union

from pydantic import BaseModel, validator

INITIAL_TYPE_CONSTANT = "<fix|feature|breaking>"

INITIAL_LOG: Dict[str, Union[str, List[dict]]] = {
    "logs": [
        {
            "description": "enter description about this PR",
            "type": INITIAL_TYPE_CONSTANT,
        }
    ]
}


class LogType(str, Enum):
    fix = "fix"
    feature = "feature"
    breaking = "breaking"
    initial = INITIAL_TYPE_CONSTANT


class LogEntry(BaseModel):
    description: str
    type: LogType

    class Config:
        """Pydantic config class"""

        use_enum_values = True

    @validator("type")
    def is_type_initial_mode(cls, value):
        if value == INITIAL_TYPE_CONSTANT:
            raise ValueError(
                "One of the types is still not different from the initial value, please edit it"
            )
        return value

    @validator("description")
    def is_description_initial_mode(cls, value):
        if value == "enter description about this PR":
            raise ValueError(
                "One of the descriptions is still not different from the initial value, please edit it"
            )
        return value


class LogObject(BaseModel):
    logs: List[LogEntry]
    pr_number: str

    def build_log(cls) -> Tuple[List[str], ...]:
        breaking_logs: List[str] = []
        feature_logs: List[str] = []
        fix_logs: List[str] = []
        for log in cls.logs:
            if log.type == LogType.breaking:
                breaking_logs.append(
                    f"* {log.description} - [#{cls.pr_number}](https://github.com/demisto/demisto-sdk/pull/{cls.pr_number})\n"
                )
            elif log.type == LogType.feature:
                feature_logs.append(
                    f"* {log.description} - [#{cls.pr_number}](https://github.com/demisto/demisto-sdk/pull/{cls.pr_number})\n"
                )
            elif log.type == LogType.fix:
                fix_logs.append(
                    f"* {log.description} - [#{cls.pr_number}](https://github.com/demisto/demisto-sdk/pull/{cls.pr_number})\n"
                )
        return breaking_logs, feature_logs, fix_logs

from enum import Enum

from pydantic import BaseModel


class ChangelogType(str, Enum):
    fix = "fix"
    feature = "feature"
    breaking = "breaking"


class ChangelogObject(BaseModel):
    description: str
    type: ChangelogType

    class Config:
        """Pydantic config class"""

        use_enum_values = True

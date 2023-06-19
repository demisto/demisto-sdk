import enum
from pathlib import Path
from typing import NamedTuple, Optional, Union


class LinterType(str, enum.Enum):
    RUFF = "Ruff"
    FLAKE8 = "Flake8"
    MYPY = "Mypy"
    VULTURE = "Vulture"


class ErrorType(enum.Enum):
    ERROR = enum.auto()
    WARNING = enum.auto()


class LinterError(NamedTuple):
    error_code: str
    path: Path
    row_start: int
    error_message: str
    error_type: Optional[ErrorType] = None
    row_end: Optional[int] = None
    col_start: Optional[int] = None
    col_end: Optional[int] = None

    def __str__(self) -> str:
        return f"{self.path}:{self.row_end} [{self.error_code}]"


class BaseParser:
    linter_type: LinterType

    @staticmethod
    def parse_single(raw: Union[str, dict]) -> LinterError:
        ...


class RuffParser(BaseParser):
    linter_type = LinterType.RUFF

    @staticmethod
    def parse_single(raw: Union[str, dict]) -> LinterError:
        if not isinstance(raw, dict):
            raise ValueError(f"input must be a dictionary, got {raw}")

        return LinterError(
            error_code=raw["code"],
            row_start=raw["location"]["row"],
            col_start=raw["location"]["column"],
            row_end=raw["end_location"]["row"],
            col_end=raw["end_location"]["column"],
            path=Path(raw["filename"]),
            error_message=raw["message"],
        )

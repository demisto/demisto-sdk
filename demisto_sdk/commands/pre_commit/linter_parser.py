import enum
from pathlib import Path
from typing import NamedTuple, Optional, Union


class LinterType(str, enum.Enum):
    RUFF = "Ruff"
    FLAKE8 = "Flake8"
    MYPY = "Mypy"
    VULTURE = "Vulture"


class ViolationType(enum.Enum):
    ERROR = enum.auto()
    WARNING = enum.auto()


class LinterViolation(NamedTuple):
    error_code: str
    path: Path
    row_start: int
    message: str
    violation_type: Optional[ViolationType] = None
    is_autofixable: Optional[bool] = None
    fix_suggestion: Optional[str] = None
    row_end: Optional[int] = None
    col_start: Optional[int] = None
    col_end: Optional[int] = None

    def __str__(self) -> str:
        fix_suggestion_suffix = (
            f" (Fix: {self.fix_suggestion})" if self.fix_suggestion else ""
        )
        return f"{self.path}:{self.row_start} [{self.error_code}] {self.message}{fix_suggestion_suffix}"


class BaseParser:
    linter_type: LinterType

    @staticmethod
    def parse_single(raw: Union[str, dict]) -> LinterViolation:
        raise NotImplementedError


class RuffParser(BaseParser):
    linter_type = LinterType.RUFF

    @staticmethod
    def parse_single(raw: Union[str, dict]) -> LinterViolation:
        if not isinstance(raw, dict):
            raise ValueError(f"input must be a dictionary, got {type(raw)} {raw}")

        return LinterViolation(
            error_code=raw["code"],
            row_start=raw["location"]["row"],
            col_start=raw["location"]["column"],
            row_end=raw["end_location"]["row"],
            col_end=raw["end_location"]["column"],
            path=Path(raw["filename"]),
            message=raw["message"],
            fix_suggestion=raw.get("fix", {})[
                "message"
            ],  # TODO too safe vs not safe enough
            is_autofixable=bool(raw["fix"]),  # TODO check docs
        )

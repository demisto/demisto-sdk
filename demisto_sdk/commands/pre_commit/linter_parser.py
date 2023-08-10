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
    linter_name: str
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

    def to_github_annotation(self) -> str:
        prefix = "warning" if self.violation_type == ViolationType.WARNING else "error"
        endline = self.row_end if self.row_end is not None else self.row_start
        suffix = f"\n{self.fix_suggestion}" if self.fix_suggestion else ""
        return f"::{prefix} file={self.path},line={self.row_start},endline={endline},title={self.linter_name}:{self.error_code}{suffix}".replace(
            "\n", "%0A"
        )


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
            linter_name=RuffParser.linter_type,
            error_code=raw["code"],
            row_start=raw["location"]["row"],
            col_start=raw["location"]["column"],
            row_end=raw["end_location"]["row"],
            col_end=raw["end_location"]["column"],
            path=Path(raw["filename"]),
            message=raw["message"],
            fix_suggestion=raw.get("fix", {}).get("message"),
            is_autofixable=bool(raw["fix"]),  # TODO check docs
        )

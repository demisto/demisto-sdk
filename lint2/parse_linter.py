import enum
from pathlib import Path
import re
from typing import NamedTuple, Optional, Union


class LinterType(str, enum.Enum):
    RUFF = "Ruff"
    FLAKE8 = "Flake8"
    MYPY = "Mypy"


class ErrorType(enum.Enum):
    ERROR = enum.auto()
    WARNING = enum.auto()


class ParseResult(NamedTuple):
    error_code: str
    path: Path
    row_start: int
    error_message: str
    error_type: Optional[ErrorType] = None
    row_end: Optional[int] = None
    col_start: Optional[int] = None
    col_end: Optional[int] = None


class BaseParser:
    linter_type: LinterType

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        ...


class RuffParser(BaseParser):
    linter_type = LinterType.RUFF

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        if not isinstance(raw, dict):
            raise ValueError(f"must be a dictionary, got {raw}")

        return ParseResult(
            error_code=raw["code"],
            row_start=raw["location"]["row"],
            col_start=raw["location"]["column"],
            row_end=raw["end_location"]["row"],
            col_end=raw["end_location"]["column"],
            path=Path(raw["filename"]),
            error_message=raw["message"],
        )


class Flake8Parser(BaseParser):
    linter_type = LinterType.FLAKE8

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        if not isinstance(raw, dict):
            raise ValueError(f"must be a dictionary, got {raw}")
        return ParseResult(
            error_code=raw["code"],
            row_start=raw["line_number"],
            error_message=raw["text"],
            path=Path(raw["filename"]),
            error_type=None,
            row_end=None,
            col_start=raw.get("column_number"),
            col_end=None,
        )


class MypyParser(BaseParser):
    linter_type = LinterType.MYPY
    _line_regex = re.compile(
        r"^(?P<path>[^:]+?):(?P<row_start>\d+):(?P<col_start>\d+):(?P<row_end>\d+):(?P<col_end>\d+):(?P<error_type>[\w\s]+):(?P<error_message>[^\:\[]+)\[(?P<error_code>[^\]]+)]$"
    )

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        if not isinstance(raw, str):
            raise ValueError(f"must be a string, got {raw}")

        if not (match := MypyParser._line_regex.match(raw)):
            raise ValueError(f"did not match on {raw}")

        match_dict = match.groupdict()

        raw_error_type = match_dict["error_type"]
        if "error" in raw_error_type:
            error_type = ErrorType.ERROR
        elif "warning" in raw_error_type:
            error_type = ErrorType.WARNING
        else:
            error_type = None

        return ParseResult(
            error_code=match_dict["error_code"],
            row_start=int(match_dict["row_start"]),
            row_end=int(match_dict["row_end"]),
            col_start=int(match_dict["col_start"]),
            col_end=int(match_dict["col_end"]),
            path=Path(match_dict["path"]),
            error_type=error_type,
            error_message=match_dict["error_message"],
        )

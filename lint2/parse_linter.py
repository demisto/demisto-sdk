import enum
from pathlib import Path
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
            error_code=raw['code'],
            row_start=raw['location']['row'],
            col_start=raw['location']['column'],
            row_end=raw['end_location']['row'],
            col_end=raw['end_location']['column'],
            path=Path(raw['filename']),
            error_message=raw['message'],
        )


class Flake8Parser(BaseParser):
    linter_type = LinterType.FLAKE8

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        ...


class MypyParser(BaseParser):
    linter_type = LinterType.MYPY

    @staticmethod
    def parse_line(raw: Union[str, dict]) -> ParseResult:
        if not isinstance(raw, str):
            raise ValueError(f"must be a string, got {raw}")

        """Packs/ipinfo/Integrations/ipinfo_v2/ipinfo_v2.py:13: error: Incompatible types in assignment (expression has type "str", variable has type "int")"""
        if raw.count(":") != 3:
            raise ValueError("unexpected `:` count")
        path, line_start, error_type, error_description = raw.split(":")
        return ParseResult(
            error_code=
        )

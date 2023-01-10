from enum import Enum
from typing import NamedTuple, Optional, Union


class LinterType(str, Enum):
    RUFF = "Ruff"
    FLAKE8 = "Flake8"
    MYPY = "Mypy"


class ParseResult(NamedTuple):
    error_code: str
    row_start: int
    col_start: int
    error_message: str
    row_end: Optional[int] = None
    col_end: Optional[int] = None


class BaseParser:
    linter_type: LinterType

    @staticmethod
    def parse_line(line: Union[str, dict]) -> ParseResult:
        ...


class RuffParser(BaseParser):
    linter_type = LinterType.RUFF

    @staticmethod
    def parse_line(line: Union[str, dict]) -> ParseResult:
        if not isinstance(line, dict):
            raise ValueError(f"must be a dictionary, got {line}")
        ...


class Flake8Parser(BaseParser):
    linter_type = LinterType.FLAKE8

    @staticmethod
    def parse_line(line: Union[str, dict]) -> ParseResult:
        ...

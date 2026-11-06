"""Data models shared by the xsoar-linter checkers."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Rule:
    """A single xsoar-linter rule, e.g. E9003 (sleep-exists)."""

    code: str
    symbol: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.code.startswith("E")


@dataclass(frozen=True)
class Finding:
    """A rule violation found in a file."""

    line: int
    col: int
    code: str
    obj: str
    message: str

    def sort_key(self) -> tuple:
        return (self.line, self.col, self.code, self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "col": self.col,
            "code": self.code,
            "obj": self.obj,
            "message": self.message,
        }


@dataclass(frozen=True)
class LintSettings:
    """Per-file settings, taken from the integration/script yml."""

    support: Optional[str] = "base"
    is_script: bool = False
    long_running: bool = False
    py2: bool = False
    commands: List[str] = field(default_factory=list)


@dataclass
class LintResult:
    """The outcome of linting one file."""

    findings: List[Finding] = field(default_factory=list)
    fails: bool = False

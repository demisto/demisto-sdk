from pathlib import Path
from typing import List, Optional

from git import GitCommandError


class UnknownFileException(ValueError):
    def __init__(self, path: Path):
        super().__init__(f"file {path} is unknown")


class GitFileReadError(ValueError):
    def __init__(self, path: Path, tag: str, exc: GitCommandError):
        self.__git_command_error = exc
        super().__init__(
            f"file {path} could not be read from branch/commit {tag} using command {exc.command}, full error:\n{exc}"
        )

    @property
    def command(self) -> List[str]:
        return self.__git_command_error.command


class GitFileNotFoundError(FileNotFoundError):
    def __init__(self, path: Path, tag: str, remote: Optional[str] = None):
        if remote:
            tag = f"{remote}:{tag}"
        super().__init__(f"file {path} does not exist at branch/commit {tag}")

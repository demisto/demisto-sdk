from pathlib import Path


class UnknownFileError(ValueError):
    def __init__(self, path: Path):
        super().__init__(f"file {path} is unknown")


class FileReadError(IOError):
    def __init__(self, path: Path, exc: Exception):
        super().__init__(f"file {path} could not be read, full error:\n{exc}")

from pathlib import Path


class FileReadError(IOError):
    def __init__(self, path: Path, exc: Exception):
        super().__init__(f"file {path} could not be read, full error:\n{exc}")


class UnknownFileError(FileReadError, ValueError):
    def __init__(self, path: Path):
        super().__init__(f"file {path} has unknown format")


class InvalidFileUrlError(FileReadError, ValueError):
    def __init__(self, url: str):
        super().__init__(f"URL {url} is not a valid URL")

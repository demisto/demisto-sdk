from pathlib import Path


class FileReadError(IOError):
    """
    Base class for errors reading files
    """
    def __init__(self, message: str, exc: Exception):
        super().__init__(message)
        self.original_exc = exc


class FileWriteError(IOError):
    def __init__(self, path: Path, exc: Exception):
        self.original_exc = exc
        super().__init__(f"could not write file {path}, full error:\n{exc}")


class LocalFileReadError(FileReadError):
    """
    Raised when there was an issue reading files from local file system.
    """
    def __init__(self, path: Path, exc: Exception):
        super().__init__(f"file {path} could not be read, error:\n{exc}", exc=exc)


class MemoryFileReadError(FileReadError):
    """
    Raised when there was an issue reading files from memory (as bytes)
    """
    def __init__(self, exc: Exception):
        super().__init__(f"file could not be read, error:\n{exc}", exc=exc)


class GitFileReadError(FileReadError):
    """
    Raised when there was an issue reading files from git (from remote/locally)
    """
    def __init__(self, path: Path, tag: str, exc: Exception):
        super().__init__(
            f"Could not get file {path} from branch/commit {tag}, error:\n{exc}",
            exc=exc,
        )


class HttpFileReadError(FileReadError):
    """
    Raised when there was an issue retrieving a file via http-request / api call
    """
    def __init__(self, url: str, exc: Exception):
        super().__init__(f"Could not read file from {url}, full error:\n{exc}", exc=exc)


class UnknownFileError(ValueError):
    """
    Raised when failing to automatically detect subclass of File object dynamically by file's suffix/name
    """
    pass

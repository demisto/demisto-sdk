from pathlib import Path


class FileReadError(IOError):
    pass


class LocalFileReadError(FileReadError):
    def __init__(self, path: Path, exc: Exception):
        self.original_exc = exc
        super().__init__(f"file {path} could not be read, full error:\n{exc}")


class FileContentReadError(FileReadError):
    def __init__(self, file_content: bytes, exc: Exception):
        super().__init__(f"file {file_content} could not be read, full error:\n{exc}")


class GitFileReadError(FileReadError):
    def __init__(self, path: Path, tag: str, exc: Exception):
        super().__init__(
            f"Could not get file {path} from branch/commit {tag}, full_error:\n{exc}"
        )


class HttpFileReadError(IOError):
    def __init__(self, url: str, exc: Exception):
        super().__init__(f"Could not read file from {url} url, full error:\n{exc}")


class UnknownFileError(FileReadError, ValueError):
    def __init__(self, path: Path):
        super().__init__(f"file {path} has unknown format")

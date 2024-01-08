from pathlib import Path


class FileReadError(IOError):
    pass


class FileWriteError(IOError):
    def __init__(self, path: Path, exc: Exception):
        super().__init__(f"could not write file {path}, full error:\n{exc}")


class LocalFileReadError(FileReadError):
    def __init__(self, path: Path, exc: Exception):
        self.original_exc = exc
        super().__init__(f"file {path} could not be read, full error:\n{exc}")


class FileContentReadError(FileReadError):
    def __init__(self, exc: Exception):
        super().__init__(f"file could not be read, full error:\n{exc}")


class GitFileReadError(FileReadError):
    def __init__(self, path: Path, tag: str, exc: Exception):
        super().__init__(
            f"Could not get file {path} from branch/commit {tag}, full_error:\n{exc}"
        )


class HttpFileReadError(IOError):
    def __init__(self, url: str, exc: Exception):
        super().__init__(f"Could not read file from {url}, full error:\n{exc}")


class UnknownFileError(ValueError):
    pass

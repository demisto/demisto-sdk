from pathlib import Path
from typing import Optional, Sequence


class FailedUploadException(RuntimeError):
    def __init__(
        self,
        path: Path,
        response_body: dict,
        status_code: Optional[int] = None,
    ) -> None:
        if status_code is not None:
            error = f"Failed uploading {path}, {status_code=}, {response_body=}"
        else:
            error = f"Failed uploading {path}, {response_body=}"
        super().__init__(error)


class FailedUploadMultipleException(RuntimeError):
    def __init__(self, failures: Sequence[FailedUploadException]) -> None:
        self.failures = failures
        super().__init__(self.failures)

    def __str__(self) -> str:
        return "\n".join(
            "Failed uploading multiple content items:",
            *[str(failure) for failure in self.failures],
        )

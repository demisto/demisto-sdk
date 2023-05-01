from pathlib import Path
from typing import Sequence


class FailedUploadException(RuntimeError):
    def __init__(
        self,
        path: Path,
        response_body: dict,
        status_code: int,
    ) -> None:
        super().__init__(f"Failed uploading {path}, {status_code=}, {response_body=}")


class FailedUploadMultipleException(RuntimeError):
    def __init__(self, failures: Sequence[FailedUploadException]) -> None:
        self.failures = failures
        super().__init__(self.failures)

    def __str__(self) -> str:
        return "\n".join(
            "Failed uploading multiple content items:",
            *[str(failure) for failure in self.failures],
        )

from pathlib import Path
from typing import Optional, Sequence


class FailedUploadException(RuntimeError):
    def __init__(
        self,
        path: Path,
        response_body: dict,
        status_code: Optional[int] = None,
        additional_info: Optional[str] = None,
    ) -> None:
        self.path = path
        self.response_body = response_body
        self.status_code = status_code
        self.additional_info = additional_info

        super().__init__(
            "\n".join(
                (
                    additional_info or "",
                    f"{status_code=}" if status_code else "",
                    f"{response_body=}" if response_body else "",
                )
            )
        )


class FailedUploadMultipleException(RuntimeError):
    def __init__(self, failures: Sequence[FailedUploadException]) -> None:
        self.failures = failures
        super().__init__(self.failures)

    def __str__(self) -> str:
        return "\n".join(str(failure) for failure in self.failures)

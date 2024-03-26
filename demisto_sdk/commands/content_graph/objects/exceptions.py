from pathlib import Path
from typing import TYPE_CHECKING, Optional, Sequence

from demisto_sdk.commands.upload.exceptions import IncompatibleUploadVersionException

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


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
    def __init__(
        self,
        uploaded_successfully: Sequence["ContentItem"],
        upload_failures: Sequence[FailedUploadException],
        incompatible_versions_items: Sequence[IncompatibleUploadVersionException],
    ) -> None:
        self.uploaded_successfully = uploaded_successfully
        self.upload_failures = upload_failures
        self.incompatible_versions_items = incompatible_versions_items
        super().__init__((self.upload_failures, self.incompatible_versions_items))

    def __str__(self) -> str:
        new_line = "\n"
        return f"""Upload Failures: {new_line.join(str(failure) for failure in self.upload_failures)}{new_line}Incompatible versions: {new_line.join(str(item) for item in self.incompatible_versions_items)}"""

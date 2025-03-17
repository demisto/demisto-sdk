import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.exceptions import FailedUploadException

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.common import ContentType


def parse_upload_response(response: Any, path: Path, content_type: "ContentType"):
    if (
        isinstance(response, dict) and len(response) == 2 and "error" in response
    ):  # response format: {"response": {...}, "error": <empty string if ok>}
        if response["error"]:
            raise FailedUploadException(path=path, response_body=response)
    elif (isinstance(response, tuple) and len(response)) == 3:
        (
            data,
            status_code,
            _,
        ) = response  # third output is headers, not used here
        if status_code > 299:
            raise FailedUploadException(
                path=path,
                response_body=data,
                status_code=status_code,
            )
    else:
        response_str = (
            f"(could not convert response of type {type(response)} to string)"
        )
        with contextlib.suppress(Exception):
            response_str = str(response)
        logger.debug(  # noqa: PLE1205
            "{}",
            f"got the following response when uploading {content_type} {path}: {response_str}",
        )


def parse_error_response(error: ApiException) -> str:
    """
    Parses error message from exception raised in call to client to upload a file

    error (ApiException): The exception which was raised in call in to client
    """
    if isinstance(error, KeyboardInterrupt):
        return "Aborted due to keyboard interrupt."

    if hasattr(error, "reason"):
        reason = str(error.reason)
        if "[SSL: CERTIFICATE_VERIFY_FAILED]" in reason:
            return (
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n"
                "Run the command with the --insecure flag."
            )

        elif "Failed to establish a new connection:" in reason:
            return (
                "Failed to establish a new connection: Connection refused.\n"
                "Check the BASE url configuration."
            )

        elif reason in ("Bad Request", "Forbidden"):
            error_body = json.loads(error.body)
            message = next(
                (
                    error_body.get(key)
                    for key in ["error", "detail", "title"]
                    if error_body.get(key)
                ),
                "",
            )
            if message.startswith("[") and message.endswith("]"):
                message = message[1:-1]

            if error_body.get("status") == 403:
                message += "\nTry checking your API key configuration."
            return message
        return reason
    return str(error)

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry


class MarkdownResult:
    """
    This class represents a response object from the node server
    """

    def __init__(self, resp):
        self.has_errors = resp["errorNum"] != 0
        self.validations = resp["validations"]
        self.fixed_text = resp["fixedText"]


def run_markdownlint(file_content: str, file_path="file", fix=False) -> MarkdownResult:
    """
    This function makes a request to the node server to check markdown lint validations
    Args:
        file_content: The markdown content to check. Will be the request body
        file_path: The name of the file to display in the validation results
        fix: Whether to fix the results, and return the fixed text in the fixed_text field. If provided, the validations
        returned will be the validations that are left over that could not be fixed

    Returns: A MarkdownResult object response for the given request

    """
    retry = Retry(total=2)
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)

    return MarkdownResult(
        session.request(
            "POST",
            f"http://localhost:6161/markdownlint?filename={file_path}&fix={fix}",
            data=file_content.encode("utf-8"),
            timeout=20,
        ).json()
    )

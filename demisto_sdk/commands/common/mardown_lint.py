import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry


class MarkdownResult:
    def __init__(self, resp):
        self.has_errors = resp['errorNum'] != 0
        self.validations = resp['validations']
        self.fixed_text = resp['fixedText']


def run_markdownlint(file_content: str, file_path='file', fix=False) -> MarkdownResult:
    retry = Retry(total=2)
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('http://', adapter)

    return MarkdownResult(session.request(
        'POST',
        f'http://localhost:6161/markdownlint?filename={file_path}&fix={fix}',
        data=file_content.encode('utf-8'),
        timeout=20
    ).json())

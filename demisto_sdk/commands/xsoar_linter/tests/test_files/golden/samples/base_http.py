"""Docstring that mentions http://example.com in the middle."""

"""http://string-expression-statement.example.com"""

URL = "http://example.com"
SECURE = "https://example.com"
UPPER = "HTTP://example.com"
RAW_BYTES = b"http://example.com"
TEXT = "see http://example.com"
host = "h"
FORMATTED = f"http://{host}/api"
CONCAT = "http://" + host
SCHEME_ONLY = "http:"
# http://in-a-comment.example.com


def helper(url: str = "http://default.example.com") -> str:
    return url

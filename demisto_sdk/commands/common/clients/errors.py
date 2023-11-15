import requests


class UnAuthorized(RuntimeError):
    def __init__(self, message: str, status_code: int = requests.codes.unauthorized):
        super().__init__(f"Unauthorized: {message} - code {status_code}")

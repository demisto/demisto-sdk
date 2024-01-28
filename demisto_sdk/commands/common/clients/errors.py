import requests


class UnAuthorized(RuntimeError):
    def __init__(self, message: str, status_code: int = requests.codes.unauthorized):
        super().__init__(f"Unauthorized: {message} - code {status_code}")


class UnHealthyServer(RuntimeError):
    def __init__(self, server_type: str, server_part: str):
        super().__init__(f"The {server_part} part of {server_type} is unhealthy")

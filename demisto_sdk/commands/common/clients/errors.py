import requests


class UnAuthorized(RuntimeError):
    def __init__(self, message: str, status_code: int = requests.codes.unauthorized):
        super().__init__(f"Unauthorized: {message} - code {status_code}")


class UnHealthyServer(RuntimeError):
    def __init__(self, server: str):
        super().__init__(f"The {server} is unhealthy")


class InvalidServerType(ValueError):
    def __init__(self, server: str, server_type: str):
        super().__init__(f"The server {server} is not type of {server_type}")

from typing import Iterable, Optional

import requests


class UnAuthorized(RuntimeError):
    def __init__(self, message: str, status_code: int = requests.codes.unauthorized):
        super().__init__(f"Unauthorized: {message} - code {status_code}")


class UnHealthyServer(RuntimeError):
    def __init__(self, server: str):
        super().__init__(f"The {server} is unhealthy")


class InvalidServerType(ValueError):
    def __init__(self, server: str, server_type: str):
        super().__init__(f"The server {server} is not {server_type} server")


class PollTimeout(RuntimeError):
    def __init__(
        self,
        current_state_message: str,
        expected_states: Iterable[str],
        timeout: int,
        reason: Optional[str] = None,
    ):
        error = f"{current_state_message}, expected to be in state(s)={expected_states} after {timeout}=seconds"
        if reason:
            error = f"{error}, reason={reason}"

        super().__init__(error)

import json


from typing import Any, Callable, Dict, Tuple

import dateparser
import demistomock as demisto
import requests
from CommonServerPython import *
from CommonServerUserPython import *

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()


class Client(BaseClient):
    """
    Client to use in the integration, overrides BaseClient.
    Used for communication with the api.
    """

    def __init__(
        self, url: str, username: str, password: str, verify: bool, proxy: bool
    ):
        super().__init__(base_url=f"{url}/api", verify=verify, proxy=proxy)
        self._url = url
        self._username = username
        self._password = password


def test_module(client: Client, *_) -> Tuple[str, dict, dict]:
    """Function which checks if there is a connection with the api.
     Args:
         client : Integration client which communicates with the api.
         args: Users arguments of the command.
    Returns:
        human readable, context, raw response of this command.
    """
    return "ok", {}, {}


def parse_incidents(
    items: list, fetch_limit: str, time_format: str, parsed_last_time: datetime
) -> Tuple[list, Any]:
    """
    This function will create a list of incidents
    Args:
        items : List of tickets of the api response.
        fetch_limit: Limit for incidents of fetch cycle.
        time_format: Time format of the integration.
        parsed_last_time: limit for number of fetch incidents per fetch.
    Returns:
        incidents: List of incidents.
        parsed_last_time: Time of last incident.
    """
    count = 0
    incidents = []
    for item in items:
        if count >= int(fetch_limit):
            break

        incident_created_time = dateparser.parse(item["created"])

        incident = {
            "name": item["title"],
            "occurred": incident_created_time.strftime(time_format),
            "rawJSON": json.dumps(item),
        }
        return_error("error")
        incidents.append(incident)
        count += 1
        parsed_last_time = incident_created_time
    return incidents, parsed_last_time


def fetch_incidents():
    return []


def main():
    """
    PARSE AND VALIDATE INTEGRATION PARAMS
    """
    params = demisto.params()
    username = params.get("credentials").get("identifier")
    password = params.get("credentials").get("password")
    base_url = params.get("url")
    proxy = demisto.params().get("proxy", False)
    verify_certificate = not params.get("insecure", False)

    client = Client(
        url=base_url,
        username=username,
        password=password,
        verify=verify_certificate,
        proxy=proxy,
    )
    command = demisto.command()
    LOG(f"Command being called is {command}")
    # Commands dict
    commands: Dict[str, Callable[[Client, Dict[str, str]], Tuple[str, dict, dict]]] = {
        "test-module": test_module,
    }
    if command in commands:
        return_outputs(*commands[command](client, demisto.args()))
    elif command == "fetch-incidents":
        incidents = fetch_incidents()
        demisto.incidents(incidents)
        demisto.results(incidents)
    else:
        raise NotImplementedError(f"{command} is not an existing QuestKace command")
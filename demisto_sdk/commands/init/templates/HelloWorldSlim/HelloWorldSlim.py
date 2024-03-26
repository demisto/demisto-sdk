""" HelloWorldSlim integration for Cortex XSOAR (aka Demisto)

This is a slim version of our HelloWorld integration, which supplies a good example on how you can build a Cortex
XSOAR Integration using Python 3. This slim version is intended only to demonstrate the structure of a basic integration,
containing the Client class, test module, and integration commands.
For any other uses of an integration, see the original HelloWorld integration.

The HelloWorldSlim resembles an integration that can retrive an alert from the api using the alert's id, and can also
modify the alert's status.

"""
import urllib3
from typing import Any, Dict


import demistomock as demisto  # noqa: E402 lgtm [py/polluting-import]
from CommonServerPython import *  # noqa: E402 lgtm [py/polluting-import]
from CommonServerUserPython import *  # noqa: E402 lgtm [py/polluting-import]

# Disable insecure warnings
urllib3.disable_warnings()


class Client(BaseClient):  # type: ignore
    """Client class to interact with the service API

    This Client implements API calls, and does not contain any Demisto logic.
    Should only do requests and return data.
    It inherits from BaseClient defined in CommonServer Python.
    Most calls use _http_request() that handles proxy, SSL verification, etc.
    """

    def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """
        Gets a specific HelloWorld alert by id
        Args:
            alert_id: id of the alert to return

        Returns:
            dict containing the alert as returned from the API
        """

        return self._http_request(
            method="GET", url_suffix="/get_alert_details", params={"alert_id": alert_id}
        )

    def update_alert_status(self, alert_id: str, alert_status: str) -> Dict[str, Any]:
        """
        Changes the status of a specific HelloWorld alert
        Args:
            alert_id: id of the alert to return
            alert_status: new alert status. Options are: 'ACTIVE' or 'CLOSED'

        Returns:
            dict containing the alert as returned from the API

        """

        return self._http_request(
            method="GET",
            url_suffix="/change_alert_status",
            params={"alert_id": alert_id, "alert_status": alert_status},
        )


def test_module(client: Client) -> str:
    """
    Tests API connectivity and authentication
    Args:
        client: HelloWorldSlim client to use

    Returns:
        'ok' if test passed, anything else will fail the test.
    """

    try:
        client.get_alert(alert_id="0")
    except DemistoException as e:
        if "Forbidden" in str(e):
            return "Authorization Error: make sure API Key is correctly set"
        else:
            raise e
    return "ok"


def get_alert_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """
    helloworldslim-get-alert command: Returns a HelloWorldSlim alert
    Args:
        client: HelloWorldSlim client to use
        args: all command arguments, usually passed from ``demisto.args()``.
        ``args['alert_id']`` alert ID to return

    Returns:
        A ``CommandResults`` object that is then passed to ``return_results``,
        that contains an alert

    """

    alert_id = args.get("alert_id", None)
    if not alert_id:
        raise ValueError("alert_id not specified")

    alert = client.get_alert(alert_id=alert_id)

    # INTEGRATION DEVELOPER TIP
    # We want to convert the "created" time from timestamp(s) to ISO8601 as
    # Cortex XSOAR customers and integrations use this format by default
    if "created" in alert:
        created_time_ms = int(alert.get("created", "0")) * 1000
        alert["created"] = timestamp_to_datestring(created_time_ms)

    # tableToMarkdown() is defined is CommonServerPython.py and is used very
    # often to convert lists and dicts into a human readable format in markdown
    readable_output = tableToMarkdown(f"HelloWorldSlim Alert {alert_id}", alert)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="HelloWorldSlim.Alert",
        outputs_key_field="alert_id",
        outputs=alert,
    )


def update_alert_status_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    """
    helloworldslim-update-alert-status command: Changes the status of an alert

    Args:
        client: HelloWorldSlim client to use
        args: all command arguments, usually passed from ``demisto.args()``.
        ``args['alert_id']`` alert ID to update
        ``args['status']`` new status, either ACTIVE or CLOSED

    Returns:
        A ``CommandResults`` object that is then passed to ``return_results``,
        that contains an updated alert
    """

    alert_id = args.get("alert_id", None)
    if not alert_id:
        raise ValueError("alert_id not specified")

    status = args.get("status", None)
    if status not in ("ACTIVE", "CLOSED"):
        raise ValueError("status must be either ACTIVE or CLOSED")

    alert = client.update_alert_status(alert_id, status)

    # INTEGRATION DEVELOPER TIP
    # We want to convert the "updated" time from timestamp(s) to ISO8601 as
    # Cortex XSOAR customers and integrations use this format by default
    if "updated" in alert:
        updated_time_ms = int(alert.get("updated", "0")) * 1000
        alert["updated"] = timestamp_to_datestring(updated_time_ms)

    # tableToMarkdown() is defined is CommonServerPython.py and is used very
    # often to convert lists and dicts into a human readable format in markdown
    readable_output = tableToMarkdown(f"HelloWorldSlim Alert {alert_id}", alert)

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="HelloWorldSlim.Alert",
        outputs_key_field="alert_id",
        outputs=alert,
    )


def main() -> None:
    api_key = demisto.params().get("apikey")

    # get the service API url
    base_url = urljoin(demisto.params()["url"], "/api/v1")

    # if your Client class inherits from BaseClient, SSL verification is
    # handled out of the box by it, just pass ``verify_certificate`` to
    # the Client constructor
    verify_certificate = not demisto.params().get("insecure", False)

    # if your Client class inherits from BaseClient, system proxy is handled
    # out of the box by it, just pass ``proxy`` to the Client constructor
    proxy = demisto.params().get("proxy", False)
    command = demisto.command()

    demisto.debug(f"Command being called is {command}")
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        client = Client(
            base_url=base_url, verify=verify_certificate, headers=headers, proxy=proxy
        )

        if command == "test-module":
            # This is the call made when pressing the integration Test button.
            result = test_module(client)
            return_results(result)

        elif command == "helloworldslim-get-alert":
            return_results(get_alert_command(client, demisto.args()))

        elif command == "helloworldslim-update-alert-status":
            return_results(update_alert_status_command(client, demisto.args()))

    # Log exceptions and return errors
    except Exception as e:
        return_error(f"Failed to execute {command} command.\nError:\n{str(e)}", error=e)


if __name__ in ("__main__", "__builtin__", "builtins"):  # pragma: no cover
    main()

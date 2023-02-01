"""HelloWorldSlim Integration for Cortex XSOAR - Unit Tests file

This file contains the Unit Tests for the HelloWorldSlim Integration based
on pytest.

More information about Unit Tests in Cortex XSOAR:
https://xsoar.pan.dev/docs/integrations/unit-testing

"""

from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


def util_load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())


def test_get_alert(requests_mock):
    """Tests helloworld-get-alert command function.

    Configures requests_mock instance to generate the appropriate
    get_alerts API response, loaded from a local JSON file. Checks
    the output of the command function with the expected output.
    """
    from HelloWorldSlim import Client, get_alert_command

    mock_response = util_load_json("test_data/get_alert.json")
    requests_mock.get(
        "https://test.com/api/v1/get_alert_details?alert_id=695b3238-05d6-4934-86f5-9fff3201aeb0",
        json=mock_response,
    )

    client = Client(
        base_url="https://test.com/api/v1",
        verify=False,
        headers={"Authentication": "Bearer some_api_key"},
    )

    args = {
        "alert_id": "695b3238-05d6-4934-86f5-9fff3201aeb0",
    }

    response = get_alert_command(client, args)

    # We modify the timestamp from the raw mock_response of the API, because the
    # integration changes the format from timestamp to ISO8601.
    mock_response["created"] = "2020-04-17T14:43:59.000Z"

    assert response.outputs == mock_response
    assert response.outputs_prefix == "HelloWorld.Alert"
    assert response.outputs_key_field == "alert_id"


def test_update_alert_status(requests_mock):
    """Tests helloworld-update-alert-status command function.

    Configures requests_mock instance to generate the appropriate
    get_alerts API response, loaded from a local JSON file. Checks
    the output of the command function with the expected output.
    """
    from HelloWorld import Client, update_alert_status_command

    mock_response = util_load_json("test_data/update_alert_status.json")
    requests_mock.get(
        "https://test.com/api/v1/change_alert_status?alert_id=695b3238-05d6-4934-86f5-9fff3201aeb0&alert_status=CLOSED",
        json=mock_response,
    )

    client = Client(
        base_url="https://test.com/api/v1",
        verify=False,
        headers={"Authentication": "Bearer some_api_key"},
    )

    args = {"alert_id": "695b3238-05d6-4934-86f5-9fff3201aeb0", "status": "CLOSED"}

    response = update_alert_status_command(client, args)

    # We modify the timestamp from the raw mock_response of the API, because the
    # integration changes the format from timestamp to ISO8601.
    mock_response["updated"] = "2020-04-17T14:45:12.000Z"

    assert response.outputs == mock_response
    assert response.outputs_prefix == "HelloWorld.Alert"
    assert response.outputs_key_field == "alert_id"

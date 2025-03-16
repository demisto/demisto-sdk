from demisto_client.demisto_api import DefaultApi

from demisto_sdk.commands.common.clients import get_client_from_server_type
from demisto_sdk.commands.common.clients.xsiam.xsiam_api_client import XsiamClient

import pytest


@pytest.fixture()
def client(mocker, requests_mock):
    def _xsoar_request_side_effect(path: str, method: str, response_type: str = ""):
        if path == "/ioc-rules" and method == "GET":
            return None, 200, {"Content-Type": "application/json"}
        elif path == "/about" and method == "GET":
            return {}, 200, {"Content-Type": "application/json"}
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_request_side_effect
    )
    requests_mock.get(
        "https://test3.com/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )
    client = get_client_from_server_type(
        base_url="https://test3.com", api_key="test", auth_id="1"
    )
    return client


def test_search_alerts_by_uuid_complex(mocker, client):
    # Create mock responses for multiple calls
    alerts = [{"alert_id": "1", "description": "Description with uuid1"},
              {"alert_id": "2", "description": "Description with uuid2"},
              {"alert_id": "3", "description": "Description without uuid"},
              {"alert_id": "4", "description": "Description without uuid"},
              {"alert_id": "5", "description": "Description with uuid5"}]

    def return_alert(
                     filters: list = None,
                     search_from: int = None,
                     search_to: int = None,
                     sort: dict = None, ):
        resp_alerts = [alert for alert in alerts[search_from:search_to]]
        return {
            "alerts": resp_alerts,
            "result_count": len(resp_alerts),
            "total_count": len(alerts)
        }

    # Setup mock side effects for multiple calls
    mocker.patch.object(XsiamClient, 'search_alerts', side_effect=return_alert)

    # Mock the search_alerts_by_uuid method inputs
    alert_uuids = ["uuid1", "uuid2", "uuid4"]
    filters = ["filter1", "filter2"]
    page_size = 1

    # Call the method to test
    result = client.search_alerts_by_uuid(alert_uuids=alert_uuids, filters=filters, page_size=page_size)

    # Perform assertions on the result
    assert result == ["1", "2"]

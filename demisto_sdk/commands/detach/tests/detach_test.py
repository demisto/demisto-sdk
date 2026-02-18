import pytest
import typer
from pytest_mock import MockerFixture

from demisto_sdk.commands.detach.detach import detach_content_items


@pytest.mark.parametrize(
    "item_type, expected_endpoint",
    [
        pytest.param("IncidentTypes", "/incidenttype/detach/item1", id="IncidentTypes"),
        pytest.param("Layouts", "/layout/item1/detach", id="Layouts"),
        pytest.param("Playbooks", "/playbook/detach/item1", id="Playbooks"),
        pytest.param("Scripts", "/automation/detach/item1", id="Scripts"),
    ],
)
def test_detach_content_items_all_types(
    mocker: MockerFixture, item_type: str, expected_endpoint: str
):
    """
    Given:
        - ids: A list of item IDs to detach.
        - item_type: The type of the items.
    When:
        - Running detach_content_items with various item types.
    Then:
        - Ensure the generic_request is called with the correct endpoint and method.
    """
    mock_client = mocker.patch("demisto_client.configure")
    mock_generic_request = mock_client.return_value.generic_request

    ids = ["item1"]

    detach_content_items(ids=ids, item_type=item_type)

    assert mock_generic_request.call_count == 1
    mock_generic_request.assert_any_call(expected_endpoint, "POST")


def test_detach_content_items_non_existent_type(mocker: MockerFixture):
    """
    Given:
        - ids: A list of item IDs to detach.
        - item_type: A non-existent item type.
    When:
        - Running detach_content_items.
    Then:
        - Ensure that it raises typer.Exit(code=1) as per implementation.
    """
    mocker.patch("demisto_client.configure")

    ids = ["item1"]
    item_type = "NonExistentType"

    with pytest.raises(typer.Exit) as excinfo:
        detach_content_items(ids=ids, item_type=item_type)

    assert excinfo.value.exit_code == 1

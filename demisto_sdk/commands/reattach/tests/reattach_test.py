import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.reattach.reattach import reattach_content_items


@pytest.mark.parametrize(
    "item_type, expected_endpoint",
    [
        pytest.param("IncidentTypes", "/incidenttype/attach/item1", id="IncidentTypes"),
        pytest.param("Layouts", "/layout/item1/attach", id="Layouts"),
        pytest.param("Playbooks", "/playbook/attach/item1", id="Playbooks"),
        pytest.param("Scripts", "/automation/attach/item1", id="Scripts"),
    ],
)
def test_reattach_content_items_all_types(
    mocker: MockerFixture, item_type: str, expected_endpoint: str
):
    """
    Given:
        - ids: A list of item IDs to reattach.
        - item_type: The type of the items.
    When:
        - Running reattach_content_items with various item types.
    Then:
        - Ensure the generic_request is called with the correct endpoint and method.
    """
    mock_client = mocker.patch("demisto_client.configure")
    mock_generic_request = mock_client.return_value.generic_request

    ids = ["item1"]

    reattach_content_items(ids=ids, item_type=item_type)

    assert mock_generic_request.call_count == 1
    mock_generic_request.assert_any_call(expected_endpoint, "POST")


def test_reattach_content_items_non_existent_type(mocker: MockerFixture):
    """
    Given:
        - ids: A list of item IDs to reattach.
        - item_type: A non-existent item type.
    When:
        - Running reattach_content_items.
    Then:
        - Ensure that no request is made (or it fails gracefully depending on implementation).
        - In the current implementation of ItemReattacher.reattach_item, it will raise a KeyError
          when accessing REATTACH_ITEM_TYPE_TO_ENDPOINT.
    """
    mocker.patch("demisto_client.configure")

    ids = ["item1"]
    item_type = "NonExistentType"

    with pytest.raises(KeyError):
        reattach_content_items(ids=ids, item_type=item_type)

from pytest_mock import MockerFixture

from demisto_sdk.commands.reattach.reattach import reattach_content_items


def test_reattach_content_items_specific(mocker: MockerFixture):
    """
    Given:
        - ids: A list of item IDs to reattach.
        - item_type: The type of the items.
    When:
        - Running reattach_content_items with specific IDs.
    Then:
        - Ensure the generic_request is called with the correct endpoint and method.
    """
    mock_client = mocker.patch("demisto_client.configure")
    mock_generic_request = mock_client.return_value.generic_request

    ids = ["item1"]
    item_type = "Playbooks"

    reattach_content_items(ids=ids, item_type=item_type)

    assert mock_generic_request.call_count == 1
    mock_generic_request.assert_any_call("/playbook/attach/item1", "POST")

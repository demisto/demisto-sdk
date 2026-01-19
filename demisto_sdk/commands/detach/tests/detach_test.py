from pytest_mock import MockerFixture
from demisto_sdk.commands.detach.detach import detach_content_items


def test_detach_content_items(mocker: MockerFixture):
    """
    Given:
        - ids: A list of item IDs to detach.
        - item_type: The type of the items.
    When:
        - Running detach_content_items.
    Then:
        - Ensure the generic_request is called with the correct endpoint and method.
    """
    mock_client = mocker.patch("demisto_client.configure")
    mock_generic_request = mock_client.return_value.generic_request
    
    ids = ["item1", "item2"]
    item_type = "Playbooks"
    
    detach_content_items(ids=ids, item_type=item_type)
    
    assert mock_generic_request.call_count == 2
    mock_generic_request.assert_any_call("/playbook/detach/item1", "POST")
    mock_generic_request.assert_any_call("/playbook/detach/item2", "POST")

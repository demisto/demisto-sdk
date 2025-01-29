"""
{
    "additional_needed_packs": {
        "PackOne": "instance_name1",
        "PackTwo": ""
    }
}
"""

import pytest

from demisto_sdk.commands.common.clients import (
    XsiamClient,
    get_client_conf_from_pytest_request,
    get_client_from_server_type,
)

# Any additional imports your tests require


@pytest.fixture(scope="class")
def client_conf(request):
    # Manually parse command-line arguments
    return get_client_conf_from_pytest_request(request)


@pytest.fixture(scope="class")
def api_client(client_conf: dict):
    if client_conf:  # Running from external pipeline
        client_obj = get_client_from_server_type(**client_conf)

    else:  # Running manually using pytest.
        client_obj = get_client_from_server_type()
    return client_obj


class TestExample:
    @classmethod
    def setup_class(self):
        """Run once for the class before *all* tests"""
        pass

    def some_helper_function(self, method):
        pass

    @classmethod
    def teardown_class(self):
        """Run once for the class after all tests"""
        pass

    # PLAYBOOK X CHECKING VALID alert
    def test_feature_one_manual_true(self, api_client: XsiamClient):
        """Test feature one"""
        a = api_client.list_indicators()

        assert a is not None, "list_indicators should not be None"

    def test_feature_two(self, api_client: XsiamClient):
        """
        Given: Describe the given inputs or the given situation prior the use case.
        When: Describe the use case
        Then: Describe the desired outcome of the use case.
        """
        # Test another aspect of your application
        api_client.run_cli_command(
            investigation_id="INCIDENT-1", command="!Set key=test value=A"
        )
        assert False  # replace with actual assertions for your application


if __name__ == "__main__":
    pytest.main()

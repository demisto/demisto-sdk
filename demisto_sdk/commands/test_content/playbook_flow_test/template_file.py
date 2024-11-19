"""
{
    "additional_needed_packs": {
        "PackOne": "instance_name1",
        "PackTwo": ""
    }
}
"""
import json

import pytest

from demisto_sdk.commands.common.clients import (
    XsiamClient,
    get_client_conf_from_pytest_request,
    get_client_from_server_type,
)

# Any additional imports your tests require

def util_load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())

@pytest.fixture
def client_conf(request):
    # Manually parse command-line arguments
    return get_client_conf_from_pytest_request(request)

@pytest.fixture
def api_client(client_conf):
    if client_conf:  # Running from external pipeline
        client_obj = get_client_from_server_type(**client_conf)

    else:  # Running manually using pytest.
        client_obj = get_client_from_server_type()
    yield client_obj

class TestExample:
    @classmethod
    def setup_class(self):
        """Run once for the class before *all* tests"""
        print("Testing out running in setup!")
        self.data = "test"

    @pytest.fixture
    def setup_method(self, client_conf = None):
        if client_conf:
            self.client = get_client_from_server_type(client_conf)
        else:
            self.client = get_client_from_server_type()

    def some_helper_function(self, method):
        pass

    def teardown_method(self, method):
        print("tearing down")

    @classmethod
    def teardown_class(self):
        """Run once for the class after all tests"""
        pass

    # PLAYBOOK X CHECKING VALID alert
    def test_feature_one_manual_true(self, api_client: XsiamClient):
        """Test feature one"""
        a = api_client.list_indicators()
        assert a is not None

    def test_feature_two(self, api_client: XsiamClient):
        """Test feature two"""
        # Test another aspect of your application
        api_client.run_cli_command(
            investigation_id="INCIDENT-1", command='!Set key=test value=A')
        assert False  # replace with actual assertions for your application


if __name__ == "__main__":
    pytest.main()

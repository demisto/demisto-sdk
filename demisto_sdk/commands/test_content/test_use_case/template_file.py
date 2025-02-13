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
    def test_wait_complete_playbook_tasks(self, api_client: XsiamClient):
        """Test feature one"""

        # search tasks without completing what's not completed
        res = api_client.pull_playbook_tasks_by_state("91818",task_states=["Waiting", "InProgress"], task_input="Yes")
        assert res == {'CompletedTask': [], 'FoundTask': [{'task name': 'Test Manual', 'task state': 'Waiting'}]}

        # search task and completing it if it's not completed
        res = api_client.pull_playbook_tasks_by_state("91818", task_states=["Error", "Waiting", "InProgress", "Completed"],
                                                    task_input="Yes", complete_task=True)
        assert res == {'CompletedTask': ['Test Manual'], 'FoundTask': []}

        # search non-existent task
        with pytest.raises(RuntimeError):
            api_client.pull_playbook_tasks_by_state("91818",
                                                    task_states=["Error", "Waiting", "InProgress", "Completed"],
                                                    task_input="Yes", complete_task=True, task_name="no task")

    def test_complete_task_with_input(self, api_client: XsiamClient):

        # complete a task with id with input Yes
        api_client.complete_playbook_task("91818", task_id="1", task_input="Yes")

        # complete a task with name and input Yes
        api_client.complete_playbook_task("91818", task_name="Test 2", task_input="Label 2")

        # try to complete a task in a non-existent investigation
        with pytest.raises(ValueError):
            api_client.complete_playbook_task("918181", "1", "Yes")

        # api_client.complete_playbook_task("26526", task_id="1", task_input="Yes")

    def test_updating_integration_instance_state(self, api_client: XsiamClient):
        """Test feature one"""
        # disable integration instance
        disabled_instance = api_client.disable_integration_instance("okta_test")
        assert disabled_instance.get("enabled") == "false"

        # Enable integration instance
        enabled_instance = api_client.enable_integration_instance("okta_test")
        assert enabled_instance.get("enabled") == "true"

        # try to disable non-existent instance
        with pytest.raises(ValueError):
            api_client.disable_integration_instance("okta_tests")

    def test_run_slash_command(self, api_client: XsiamClient):
        """
        Given: Incident ID and a slash command to run.
        When: run slash command
        Then: the slash command gets executed.
        """
        # TODO: API does not support running slash command, it just prints it as an entry in the war room
        # Test slash command
        api_client.run_slash_command(
            investigation_id="91818", command="incident_set accountid='test 2'"
        )

    def test_upload_file_to_incident(self, api_client: XsiamClient):
        # api_client.upload_file_to_war_room(file_path="/Users/mmaayta/Downloads/testApi.doc", file_name="testMeritApi2", incident_id="91818")

        api_client.upload_file_to_war_room(file_path="/Users/mmaayta/Downloads/testApi.doc", file_name="testMeritApi3", incident_id="2927")


if __name__ == "__main__":
    pytest.main()

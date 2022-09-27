import json
import os

from demisto_sdk.commands.unify.agent_config_unifier import AgentConfigUnifier
from demisto_sdk.commands.common.legacy_git_tools import git_path

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'


def test_unify_agent_config():
    """
    Given
    - Dummy Agent Config.
    - No output path.

    When
    - Running Unify on it.

    Then
    - Ensure Unify agent config works
    """
    input_path_script = TESTS_DIR + '/test_files/Packs/DummyPack/AgentConfigs/DummyAgentConfig'
    unifier = AgentConfigUnifier(input_path_script)
    json_files = unifier.unify()

    export_json_path = json_files[0]
    expected_json_path = TESTS_DIR + '/test_files/Packs/DummyPack/AgentConfigs/DummyAgentConfig/agentconfig-DummyAgentConfig.json'
    assert export_json_path == expected_json_path

    expected_json_file = {'content_global_id': '1',
                          'name': 'Dummmy',
                          'os_type': 'AGENT_OS_LINUX',
                          'profile_type': 'STANDARD',
                          'yaml_template': 'dGVzdDogZHVtbXlfdGVzdA=='}
    with open(expected_json_path, 'r') as real_file:
        assert expected_json_file == json.load(real_file)

    #os.remove(expected_json_path)

import json
import os

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.unify.agent_config_unifier import AgentConfigUnifier

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
    input_path = TESTS_DIR + '/test_files/Packs/DummyPack/AgentConfigs/DummyAgentConfig'
    output_path = TESTS_DIR + '/test_files/Packs/DummyPack/AgentConfigs/'

    unifier = AgentConfigUnifier(input=input_path, output=output_path)
    json_files = unifier.unify()

    expected_json_path = TESTS_DIR + '/test_files/Packs/DummyPack/AgentConfigs/external-agentconfig-DummyAgentConfig.json'
    export_json_path = json_files[0]

    assert export_json_path == expected_json_path

    expected_json_file = {'content_global_id': '1',
                          'name': 'Dummmy',
                          'os_type': 'AGENT_OS_LINUX',
                          'profile_type': 'STANDARD',
                          'yaml_template': 'dGVzdDogZHVtbXlfdGVzdA=='}
    with open(expected_json_path, 'r') as real_file:
        assert expected_json_file == json.load(real_file)

    os.remove(expected_json_path)

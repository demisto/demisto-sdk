from demisto_sdk.commands.common.content.objects.pack_objects import \
    AgentConfig
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


def get_agent_config(pack, name):
    return pack.create_agent_config(name)


class TestAgentConfig:
    def test_objects_factory(self, pack):
        agent_config = get_agent_config(pack, 'agent_config_name')
        obj = path_to_pack_object(agent_config.agent_config_tmp_path)
        assert isinstance(obj, AgentConfig)

    def test_prefix(self, pack):
        agent_config = get_agent_config(pack, 'external-agentconfig-agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.normalize_file_name() == agent_config.agent_config_tmp_path.name

        agent_config = get_agent_config(pack, 'agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.normalize_file_name() == f"external-agentconfig-{agent_config.agent_config_tmp_path.name}"

    def test_files_detection(self, pack):
        agent_config = get_agent_config(pack, 'agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.path == agent_config.agent_config_tmp_path

    # def test_unify_agent_config(self, pack):
    #     """
    #     Given:
    #     agent config:
    #     - yml file
    #     - json file
    #     When:
    #      - we want to unify all files to one unified json file.
    #
    #      Then:
    #      - Ensure the json was unified successfully.
    #     """
    #     agent_config = get_agent_config(pack, 'agent_config_name')
    #     obj = AgentConfig(agent_config.agent_config_tmp_path)
    #     unify_obj = get_yaml(obj._unify(agent_config.agent_config_tmp_path.parent)[0])
    #     assert unify_obj['schema'] == '{\n    "test_audit_raw": {\n        "name": {\n            "type": "string",\n' \
    #                                   '            "is_array": false\n        }\n    }\n}'

from demisto_sdk.commands.common.content.objects.pack_objects import \
    AgentConfig
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


class TestAgentConfig:
    def test_objects_factory(self, pack):
        agent_config = pack.create_agent_config('agent_config_name')
        obj = path_to_pack_object(agent_config.agent_config_tmp_path)
        assert isinstance(obj, AgentConfig)

    def test_prefix(self, pack):
        agent_config = pack.create_agent_config('external-agentconfig-agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.normalize_file_name() == agent_config.agent_config_tmp_path.name

        agent_config = pack.create_agent_config('agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.normalize_file_name() == f"external-agentconfig-{agent_config.agent_config_tmp_path.name}"

    def test_files_detection(self, pack):
        agent_config = pack.create_agent_config('agent_config_name')
        obj = AgentConfig(agent_config.agent_config_tmp_path)
        assert obj.path == agent_config.agent_config_tmp_path

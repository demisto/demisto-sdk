import pytest
from pathlib import Path
from demisto_sdk.commands.common.constants import MarketplaceVersions

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.content_graph_commands import create_content_graph
from demisto_sdk.commands.content_graph.tests.common import load_json
from TestSuite.repo import Repo


class TestCreateContentGraph:
    def test_create_content_graph_end_to_end_with_new_service(self, mocker, repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with a new service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
        mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
        mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))

        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        interface = create_content_graph(keep_service=True, use_existing=False)
        content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1
        interface.delete_all_graph_nodes_and_relationships()

    def test_create_content_graph_end_to_end_with_existing_service(self, mocker, repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with an existing service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
        mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
        mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))

        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        interface = create_content_graph(keep_service=True, use_existing=True)
        content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1
        interface.delete_all_graph_nodes_and_relationships()

    # def test_create_content_graph_single_pack(self, mocker, repo: Repo):
    #     """
    #     Given:
    #         - A mock model of a repository with a single pack TestPack, containing:
    #           - An integration TestIntegration, which:
    #             - Has a single command, test-command.
    #             - Imports TestApiModule in the code.
    #             - Is tested by TestTPB.
    #             - A default classifier.
    #           - A script Script1.
    #           - A script Script2 that uses Script1.
    #           - A test playbook TestTPB.
    #     When:
    #         - Running create_content_graph() with an existing service and killing it.
    #     Then:
    #         - Make sure the service is not available by failing to run a query.
    #     """
    #     import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
    #     mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
    #     mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))

    #     pack = repo.create_pack('TestPack')
    #     pack.pack_metadata.write_json(load_json('pack_metadata.json'))
    #     integration = pack.create_integration()
    #     integration.create_default_integration('TestIntegration')

    #     interface = create_content_graph(keep_service=False, use_existing=False)
    #     with pytest.raises(Exception):
    #         interface.get_packs_content_items()

    def test_create_content_graph_end_to_end_and_kill_existing_service(self, mocker, repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with an existing service and killing it.
        Then:
            - Make sure the service is not available by failing to run a query.
        """
        import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
        mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
        mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))

        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        interface = create_content_graph(keep_service=False, use_existing=True)
        with pytest.raises(Exception):
            interface.get_packs_content_items()
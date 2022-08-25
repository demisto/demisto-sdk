from pathlib import Path

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.content_graph_commands import create_content_graph
from TestSuite.repo import Repo


class TestCreateContentGraph:
    def test_sanity(self, mocker, repo: Repo):
        """
        Given:
            - A repository with a pack containing an integration.
        When:
            - Running create_content_graph().
            - Querying for all content items in the graph.
        Then:
            - Make sure there is a single integration in the query response.
        """
        import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
        mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
        mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))

        pack = repo.create_pack()
        pack.create_integration()
        interface = create_content_graph(keep_service=False, use_existing=False)
        content_items = interface.get_packs_content_items()
        assert len(content_items) == 1

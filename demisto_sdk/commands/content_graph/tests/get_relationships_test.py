from pathlib import Path

import pytest

from demisto_sdk.commands.content_graph import neo4j_service
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.commands.get_relationships import (
    get_relationships_by_path,
)
from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_integration,
    mock_pack,
    mock_script,
    mock_test_playbook,
)
from TestSuite.repo import Repo


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))
    neo4j_service.stop()


@pytest.fixture
def repository(mocker):
    repository = ContentDTO(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        return_value=[repository],
    )
    return repository


def create_mini_content(repository: ContentDTO):
    """Creates a content repo with three packs and relationships

    Args:
        repository (ContentDTO): the content dto to populate
    """
    pack1 = mock_pack(
        name="SamplePack",
        path=Path("Packs/SamplePack"),
        repository=repository,
    )
    pack2 = mock_pack(
        name="SamplePack2",
        path=Path("Packs/SamplePack2"),
        repository=repository,
    )
    pack3 = mock_pack(
        name="SamplePack3",
        path=Path("Packs/SamplePack3"),
        repository=repository,
    )

    # pack1 content items
    pack1_integration = mock_integration(
        path=Path(
            "Packs/SamplePack/Integrations/SampleIntegration/SampleIntegration.yml"
        ),
        pack=pack1,
    )
    mock_script(
        path=Path("Packs/SamplePack/Scripts/SampleScript/SampleScript.yml"),
        pack=pack1,
    )

    # pack2 content items
    pack2_script = mock_script(
        "SampleScript2",
        path=Path("Packs/SamplePack2/Scripts/SampleScript2/SampleScript2.yml"),
        pack=pack2,
        uses=[(pack1_integration, False)],
    )

    # pack3 content items
    mock_script(
        "TestApiModule",
        path=Path("Packs/SamplePack3/Scripts/TestApiModule/TestApiModule.yml"),
        pack=pack3,
        importing_items=[pack1_integration],
    )
    mock_test_playbook(
        path=Path(
            "Packs/SamplePack3/TestPlaybooks/SampleTestPlaybook/SampleTestPlaybook.yml"
        ),
        pack=pack3,
        uses=[(pack1_integration, False), (pack2_script, True)],
        tested_items=[pack1_integration],
    )


class TestGetRelationships:
    def test_get_relationships(
        self,
        repository: ContentDTO,
    ):
        """
        Given:
            - A mocked model of a repository.
            - A path to a script SampleScript2 in SamplePack2 pack.
        When:
            - Running get_relationships_by_path().
        Then:
            - Make sure the sources and targets of SampleScript2 are the expected.
        """
        create_mini_content(repository)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)

            sample_script_path = repository.packs[1].content_items.script[0].path
            sources, targets = get_relationships_by_path(
                interface,
                path=sample_script_path,
                relationship=RelationshipType.USES,
                depth=1,
            )
            test_playbook_path = repository.packs[2].content_items.test_playbook[0].path
            assert str(test_playbook_path) in sources
            integration_path = repository.packs[0].content_items.integration[0].path
            assert str(integration_path) in targets

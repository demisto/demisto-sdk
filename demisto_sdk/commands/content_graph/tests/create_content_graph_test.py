from typing import Any, Dict, List
import pytest
from pathlib import Path
from demisto_sdk.commands.content_graph.common import ContentTypes, Rel

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.content_graph_commands import create_content_graph, stop_content_graph
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack, PackContentItems
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.tests.tests_utils import load_json
from TestSuite.repo import Repo


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """ Auto-used fixture for setup before every test run """
    mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
    mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))


""" Fixtures for mock content object models """


@pytest.fixture
def repository():
    return Repository(
        path=Path('/dummypath'),
        packs=[],
    )


@pytest.fixture
def pack():
    pack_name = 'SamplePack'
    return Pack(
        object_id=pack_name,
        content_type=ContentTypes.PACK,
        node_id=f'{ContentTypes.PACK}:{pack_name}',
        path=Path('/dummypath'),
        name=pack_name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description='',
        created='',
        updated='',
        support='',
        email='',
        url='',
        author='',
        certification='',
        hidden=False,
        server_min_version='',
        current_version='1.0.0',
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems=PackContentItems(),
    )


@pytest.fixture
def integration():
    integration_name = 'SampleIntegration'
    return Integration(
        id=integration_name,
        content_type=ContentTypes.INTEGRATION,
        node_id=f'{ContentTypes.INTEGRATION}:{integration_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        toversion='99.99.99',
        name=integration_name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description='',
        deprecated=False,
        type='python3',
        docker_image='mock:docker',
        category='blabla',
        commands=[Command(name='test-command', description='')],
    )


@pytest.fixture
def script():
    script_name = 'SampleScript'
    return Script(
        id=script_name,
        content_type=ContentTypes.SCRIPT,
        node_id=f'{ContentTypes.SCRIPT}:{script_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        description='',
        toversion='99.99.99',
        name=script_name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type='python3',
        docker_image='mock:docker',
        tags=[],
        is_test=False,
    )


@pytest.fixture
def playbook():
    playbook_name = 'SamplePlaybook'
    return Playbook(
        id=playbook_name,
        content_type=ContentTypes.PLAYBOOK,
        node_id=f'{ContentTypes.PLAYBOOK}:{playbook_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        toversion='99.99.99',
        name=playbook_name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description='',
        deprecated=False,
        is_test=False,
    )


""" HELPERS """


def mock_relationship(
    source: str,
    target: str,
    source_fromversion: str = '5.0.0',
    source_marketplaces: List[str] = [MarketplaceVersions.XSOAR],
    **kwargs
) -> Dict[str, Any]:
    rel = {
        'source': source,
        'source_fromversion': source_fromversion,
        'source_marketplaces': source_marketplaces,
        'target': target,
    }
    rel.update(kwargs)
    return rel


class TestCreateContentGraph:
    def test_create_content_graph_end_to_end_with_new_service(self, repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with a new service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        interface = create_content_graph(use_existing=False)
        content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1

    def test_create_content_graph_end_to_end_with_existing_service(self, repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph() with an existing, running service.
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        interface = create_content_graph(use_existing=True)
        content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1

    def test_create_content_graph_single_pack(
        self,
        mocker,
        repository: Repository,
        pack: Pack,
        integration: Integration,
        script: Script,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing:
              - An integration SampleIntegration, which:
                1. Has a single command test-command.
                2. Imports TestApiModule in the code.
                3. Is tested by SampleTestPlaybook.
                4. A default classifier SampleClassifier.
              - A script SampleScript that uses SampleScript2.
        When:
            - Running create_content_graph() with an existing service and killing it.
        Then:
            - Make sure the graph has all the corresponding nodes and relationships.
        """
        relationships = {
            Rel.IN_PACK: [
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    f'{ContentTypes.PACK}:SamplePack'
                ),
                mock_relationship(
                    f'{ContentTypes.SCRIPT}:SampleScript',
                    f'{ContentTypes.PACK}:SamplePack'
                ),
            ],
            Rel.HAS_COMMAND: [
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    'test-command',
                    name='test-command',
                    description='',
                    deprecated=False,
                )
            ],
            Rel.IMPORTS: [
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    f'{ContentTypes.SCRIPT}:TestApiModule'
                )
            ],
            Rel.TESTED_BY: [
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    f'{ContentTypes.TEST_PLAYBOOK}:SampleTestPlaybook'
                )
            ],
            Rel.USES: [
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    f'{ContentTypes.CLASSIFIER}:SampleClassifier'
                ),
                mock_relationship(
                    f'{ContentTypes.INTEGRATION}:SampleIntegration',
                    f'{ContentTypes.CLASSIFIER}:SampleClassifier'
                )
            ],
            Rel.USES_COMMAND_OR_SCRIPT: [
                mock_relationship(
                    f'{ContentTypes.SCRIPT}:SampleScript',
                    'SampleScript2'
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.script.append(script)
        repository.packs.append(pack)
        mocker.patch(
            'demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_repository',
            return_value=repository,
        )
        
        interface = create_content_graph(use_existing=True)
        content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1
        assert content_items[0]['pack']['name'] == 'SamplePack'
        assert all(
            content_item['name'] in ['SampleIntegration', 'SampleScript']
            for content_item in content_items[0]['content_items']
        )
        assert False  # todo: complete assertions on relationships

    def test_stop_content_graph(self):
        """
        Given:
            - A running content graph service.
        When:
            - Running stop_content_graph().
        Then:
            - Make sure no exception is raised.
        """
        stop_content_graph()

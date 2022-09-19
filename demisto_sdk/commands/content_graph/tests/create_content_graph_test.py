from pathlib import Path
from typing import Any, Dict, List

import pytest

import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, Relationship
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph, marshal_content_graph, stop_content_graph)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.integration import (
    Command, Integration)
from demisto_sdk.commands.content_graph.objects.pack import (Pack,
                                                             PackContentItems)
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo

# Fixtures for mock content object models


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """ Auto-used fixture for setup before every test run """
    mocker.patch.object(content_graph_commands, 'REPO_PATH', Path(repo.path))
    mocker.patch.object(neo4j_service, 'REPO_PATH', Path(repo.path))


@pytest.fixture
def repository(mocker):
    repository = Repository(
        path=Path('/dummypath'),
        packs=[],
    )
    mocker.patch(
        'demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_repository',
        return_value=repository,
    )
    return repository


@pytest.fixture
def pack():
    pack_name = 'SamplePack'
    return Pack(
        object_id=pack_name,
        content_type=ContentType.PACK,
        node_id=f'{ContentType.PACK}:{pack_name}',
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
        content_type=ContentType.INTEGRATION,
        node_id=f'{ContentType.INTEGRATION}:{integration_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        toversion='99.99.99',
        display_name=integration_name,
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
        content_type=ContentType.SCRIPT,
        node_id=f'{ContentType.SCRIPT}:{script_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        description='',
        display_name=script_name,
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
        content_type=ContentType.PLAYBOOK,
        node_id=f'{ContentType.PLAYBOOK}:{playbook_name}',
        path=Path('/dummypath'),
        fromversion='5.0.0',
        toversion='99.99.99',
        display_name=playbook_name,
        name=playbook_name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description='',
        deprecated=False,
        is_test=False,
    )


# HELPERS


def mock_relationship(
    source: str,
    source_type: ContentType,
    target: str,
    target_type: ContentType,
    source_fromversion: str = '5.0.0',
    source_marketplaces: List[str] = [MarketplaceVersions.XSOAR],
    **kwargs
) -> Dict[str, Any]:
    rel = {
        'source_id': source,
        'source_type': source_type,
        'source_fromversion': source_fromversion,
        'source_marketplaces': source_marketplaces,
        'target': target,
        'target_type': target_type,
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

        with ContentGraphInterface(start_service=True) as interface:
            create_content_graph(interface)
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

        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            content_items = interface.get_packs_content_items(marketplace=MarketplaceVersions.XSOAR)
        assert len(content_items) == 1

    def test_create_content_graph_single_pack(
        self,
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
            - Running create_content_graph().
        Then:
            - Make sure the graph has all the corresponding nodes and relationships.
        """
        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
                mock_relationship(
                    'SampleScript',
                    ContentType.SCRIPT,
                    'SamplePack',
                    ContentType.PACK,
                ),
            ],
            Relationship.HAS_COMMAND: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                )
            ],
            Relationship.IMPORTS: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'TestApiModule',
                    ContentType.SCRIPT,
                )
            ],
            Relationship.TESTED_BY: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SampleTestPlaybook',
                    ContentType.TEST_PLAYBOOK,
                )
            ],
            Relationship.USES_BY_ID: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SampleClassifier',
                    ContentType.CLASSIFIER,
                ),
            ],
            Relationship.USES_COMMAND_OR_SCRIPT: [
                mock_relationship(
                    'SampleScript',
                    ContentType.SCRIPT,
                    'SampleScript2',
                    ContentType.COMMAND_OR_SCRIPT,
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.script.append(script)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            result = interface.get_relationships_by_type(Relationship.IN_PACK)
            for rel in result:
                assert rel['source']['name'] in ['SampleIntegration', 'SampleScript']
                assert rel['target']['name'] == 'SamplePack'

            result = interface.get_relationships_by_type(Relationship.HAS_COMMAND)
            for rel in result:
                assert rel['source']['name'] == 'SampleIntegration'
                assert rel['target']['name'] == 'test-command'

            result = interface.get_relationships_by_type(Relationship.USES)
            for rel in result:
                if rel['source']['name'] == 'SampleIntegration':
                    assert rel['target']['object_id'] == 'SampleClassifier'
                elif rel['source']['name'] == 'SampleScript':
                    assert rel['target']['object_id'] == 'SampleScript2'
                else:
                    assert False  # there is no else case

            result = interface.get_relationships_by_type(Relationship.TESTED_BY)
            for rel in result:
                assert rel['source']['name'] == 'SampleIntegration'
                assert rel['target']['object_id'] == 'SampleTestPlaybook'

            result = interface.get_relationships_by_type(Relationship.IMPORTS)
            for rel in result:
                assert rel['source']['name'] == 'SampleIntegration'
                assert rel['target']['object_id'] == 'TestApiModule'

    def test_create_content_graph_two_integrations_with_same_command(
        self,
        repository: Repository,
        pack: Pack,
        integration: Integration,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing two integrations,
              each has a command named test-command.
        When:
            - Running create_content_graph().
        Then:
            - Make sure only one command node was created.
        """
        integration2 = integration.copy()
        integration2.name = integration2.object_id = 'SampleIntegration2'
        integration2.node_id = f'{ContentType.INTEGRATION}:{integration2.object_id}'

        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
                mock_relationship(
                    'SampleIntegration2',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
            ],
            Relationship.HAS_COMMAND: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                ),
                mock_relationship(
                    'SampleIntegration2',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert interface.search_nodes(object_id='SampleIntegration')
            assert interface.search_nodes(object_id='SampleIntegration2')
            assert len(interface.get_nodes_by_type(ContentType.COMMAND)) == 1

    def test_create_content_graph_playbook_uses_script_not_in_repository(
        self,
        repository: Repository,
        pack: Pack,
        playbook: Playbook,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing a playbook tha
              wasn't parsed, meaning it's not in the repository.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the script has the boolean property "not_in_repository".
        """
        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SamplePlaybook',
                    ContentType.PLAYBOOK,
                    'SamplePack',
                    ContentType.PACK,
                ),
            ],
            Relationship.USES_BY_ID: [
                mock_relationship(
                    'SamplePlaybook',
                    ContentType.PLAYBOOK,
                    'TestScript',
                    ContentType.SCRIPT,
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.playbook.append(playbook)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            script = interface.get_single_node(object_id='TestScript')
        assert script.get('not_in_repository')

    def test_create_content_graph_duplicate_integrations(
        self,
        repository: Repository,
        pack: Pack,
        integration: Integration,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing two integrations
              with the exact same properties.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the duplicates are found and the command fails.
        """
        integration2 = integration.copy()
        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
            ],
            Relationship.HAS_COMMAND: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)

        with pytest.raises(Exception) as e:
            with ContentGraphInterface() as interface:
                create_content_graph(interface)
        assert 'Duplicates found in graph' in str(e)

    def test_create_content_graph_duplicate_integrations_different_marketplaces(
        self,
        repository: Repository,
        pack: Pack,
        integration: Integration,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing two integrations
              with the exact same properties but they are from different markletplaces.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the the integrations are not recognized as duplicates and the command succeeds.
        """
        integration2 = integration.copy()
        integration2.marketplaces = [MarketplaceVersions.MarketplaceV2]
        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                    source_marketplaces=[MarketplaceVersions.MarketplaceV2]
                ),
            ],
            Relationship.HAS_COMMAND: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                    source_marketplaces=[MarketplaceVersions.MarketplaceV2]
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)

        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert len(interface.search_nodes(object_id='SampleIntegration')) == 2

    def test_create_content_graph_duplicate_integrations_different_fromversion(
        self,
        repository: Repository,
        pack: Pack,
        integration: Integration,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing two integrations
              with the exact same properties but have different version ranges.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the the integrations are not recognized as duplicates and the command succeeds.
        """
        integration2 = integration.copy()
        integration.toversion = '6.0.0'
        integration2.fromversion = '6.0.2'
        relationships = {
            Relationship.IN_PACK: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'SamplePack',
                    ContentType.PACK,
                    source_fromversion='6.0.2'
                ),
            ],
            Relationship.HAS_COMMAND: [
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                ),
                mock_relationship(
                    'SampleIntegration',
                    ContentType.INTEGRATION,
                    'test-command',
                    ContentType.COMMAND,
                    name='test-command',
                    description='',
                    deprecated=False,
                    source_fromversion='6.0.2',
                )
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)

        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert len(interface.search_nodes(object_id='SampleIntegration')) == 2

    def test_create_content_graph_empty_repository(
        self,
        repository: Repository,
    ):
        """
        Given:
            - A mocked model of an empty repository.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph contains server items.
            - Make sure all nodes in the graph are server items.
        """
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            result = interface.search_nodes()
            assert len(result) > 0
            assert all(entry['node']['is_server_item'] is True for entry in result)

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

    def test_dump_content_graph(self, tmp_path: Path, repo: Repo):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing an integration.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph is dumped to the correct path.
        """
        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')

        with ContentGraphInterface(start_service=True, output_file=tmp_path / 'content.dump') as interface:
            create_content_graph(interface)

        assert Path.exists(tmp_path / 'content.dump'), 'Make sure dump file created'
        stop_content_graph()

    def test_marshal_content_graph(self, tmp_path: Path, repo: Repo):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing an integration.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph is dumped to the correct path.
        """
        pack = repo.create_pack('TestPack')
        pack.pack_metadata.write_json(load_json('pack_metadata.json'))
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')
        dump_path = tmp_path / 'content.dump'
        with ContentGraphInterface(start_service=True, output_file=dump_path) as interface:
            create_content_graph(interface)

        assert Path.exists(dump_path), 'Make sure dump file created'
        neo4j_service.load(dump_path)
        repo_model: Repository = marshal_content_graph(interface, MarketplaceVersions.XSOAR)
        packs = repo_model.packs
        assert len(packs) == 1
        pack = packs[0]
        assert pack.name == 'HelloWorld'
        integrations = repo_model.packs[0].content_items.integration
        integration = integrations[0]
        assert len(integrations) == 1
        assert integration.name == 'TestIntegration'
        commands = integration.commands
        assert len(commands) == 1
        assert commands[0].name == 'test-command'
        stop_content_graph()

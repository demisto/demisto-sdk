from pathlib import Path
from typing import Any, Dict, List

import pytest

import demisto_sdk.commands.content_graph.content_graph_commands as content_graph_commands
import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (ContentType,
                                                       RelationshipType)
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph, marshal_content_graph, stop_content_graph)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import (
    Command, Integration)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import Repository
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import \
    TestPlaybook
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo

# Fixtures for mock content object models


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    mocker.patch.object(content_graph_commands, "REPO_PATH", Path(repo.path))
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))


@pytest.fixture
def repository(mocker):
    repository = Repository(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_repository",
        return_value=repository,
    )
    return repository


def mock_pack(name: str = "SamplePack"):
    return Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=Path("/dummypath"),
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        created="",
        updated="",
        support="",
        email="",
        url="",
        author="",
        certification="",
        hidden=False,
        server_min_version="",
        current_version="1.0.0",
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems=[],
    )


def mock_integration(name: str = "SampleIntegration"):
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        category="blabla",
        commands=[Command(name="test-command", description="")],
    )


def mock_script(name: str = "SampleScript"):
    return Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        description="",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
    )


def mock_classifier(name: str = "SampleClassifier"):
    return Classifier(
        id=name,
        content_type=ContentType.CLASSIFIER,
        node_id=f"{ContentType.CLASSIFIER}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        description="",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
    )


def mock_playbook(name: str = "SamplePlaybook"):
    return Playbook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        is_test=False,
    )


def mock_test_playbook(name: str = "SampleTestPlaybook"):
    return TestPlaybook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("/dummypath"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        description="",
        deprecated=False,
        is_test=True,
    )


# HELPERS


def mock_relationship(
    source: str,
    source_type: ContentType,
    target: str,
    target_type: ContentType,
    source_fromversion: str = "5.0.0",
    source_marketplaces: List[str] = [MarketplaceVersions.XSOAR],
    **kwargs,
) -> Dict[str, Any]:
    rel = {
        "source_id": source,
        "source_type": source_type,
        "source_fromversion": source_fromversion,
        "source_marketplaces": source_marketplaces,
        "target": target,
        "target_type": target_type,
    }
    rel.update(kwargs)
    return rel


class TestCreateContentGraph:
    def _test_create_content_graph_end_to_end(self, repo: Repo, start_service: bool):
        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        integration = pack.create_integration()
        integration.create_default_integration(
            "TestIntegration", ["test-command1", "test-command2"]
        )
        script = pack.create_script()
        api_module = pack.create_script()
        script.create_default_script("SampleScript")
        api_module.create_default_script("TestApiModule")

        pack.create_classifier(
            name="SampleClassifier", content=load_json("classifier.json")
        )

        with ContentGraphInterface(start_service=start_service) as interface:
            create_content_graph(interface)
            packs = interface.match(
                marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK
            )
            integrations = interface.match(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.INTEGRATION,
            )
            all_content_items = interface.match(marketplace=MarketplaceVersions.XSOAR)

        assert len(packs) == 1
        assert len(integrations) == 1
        assert len(all_content_items) == 8
        returned_pack = packs[0]
        assert returned_pack.object_id == "TestPack"
        # make sure that data from pack_metadata.json updated
        assert returned_pack.name == "HelloWorld"
        assert returned_pack.support == "community"
        assert len(packs[0].content_items.integration) == 1
        returned_integration = packs[0].content_items.integration[0]
        assert returned_integration == integrations[0]
        assert returned_integration.name == "TestIntegration"
        assert {command.name for command in returned_integration.commands} == {
            "test-command",
            "test-command1",
            "test-command2",
        }
        returned_scripts = {
            script.object_id for script in packs[0].content_items.script
        }
        assert returned_scripts == {"SampleScript", "TestApiModule"}

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
        self._test_create_content_graph_end_to_end(repo, start_service=True)

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
        self._test_create_content_graph_end_to_end(repo, start_service=False)

    def test_create_content_graph_single_pack(
        self,
        repository: Repository,
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
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleScript",
                    ContentType.SCRIPT,
                    "SamplePack",
                    ContentType.PACK,
                ),
            ],
            RelationshipType.HAS_COMMAND: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                )
            ],
            RelationshipType.IMPORTS: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "TestApiModule",
                    ContentType.SCRIPT,
                )
            ],
            RelationshipType.TESTED_BY: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SampleTestPlaybook",
                    ContentType.TEST_PLAYBOOK,
                )
            ],
            RelationshipType.USES_BY_ID: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SampleClassifier",
                    ContentType.CLASSIFIER,
                ),
            ],
        }
        relationship_pack2 = {
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleClassifier",
                    ContentType.CLASSIFIER,
                    "SamplePack2",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleTestPlaybook",
                    ContentType.TEST_PLAYBOOK,
                    "SamplePack2",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "TestApiModule", ContentType.SCRIPT, "SamplePack2", ContentType.PACK
                ),
            ]
        }
        pack1 = mock_pack()
        pack2 = mock_pack("SamplePack2")
        pack1.relationships = relationships
        pack2.relationships = relationship_pack2
        pack1.content_items.integration.append(mock_integration())
        pack1.content_items.script.append(mock_script())
        pack2.content_items.script.append(mock_script("TestApiModule"))
        pack2.content_items.classifier.append(mock_classifier())
        pack2.content_items.test_playbook.append(mock_test_playbook())
        repository.packs.extend([pack1, pack2])
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            packs = interface.match(
                marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK
            )
            all_content_items = interface.match(
                marketplace=MarketplaceVersions.XSOAR,
            )
            assert len(packs) == 2
            assert len(all_content_items) == 7
            returned_pack = packs[0]
            assert len(returned_pack.content_items.integration) == 1
            assert len(returned_pack.content_items.script) == 1

            returned_integration = returned_pack.content_items.integration[0]
            assert returned_integration.commands[0].name == "test-command"
            uses_integration = returned_integration.uses[0]
            assert uses_integration.object_id == "SampleClassifier"
            tested_by = returned_integration.tested_by[0]
            assert tested_by.object_id == "TestApiModule"

            imports = returned_integration.imports
            assert imports.object_id == "SampleTestPlaybook"

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
        integration2.name = integration2.object_id = "SampleIntegration2"
        integration2.node_id = f"{ContentType.INTEGRATION}:{integration2.object_id}"

        relationships = {
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleIntegration2",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
            ],
            RelationshipType.HAS_COMMAND: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
                mock_relationship(
                    "SampleIntegration2",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert interface.match(object_id="SampleIntegration")
            assert interface.match(object_id="SampleIntegration2")
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
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SamplePlaybook",
                    ContentType.PLAYBOOK,
                    "SamplePack",
                    ContentType.PACK,
                ),
            ],
            RelationshipType.USES_BY_ID: [
                mock_relationship(
                    "SamplePlaybook",
                    ContentType.PLAYBOOK,
                    "TestScript",
                    ContentType.SCRIPT,
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.playbook.append(playbook)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            script = interface.get_single_node(object_id="TestScript")
        assert script.get("not_in_repository")

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
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
            ],
            RelationshipType.HAS_COMMAND: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with pytest.raises(Exception) as e:
            with ContentGraphInterface() as interface:
                create_content_graph(interface)
        assert "Duplicates found in graph" in str(e)

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
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                    source_marketplaces=[MarketplaceVersions.MarketplaceV2],
                ),
            ],
            RelationshipType.HAS_COMMAND: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                    source_marketplaces=[MarketplaceVersions.MarketplaceV2],
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert len(interface.match(object_id="SampleIntegration")) == 2

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
        integration.toversion = "6.0.0"
        integration2.fromversion = "6.0.2"
        relationships = {
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "SamplePack",
                    ContentType.PACK,
                    source_fromversion="6.0.2",
                ),
            ],
            RelationshipType.HAS_COMMAND: [
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                ),
                mock_relationship(
                    "SampleIntegration",
                    ContentType.INTEGRATION,
                    "test-command",
                    ContentType.COMMAND,
                    name="test-command",
                    description="",
                    deprecated=False,
                    source_fromversion="6.0.2",
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.integration.append(integration)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert len(interface.match(object_id="SampleIntegration")) == 2

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
            result = interface.match()
            assert len(result) > 0
            assert all(entry["node"]["is_server_item"] is True for entry in result)

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
        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        integration = pack.create_integration()
        integration.create_default_integration("TestIntegration")

        with ContentGraphInterface(
            start_service=True, output_file=tmp_path / "content.dump"
        ) as interface:
            create_content_graph(interface)

        assert Path.exists(tmp_path / "content.dump"), "Make sure dump file created"
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
        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        integration = pack.create_integration()
        integration.create_default_integration("TestIntegration")
        dump_path = tmp_path / "content.dump"
        with ContentGraphInterface(
            start_service=True, output_file=dump_path
        ) as interface:
            create_content_graph(interface)

        assert Path.exists(dump_path), "Make sure dump file created"
        neo4j_service.load(dump_path)
        repo_model: Repository = marshal_content_graph(
            interface, MarketplaceVersions.XSOAR
        )
        packs = repo_model.packs
        assert len(packs) == 1
        pack = packs[0]
        assert pack.name == "HelloWorld"
        integrations = repo_model.packs[0].content_items.integration
        integration = integrations[0]
        assert len(integrations) == 1
        assert integration.name == "TestIntegration"
        commands = integration.commands
        assert len(commands) == 1
        assert commands[0].name == "test-command"
        stop_content_graph()

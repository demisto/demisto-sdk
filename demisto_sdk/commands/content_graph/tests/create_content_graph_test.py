from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph,
    stop_content_graph,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

# Fixtures for mock content object models


@pytest.fixture(autouse=True)
def setup(mocker, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    mocker.patch(
        "demisto_sdk.commands.content_graph.objects.base_content.get_content_path",
        return_value=Path(repo.path),
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))
    stop_content_graph()


@pytest.fixture
def repository(mocker):
    repository = ContentDTO(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


def mock_pack(name: str = "SamplePack"):
    return Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=Path("Packs"),
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        hidden=False,
        server_min_version="5.5.0",
        current_version="1.0.0",
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems=[],
        excluded_dependencies=[],
    )


def mock_integration(name: str = "SampleIntegration"):
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=Path("Packs"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
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
        path=Path("Packs"),
        fromversion="5.0.0",
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
        path=Path("Packs"),
        fromversion="5.0.0",
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
        path=Path("Packs"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        is_test=False,
    )


def mock_test_playbook(name: str = "SampleTestPlaybook"):
    return TestPlaybook(
        id=name,
        # content_type=ContentType.TEST_PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("Packs"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
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


def find_model_for_id(packs: List[Pack], source_id: str):
    for pack in packs:
        if pack.object_id == source_id:
            return pack
        for content_item in pack.content_items:
            if content_item.object_id == source_id:
                return content_item
            if isinstance(content_item, Integration):
                for command in content_item.commands:
                    if command.name == source_id:
                        return command
    return None


def create_mini_content(repository: ContentDTO):
    """Created a content repo with three packs and relationships§

    Args:
        repository (ContentDTO): the content dto to populate
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
                mandatorily=True,
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
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "TestApiModule",
                ContentType.SCRIPT,
                "SampleScript2",
                ContentType.SCRIPT,
                mandatorily=True,
            ),
            mock_relationship(
                "SampleTestPlaybook",
                ContentType.TEST_PLAYBOOK,
                "SampleIntegration",
                ContentType.INTEGRATION,
            ),
        ],
    }
    relationship_pack3 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "SamplePack3",
                ContentType.PACK,
            ),
            mock_relationship(
                "SampleScript2",
                ContentType.SCRIPT,
                "SamplePack3",
                ContentType.PACK,
            ),
        ]
    }
    pack1 = mock_pack()
    pack2 = mock_pack("SamplePack2")
    pack3 = mock_pack("SamplePack3")
    pack1.relationships = relationships
    pack2.relationships = relationship_pack2
    pack3.relationships = relationship_pack3
    pack1.content_items.integration.append(mock_integration())
    pack1.content_items.script.append(mock_script())
    pack2.content_items.script.append(mock_script("TestApiModule"))
    pack2.content_items.classifier.append(mock_classifier())
    pack2.content_items.test_playbook.append(mock_test_playbook())
    pack3.content_items.playbook.append(mock_playbook())
    pack3.content_items.script.append(mock_script("SampleScript2"))
    repository.packs.extend([pack1, pack2, pack3])


class TestCreateContentGraph:
    def test_create_content_graph_end_to_end(self, repo: Repo, tmp_path: Path, mocker):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph()
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )

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

        with ContentGraphInterface() as interface:
            create_content_graph(interface, output_path=tmp_path)
            packs = interface.search(
                marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK
            )
            integrations = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.INTEGRATION,
            )
            all_content_items = interface.search(marketplace=MarketplaceVersions.XSOAR)
            content_cto = interface.marshal_graph(MarketplaceVersions.XSOAR)
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
        with ChangeCWD(repo.path):
            content_cto.dump(tmp_path, MarketplaceVersions.XSOAR, zip=False)
        assert Path.exists(tmp_path / "TestPack")
        assert Path.exists(tmp_path / "TestPack" / "metadata.json")
        assert Path.exists(
            tmp_path / "TestPack" / "Integrations" / "integration-integration_0.yml"
        )
        assert Path.exists(tmp_path / "TestPack" / "Scripts" / "script-script0.yml")
        assert Path.exists(tmp_path / "TestPack" / "Scripts" / "script-script1.yml")

        # make sure that the output file zip is created
        assert Path.exists(tmp_path / "xsoar.zip")
        with ZipFile(tmp_path / "xsoar.zip", "r") as zip_obj:
            zip_obj.extractall(tmp_path / "extracted")
            # make sure that the extracted files are all .csv
            extracted_files = list(tmp_path.glob("extracted/*"))
            assert extracted_files
            assert all(
                file.suffix == ".csv" or file.name == "metadata.json"
                for file in extracted_files
            )

    def test_create_content_graph_relationships(
        self,
        repository: ContentDTO,
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
        create_mini_content(repository)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            packs = interface.search(
                marketplace=MarketplaceVersions.XSOAR, content_type=ContentType.PACK
            )
            for pack in repository.packs:
                for relationship_type, relationships in pack.relationships.items():
                    for relationship in relationships:
                        content_item_source = find_model_for_id(
                            packs, relationship.get("source_id")
                        )
                        content_item_target = find_model_for_id(
                            packs, relationship.get("target")
                        )
                        assert content_item_source
                        assert content_item_target
                        if relationship_type == RelationshipType.IN_PACK:
                            assert (
                                content_item_source.in_pack.object_id == pack.object_id
                            )
                        if relationship_type == RelationshipType.IMPORTS:
                            assert (
                                content_item_source.imports[0].object_id
                                == content_item_target.object_id
                            )
                        if relationship_type == RelationshipType.USES_BY_ID:
                            assert (
                                content_item_source.uses[0].content_item_to.object_id
                                == content_item_target.object_id
                            )
                        if relationship_type == RelationshipType.TESTED_BY:
                            assert (
                                content_item_source.tested_by[0].object_id
                                == content_item_target.object_id
                            )

            assert packs[0].depends_on[0].content_item_to == packs[1]
            assert not packs[0].depends_on[0].is_test  # this is not a test dependency

            for p in packs[1].depends_on:
                if p.content_item_to == packs[2]:
                    # regular dependency
                    assert not p.is_test
                elif p.content_item_to == packs[0]:
                    # test dependency
                    assert p.is_test
                else:

                    assert False

            # now with all levels
            packs = interface.search(
                MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )
            depends_on_pack1 = [r for r in packs[0].depends_on]
            assert depends_on_pack1
            for depends in depends_on_pack1:
                if depends.content_item_to == packs[1]:
                    assert depends.is_direct
                elif depends.content_item_to == packs[2]:
                    assert not depends.is_direct
                else:
                    assert False

    def test_create_content_graph_two_integrations_with_same_command(
        self,
        repository: ContentDTO,
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
        pack = mock_pack()
        integration1 = mock_integration()
        integration2 = mock_integration("SampleIntegration2")
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
        pack.content_items.integration.append(integration1)
        pack.content_items.integration.append(integration2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert interface.search(
                MarketplaceVersions.XSOAR, object_id="SampleIntegration"
            )
            assert interface.search(
                MarketplaceVersions.XSOAR, object_id="SampleIntegration2"
            )
            assert (
                len(
                    interface.search(
                        MarketplaceVersions.XSOAR, content_type=ContentType.COMMAND
                    )
                )
                == 1
            )

    def test_create_content_graph_playbook_uses_script_not_in_repository(
        self,
        repository: ContentDTO,
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
        pack = mock_pack()
        pack.relationships = relationships
        pack.content_items.playbook.append(mock_playbook())
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            script = interface.search(object_id="TestScript")[0]
        assert script.not_in_repository

    def test_create_content_graph_duplicate_integrations_different_marketplaces(
        self,
        repository: ContentDTO,
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
        pack = mock_pack()
        integration = mock_integration()
        integration2 = mock_integration()
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
            assert len(interface.search(object_id="SampleIntegration")) == 2
            assert (
                len(
                    interface.search(
                        MarketplaceVersions.XSOAR, object_id="SampleIntegration"
                    )
                )
                == 1
            )
            assert (
                len(
                    interface.search(
                        MarketplaceVersions.MarketplaceV2, object_id="SampleIntegration"
                    )
                )
                == 1
            )

    def test_create_content_graph_duplicate_integrations_different_fromversion(
        self,
        repository: ContentDTO,
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
        pack = mock_pack()
        integration = mock_integration()
        integration2 = mock_integration()
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
            assert len(interface.search(object_id="SampleIntegration")) == 2

    def test_create_content_graph_empty_repository(
        self,
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
            assert not interface.search()

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

from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
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
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.content_graph.tests.test_tools import load_json
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

# Fixtures for mock content object models


@pytest.fixture(autouse=True)
def setup_method(mocker, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
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
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        return_value=[repository],
    )
    return repository


def mock_pack(name: str = "SamplePack", path: Path = Path("Packs")) -> Pack:
    return Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=path,
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
        deprecated=False,
    )


def mock_integration(name: str = "SampleIntegration", path: Path = Path("Packs")):
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=path,
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


def mock_script(
    name: str = "SampleScript",
    marketplaces: List[MarketplaceVersions] = [MarketplaceVersions.XSOAR],
    skip_prepare: List[str] = [],
):
    return Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=Path("Packs"),
        fromversion="5.0.0",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=marketplaces,
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
        skip_prepare=skip_prepare,
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


def mock_playbook(
    name: str = "SamplePlaybook",
    marketplaces: List[MarketplaceVersions] = [MarketplaceVersions.XSOAR],
):
    return Playbook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path("Packs"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=marketplaces,
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


def mock_widget(name: str = "SampleWidget"):
    return Widget(
        id=name,
        content_type=ContentType.WIDGET,
        node_id=f"{ContentType.WIDGET}:{name}",
        path=Path("Packs"),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        widget_type="number",
        data_type="roi",
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
        assert (tmp_path / "TestPack").exists()
        assert (tmp_path / "TestPack" / "metadata.json").exists()
        assert (
            tmp_path / "TestPack" / "Integrations" / "integration-integration_0.yml"
        ).exists()
        assert (tmp_path / "TestPack" / "Scripts" / "script-script0.yml").exists()
        assert (tmp_path / "TestPack" / "Scripts" / "script-script1.yml").exists()

        # make sure that the output file zip is created
        assert Path.exists(tmp_path / "xsoar.zip")
        with ZipFile(tmp_path / "xsoar.zip", "r") as zip_obj:
            zip_obj.extractall(tmp_path / "extracted")
            # make sure that the extracted files are all .csv
            extracted_files = list(tmp_path.glob("extracted/*"))
            assert extracted_files
            assert all(
                file.suffix == ".graphml" or file.name == "metadata.json"
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

    def test_create_content_graph_duplicate_widgets(
        self,
        repository: ContentDTO,
    ):
        """
        Given:
            - A mocked model of a repository with a pack TestPack, containing two widgets
              with the exact same id, fromversion and marketplaces properties.
        When:
            - Running create_content_graph().
        Then:
            - Make sure both widgets exist in the graph.
        """
        pack = mock_pack()
        widget = mock_widget()
        widget2 = mock_widget()
        relationships = {
            RelationshipType.IN_PACK: [
                mock_relationship(
                    "SampleWidget",
                    ContentType.WIDGET,
                    "SamplePack",
                    ContentType.PACK,
                ),
                mock_relationship(
                    "SampleWidget",
                    ContentType.WIDGET,
                    "SamplePack",
                    ContentType.PACK,
                ),
            ],
        }
        pack.relationships = relationships
        pack.content_items.widget.append(widget)
        pack.content_items.widget.append(widget2)
        repository.packs.append(pack)
        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            assert len(interface.search(object_id="SampleWidget")) == 2

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

    def test_create_content_graph_incident_to_alert_scripts(
        self, repo: Repo, tmp_path: Path, mocker
    ):
        """
        Given:
            - A repository with a pack TestPack, containing two scripts,
            one (getIncident) is set with skipping the preparation of incident to alert
            and the other (setIncident) is not.
        When:
            - Running create_content_graph().
        Then:
            - Ensure that `getIncident` script has passed the prepare process as expected.
            - Ensure the 'setIncident' script has not passed incident to alert preparation.
        """
        mocker.patch.object(
            IntegrationScript, "get_supported_native_images", return_value=[]
        )

        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        pack.create_script(name="getIncident")
        pack.create_script(name="setIncident", skip_prepare=[SKIP_PREPARE_SCRIPT_NAME])

        with ContentGraphInterface() as interface:
            create_content_graph(interface, output_path=tmp_path)
            packs = interface.search(
                marketplace=MarketplaceVersions.MarketplaceV2,
                content_type=ContentType.PACK,
            )
            scripts = interface.search(
                marketplace=MarketplaceVersions.MarketplaceV2,
                content_type=ContentType.SCRIPT,
            )
            all_content_items = interface.search(
                marketplace=MarketplaceVersions.MarketplaceV2
            )
            content_cto = interface.marshal_graph(MarketplaceVersions.MarketplaceV2)

        assert len(packs) == 1
        assert len(scripts) == 2
        assert len(all_content_items) == 3
        with ChangeCWD(repo.path):
            content_cto.dump(tmp_path, MarketplaceVersions.MarketplaceV2, zip=False)
        script_path = tmp_path / "TestPack" / "Scripts"
        assert (script_path / "script-getIncident.yml").exists()
        assert (script_path / "script-getAlert.yml").exists()
        assert (script_path / "script-setIncident.yml").exists()
        assert not (script_path / "script-setAlert.yml").exists()

    def test_create_content_graph_relationships_from_metadata(
        self,
        repo: Repo,
    ):
        """
        Given:
            - A mocked model of a repository with a pack Core, which depends on NonCorePack according to the pack metadata
        When:
            - Running create_content_graph().
        Then:
            - Make sure the relationship's is_test is not null.
        """
        core_metadata = load_json("pack_metadata.json")
        core_metadata["name"] = "Core"
        core_metadata["dependencies"].update(
            {"NonCorePack": {"mandatory": True, "display_name": "Non Core Pack"}}
        )
        pack_core = repo.create_pack("Core")
        repo.create_pack("NonCorePack")
        pack_core.pack_metadata.write_json(core_metadata)

        with ContentGraphInterface() as interface:
            create_content_graph(interface)

            data = interface.run_single_query(
                "MATCH p=()-[r:DEPENDS_ON]->() WHERE r.is_test IS NULL RETURN p"
            )

            assert not data


def test_docker_images_for_dockerfiles_info():
    docker_images = [
       "demisto/python3:3.10.12.63474",
       "demisto/python3:3.9.5.21272",
       "demisto/crypto:1.0.0.66562",
       "demisto/pyjwt3:1.0.0.48806",
       "demisto/pytan:1.0.0.38590",
       "demisto/python3:3.10.12.66339",
       "demisto/python3:3.10.10.48392",
       "demisto/python_pancloud_v2:1.0.0.64955",
       "demisto/py3-tools:1.0.0.49475",
       "demisto/python3:3.10.12.65389",
       "demisto/python3:3.9.8.24399",
       "demisto/taxii2:1.0.0.18446",
       "demisto/google-api-py3:1.0.0.64100",
       "demisto/glpi:1.0.0.65890",
       "demisto/fastapi:1.0.0.36992",
       "demisto/fastapi:1.0.0.64153",
       "demisto/boto3py3:1.0.0.65194",
       "demisto/lxml:1.0.0.63707",
       "demisto/python:2.7.18.20958",
       "demisto/polyswarm:1.0.0.18926",
       "demisto/pymisp2:1.0.0.63745",
       "demisto/pymisp:1.0.0.19190",
       "demisto/fp-smc:1.0.22.66577",
       "demisto/py3-tools:1.0.0.67011",
       "demisto/py3-tools:1.0.0.65178",
       "demisto/tweepy:1.0.0.23810",
       "demisto/fastapi:1.0.0.27446",
       "demisto/taxii2:1.0.0.66032",
       "demisto/crypto:1.0.0.63672",
       "demisto/netutils:1.0.0.24101",
       "demisto/chromium:1.0.0.56296",
       "demisto/py42:1.0.0.66909",
       "demisto/ansible-runner:1.0.0.24037",
       "demisto/crypto:1.0.0.51288",
       "demisto/python_pancloud:1.0.0.66801",
       "demisto/akamai:1.0.0.63810",
       "demisto/btfl-soup:1.0.1.45563",
       "demisto/hashicorp:1.0.0.65633",
       "demisto/python3:3.10.1.25933",
       "demisto/python3:3.10.10.49934",
       "demisto/blueliv:1.0.0.52588",
       "demisto/taxii:1.0.0.45815",
       "demisto/taxii2:1.0.0.61540",
       "demisto/syslog:1.0.0.61542",
       "demisto/syslog:1.0.0.48738",
       "demisto/pydantic-jwt3:1.0.0.64406",
       "demisto/pyjwt3:1.0.0.63826",
       "demisto/devo:1.0.0.66471",
       "demisto/python:2.7.18.24066",
       "demisto/boto3py3:1.0.0.38849",
       "demisto/python3:3.10.5.31928",
       "demisto/threatconnect-sdk:1.0.0.7659",
       "demisto/threatconnect-py3-sdk:1.0.0.40378",
       "demisto/google-cloud-storage:1.0.0.25839",
       "demisto/crypto:1.0.0.11287",
       "demisto/fastapi:1.0.0.61475",
       "demisto/google-cloud-translate:1.0.0.63615",
       "demisto/pycountry:1.0.0.65943",
       "demisto/python3:3.8.5.10845",
       "demisto/bottle:1.0.0.32745",
       "demisto/boto3py3:1.0.0.52713",
       "demisto/googleapi-python3:1.0.0.65068",
       "demisto/py3-tools:0.0.1.25751",
       "demisto/python3:3.10.8.37753",
       "demisto/pyjwt3:1.0.0.65237",
       "demisto/boto3py3:1.0.0.45936",
       "demisto/boto3py3:1.0.0.66174",
       "demisto/ntlm:1.0.0.44693",
       "demisto/googleapi-python3:1.0.0.66918",
       "demisto/googleapi-python3:1.0.0.63869",
       "demisto/winrm:1.0.0.13142",
       "demisto/teams:1.0.0.14902",
       "demisto/powershell-ubuntu:7.2.2.29705",
       "demisto/python:2.7.18.27799",
       "demisto/python3:3.10.9.42476",
       "demisto/py3-tools:1.0.0.49572",
       "demisto/google-api-py3:1.0.0.65791",
       "demisto/taxii-server:1.0.0.66858",
       "demisto/py3-tools:1.0.0.31193",
       "demisto/pyjwt3:1.0.0.23674",
       "demisto/googleapi-python3:1.0.0.65453",
       "demisto/py3-tools:1.0.0.65317",
       "demisto/boto3py3:1.0.0.41082",
       "demisto/pyotrs:1.0.0.44880",
       "demisto/pyjwt3:1.0.0.66845",
       "demisto/btfl-soup:1.0.1.46582",
       "demisto/python3:3.10.1.26972",
       "demisto/pwsh-exchangev3:1.0.0.49863",
       "demisto/xml-feed:1.0.0.63829",
       "demisto/taxii2:1.0.0.63768",
       "demisto/python:2.7.18.24398",
       "demisto/python3:3.10.10.51930",
       "demisto/datadog-api-client:1.0.0.65877",
       "demisto/py3-tools:1.0.0.56465",
       "demisto/py3-tools:1.0.0.47433",
       "demisto/netmiko:1.0.0.65282",
       "demisto/google-api-py3:1.0.0.55175",
       "demisto/cloudshare:1.0.0.14120",
       "demisto/rubrik-polaris-sdk-py3:1.0.0.66039",
       "demisto/python:2.7.18.8715",
       "demisto/powershell-ubuntu:7.1.4.24032",
       "demisto/py3ews:1.0.0.66850",
       "demisto/pwsh-exchangev3:1.0.0.67228",
       "demisto/powershell-ubuntu:7.3.0.49844",
       "demisto/netmiko:1.0.0.65807",
       "demisto/feed-parser:1.0.0.14495",
       "demisto/opencti-v4:1.0.0.46493",
       "demisto/opencti:1.0.0.41469",
       "demisto/reversinglabs-sdk-py3:2.0.0.64132",
       "demisto/pan-os-python:1.0.0.65924",
       "demisto/py3-tools:1.0.0.44868",
       "demisto/reversinglabs-sdk-py3:2.0.0.40822",
       "demisto/btfl-soup:1.0.1.63668",
       "demisto/accessdata:1.1.0.33872",
       "demisto/dxl:1.0.0.63890",
       "demisto/py3-tools:1.0.0.63856",
       "demisto/dxl:1.0.0.35274",
       "demisto/pydantic-jwt3:1.0.0.63835",
       "demisto/splunksdk:1.0.0.49073",
       "demisto/googleapi-python3:1.0.0.67173",
       "demisto/paho-mqtt:1.0.0.19143",
       "demisto/pyjwt3:1.0.0.13142",
       "demisto/btfl-soup:1.0.0.925",
       "demisto/boto3py3:1.0.0.63019",
       "demisto/jmespath:1.0.0.23980",
       "demisto/py-ews:5.0.2.63879",
       "demisto/py3ews:1.0.0.47270",
       "demisto/cymruwhois:1.0.0.65875",
       "demisto/python3:3.10.7.33922",
       "demisto/boto3py3:1.0.0.63655",
       "demisto/py3-tools:1.0.0.66127",
       "demisto/python3:3.10.11.56082",
       "demisto/snowflake:1.0.0.2505",
       "demisto/googleapi-python3:1.0.0.62073",
       "demisto/akamai:1.0.0.65229",
       "demisto/pydantic-jwt3:1.0.0.45851",
       "demisto/argus-toolbelt:2.0.0.29288",
       "demisto/ippysocks-py3:1.0.0.63627",
       "demisto/pycountry:1.0.0.63741",
       "demisto/py3-tools:1.0.0.49703",
       "demisto/py3-tools:1.0.0.45685",
       "demisto/yolo-coco:1.0.0.15530",
       "demisto/python3:3.10.5.31797",
       "demisto/dnstwist:1.0.0.46433",
       "demisto/xml-feed:1.0.0.29458",
       "demisto/opencti-v4:1.0.0.61509",
       "demisto/zeep:1.0.0.23423",
       "demisto/python3-deb:3.9.1.15758",
       "demisto/python:2.7.18.52566",
       "demisto/taxii2:1.0.0.23423",
       "demisto/carbon-black-cloud:1.0.0.64437",
       "demisto/akamai:1.0.0.34769",
       "demisto/octoxlabs:1.0.0.65919",
       "demisto/boto3py3:1.0.0.64480",
       "demisto/illumio:1.0.0.65903",
       "demisto/oauthlib:1.0.0.38743",
       "demisto/fastapi:1.0.0.63688",
       "demisto/xsoar-tools:1.0.0.25075",
       "demisto/oci:1.0.0.65918",
       "demisto/powershell-ubuntu:7.1.3.22304",
       "demisto/bigquery:1.0.0.61798",
       "demisto/graphql:1.0.0.65897",
       "demisto/flask-nginx:1.0.0.65013",
       "demisto/boto3py3:1.0.0.41926",
       "demisto/oauthlib:1.0.0.63821",
       "demisto/tidy:1.0.0.62989",
       "demisto/python3:3.10.7.35188",
       "demisto/minio:1.0.0.19143",
       "demisto/fastapi:1.0.0.64474",
       "demisto/m2crypto:1.0.0.65914",
       "demisto/py3-tools:1.0.0.64131",
       "demisto/resilient:2.0.0.45701",
       "demisto/duoadmin3:1.0.0.65621",
       "demisto/ansible-runner:1.0.0.21184",
       "demisto/ansible-runner:1.0.0.21453",
       "demisto/joe-security:1.0.0.46413",
       "demisto/pykafka:1.0.0.19034",
       "demisto/confluent-kafka:1.0.0.65871",
       "demisto/graphql:1.0.0.45620",
       "demisto/bs4-py3:1.0.0.48637",
       "demisto/openssh:1.0.0.12410",
       "demisto/netmiko:1.0.0.62777",
       "demisto/google-k8s-engine:1.0.0.64696",
       "demisto/taxii:1.0.0.43208",
       "demisto/py3-tools:1.0.0.66062",
       "demisto/fastapi:1.0.0.56647",
       "demisto/fastapi:1.0.0.65888",
       "demisto/keeper-ksm:1.0.0.67054",
       "demisto/greynoise:1.0.0.65909",
       "demisto/greynoise:1.0.0.61972",
       "demisto/exodusintelligence:1.0.0.34185",
       "demisto/pyjwt3:1.0.0.27257",
       "demisto/bs4:1.0.0.8854",
       "demisto/python3-deb:3.10.12.63475",
       "demisto/pyjwt3:1.0.0.55864",
       "demisto/smbprotocol:1.0.0.63639",
       "demisto/smb:1.0.0.7685",
       "demisto/google-vision-api:1.0.0.63870",
       "demisto/ntlm:1.0.0.64630",
       "demisto/bs4:1.0.0.24033",
       "demisto/uptycs:1.0.0.63766",
       "demisto/boto3py3:1.0.0.48955",
       "demisto/py3-tools:1.0.0.45904",
       "demisto/fastapi:1.0.0.32142",
       "demisto/google-kms:1.0.0.62005",
       "demisto/slackv3:1.0.0.63762",
       "demisto/slack:1.0.0.42956",
       "demisto/py3-tools:1.0.0.47376",
       "demisto/taxii-server:1.0.0.32901",
       "demisto/flask-nginx:1.0.0.63817",
       "demisto/sixgill:1.0.0.20925",
       "demisto/sixgill:1.0.0.66910",
       "demisto/ibm-db2:1.0.0.27972",
       "demisto/armorblox:1.0.0.65856",
       "demisto/python3:3.8.2.6981",
       "demisto/python_pancloud:1.0.0.7740",
       "demisto/psycopg2",
       "demisto/lacework:1.0.0.47313",
       "demisto/py3-tools:1.0.0.43697",
       "demisto/genericsql:1.1.0.62758",
       "demisto/pycef:1.0.0.61516",
       "demisto/pwsh-infocyte:1.1.0.23036",
       "demisto/crypto:1.0.0.61689",
       "demisto/axonius:1.0.0.40908",
       "demisto/cloaken:1.0.0.44754",
       "demisto/ntlm:1.0.0.31381",
       "demisto/google-cloud-storage:1.0.0.63865",
       "demisto/nmap:1.0.0.46402",
       "demisto/flask-nginx:1.0.0.23674",
       "demisto/py3-tools:1.0.0.49159",
       "demisto/py3-tools:1.0.0.66616",
       "demisto/splunksdk-py3:1.0.0.66897",
       "demisto/bs4-py3:1.0.0.32198",
       "demisto/boto3py3:1.0.0.64969",
       "demisto/boto3py3:1.0.0.67091",
       "demisto/tesseract:1.0.0.62842",
       "demisto/googleapi-python3:1.0.0.40612",
       "demisto/opnsense:1.0.0.65922",
       "demisto/luminate:1.0.0.14061",
       "demisto/faker3:1.0.0.17991",
       "demisto/azure-kusto-data:1.0.0.66840",
       "demisto/googleapi-python3:1.0.0.64742",
       "demisto/taxii2:1.0.0.57584",
       "demisto/crypto:1.0.0.58095",
       "demisto/py3-tools:0.0.1.30715",
       "demisto/trustar:20.2.0.65839",
       "demisto/trustar:20.1.0.8039",
       "demisto/boto3:2.0.0.52592",
       "demisto/bottle:1.0.0.65861",
       "demisto/boto3py3:1.0.0.33827",
       "demisto/google-api-py3:1.0.0.64930",
       "demisto/netutils:1.0.0.46652",
       "demisto/googleapi-python3:1.0.0.62767",
       "demisto/netmiko:1.0.0.61830",
       "demisto/feed-performance-test:1.0.46565",
       "demisto/dnspython:1.0.0.24037",
       "demisto/sixgill:1.0.0.50510",
       "demisto/python3:3.8.3.8715",
       "demisto/dxl:1.0.0.65407",
       "demisto/dxl2:1.0.0.38570",
       "demisto/py3-tools:1.0.0.61931",
       "demisto/gdetect:1.0.0.29628",
       "demisto/googleapi-python3:1.0.0.64222",
       "demisto/teams:1.0.0.66853",
       "demisto/sixgill:1.0.0.23434",
       "demisto/vmware:2.0.0.43555",
       "demisto/unifi-video:1.0.0.16705",
       "demisto/python3:3.9.7.24076",
       "demisto/python3:3.10.6.33415",
       "demisto/py3-tools:1.0.0.49929",
       "demisto/python3:3.10.11.58677",
       "demisto/python3:3.8.6.13358",
       "demisto/etl2pcap:1.0.0.19032",
       "demisto/python3:3.10.9.45313",
       "demisto/bs4-py3:1.0.0.30051",
       "demisto/powershell:7.2.1.26295",
       "demisto/python-phash:1.0.0.25389",
       "demisto/sane-doc-reports:1.0.0.27897",
       "demisto/jq:1.0.0.24037",
       "demisto/py3-tools:1.0.0.38394",
       "demisto/ssl-analyze:1.0.0.14890",
       "demisto/python3:3.10.8.36650",
       "demisto/python3:3.10.4.27798",
       "demisto/python3:3.10.11.61265",
       "demisto/py3-tools:1.0.0.45198",
       "demisto/crypto:1.0.0.65874",
       "demisto/stringsifter:3.20230711.65151",
       "demisto/python3:3.10.9.40422",
       "demisto/python3:3.10.4.30607",
       "demisto/unzip:1.0.0.19258",
       "demisto/python3:3.10.4.29342",
       "demisto/python3:3.10.9.46032",
       "demisto/python3:3.10.9.46807",
       "demisto/pwsh-exchange:1.0.0.34118",
       "demisto/bs4-py3:1.0.0.24176",
       "demisto/python3:3.9.9.25564",
       "demisto/yarapy:1.0.0.10928",
       "demisto/bs4-tld:1.0.0.63807",
       "demisto/ansible-runner:1.0.0.47562",
       "demisto/pycountry:1.0.0.36195",
       "demisto/mlurlphishing:1.0.0.28347",
       "demisto/xsoar-tools:1.0.0.36076",
       "demisto/xsoar-tools:1.0.0.42327",
       "demisto/xsoar-tools:1.0.0.62936",
       "demisto/xsoar-tools:1.0.0.32653",
       "demisto/xsoar-tools:1.0.0.40869",
       "demisto/xsoar-tools:1.0.0.19258",
       "demisto/parse-emails:1.0.0.63730",
       "demisto/py3-tools:1.0.0.67089",
       "demisto/ml:1.0.0.45981",
       "demisto/dl:1.5",
       "demisto/ml:1.0.0.32340",
       "demisto/python3:3.9.5.20070",
       "demisto/python:2.7.18.10627",
       "demisto/ml:1.0.0.20606",
       "demisto/btfl-soup:1.0.1.20315",
       "demisto/python3:3.10.9.44472",
       "demisto/python3:3.8.3.9324",
       "demisto/pandas:1.0.0.31117",
       "demisto/sklearn:1.0.0.64885",
       "demisto/py3-tools:1.0.0.50499",
       "demisto/python3:3.10.8.37233",
       "demisto/bs4-py3:1.0.0.63660",
       "demisto/python3:3.10.12.62631",
       "demisto/python3:3.10.10.47713",
       "demisto/sklearn:1.0.0.12410",
       "demisto/sklearn:1.0.0.29944",
       "demisto/pcap-miner:1.0.0.32154",
       "demisto/pcap-miner:1.0.0.10664",
       "demisto/pcap-miner:1.0.0.9769",
       "demisto/pcap-miner:1.0.0.30520",
       "demisto/aquatone",
       "demisto/pdfx",
       "demisto/dl:1.1",
       "demisto/machine-learning",
       "demisto/python3:3.7.4.1150",
       "demisto/ml-telemetry",
       "demisto/python3:3.10.11.54132",
       "demisto/python3:3.8.6.12176",
       "demisto/ansible-runner:1.0.0.20884",
       "demisto/python3:3.10.1.27636",
       "demisto/flask-nginx:1.0.0.20328",
       "demisto/pyjwt3:1.0.0.49643",
       "demisto/crypto:1.0.0.52480",
       "demisto/googleapi-python3:1.0.0.12698",
       "demisto/fastapi:1.0.0.28667",
       "demisto/teams:1.0.0.43500",
       "demisto/readpdf:1.0.0.43274",
       "demisto/readpdf:1.0.0.50963",
       "demisto/mlurlphishing:1.0.0.61412",
       "demisto/iputils:1.0.0.4663",
       "demisto/unrar:1.4",
       "demisto/dnspython:1.0.0.12410",
       "demisto/powershell:7.1.3.22028",
       "demisto/parse-emails:1.0.0.65301",
       "demisto/pandas:1.0.0.26289",
       "demisto/processing-image-file:1.0.0.66515",
       "demisto/bs4-tld:1.0.0.21999",
       "demisto/xml-feed:1.0.0.65027",
       "demisto/office-utils:2.0.0.54910",
       "demisto/aquatone:2.0.0.36846",
       "demisto/office-utils:2.0.0.49835",
       "demisto/netutils:1.0.0.43061",
       "demisto/pcap-http-extractor:1.0.0.32113",
       "demisto/py3-tools:1.0.0.58222",
       "demisto/nltk:2.0.0.19143",
       "demisto/xsoar-tools:1.0.0.46482",
       "demisto/dempcap:1.0.0.14059",
       "demisto/docxpy:1.0.0.40261",
       "demisto/ssdeep:1.0.0.23743",
       "demisto/machine-learning:1.0.0.22015",
       "demisto/python3-deb:3.10.10.49238",
       "demisto/unzip:1.0.0.61858",
       "demisto/xslxwriter:1.0.0.45070",
       "demisto/py3-tools:1.0.0.46591",
       "demisto/btfl-soup:1.0.1.6233",
       "demisto/ml:1.0.0.62124",
       "demisto/taxii:1.0.0.48109",
       "demisto/ml:1.0.0.23334",
       "demisto/sklearn:1.0.0.49796",
       "demisto/xsoar-tools:1.0.0.58259",
       "demisto/mlclustering:1.0.0.23151",
       "demisto/sane-pdf-reports:1.0.0.62999",
       "demisto/sane-doc-reports:1.0.0.24118",
       "demisto/ml:1.0.0.30541",
       "demisto/ml:1.0.0.57750",
       "demisto/python:2.7.18.63476",
       "demisto/fetch-data:1.0.0.22177",
       "demisto/dl:1.4",
       "demisto/python3:3.9.1.14969",
       "demisto/rakyll-hey:1.0.0.49364",
       "demisto/python:2.7.18.9326",
       "demisto/docxpy:1.0.0.33689",
       "demisto/python3:3.7.4.977",
       "demisto/python3:3.10.8.35482",
       "demisto/python3:3.7.4.2245",
       "demisto/archer:1.0.0.270",
       "demisto/faker3:1.0.0.247",
       "demisto/sixgill:1.0.0.28665",
       "demisto/powershell-teams:1.0.0.22275"
    ]
    from demisto_sdk.commands.common.docker_helper import get_python_version
    from demisto_sdk.commands.common.logger import logger

    d = {}
    for image in docker_images:
        if image not in d:
            d[image] = {"python_version": get_python_version(image)}
    logger.info(f'{d=}')
    print(d)
    assert d == 1

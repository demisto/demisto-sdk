from pathlib import Path
from typing import Any, Dict, List, Tuple
from zipfile import ZipFile

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects import IncidentField, Layout, Mapper
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
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
    mocker.patch(
        "demisto_sdk.commands.common.docker_images_metadata.get_remote_file_from_api",
        return_value={
            "docker_images": {
                "python3": {
                    "3.10.11.54799": {"python_version": "3.10.11"},
                    "3.10.12.63474": {"python_version": "3.10.11"},
                }
            }
        },
    )
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


def mock_pack(
    name: str = "SamplePack",
    path: Path = Path("Packs"),
    repository: ContentDTO = None,
) -> Pack:
    pack = Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=path,
        name=name,
        display_name=name,
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
    if repository:
        repository.packs.append(pack)
    return pack


def mock_integration(
    name: str = "SampleIntegration",
    path: Path = Path("Packs"),
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
) -> Integration:
    integration = Integration(
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
        docker_image="demisto/python3:3.10.11.54799",
        category="blabla",
        commands=[Command(name="test-command", description="")],
    )
    if pack is not None:
        pack.content_items.integration.append(integration)
        build_in_pack_relationship(pack, integration)
        add_uses_relationships(pack, integration, uses)
    return integration


def mock_script(
    name: str = "SampleScript",
    marketplaces: List[MarketplaceVersions] = [MarketplaceVersions.XSOAR],
    skip_prepare: List[str] = [],
    path: Path = Path("Packs"),
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
    importing_items: List[ContentItem] = None,
) -> Script:
    script = Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=path,
        fromversion="5.0.0",
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=marketplaces,
        deprecated=False,
        type="python3",
        docker_image="demisto/python3:3.10.11.54799",
        tags=[],
        is_test=False,
        skip_prepare=skip_prepare,
    )
    if pack:
        pack.content_items.script.append(script)
        build_in_pack_relationship(pack, script)
        add_uses_relationships(pack, script, uses)
        if importing_items is not None:
            # Note: `importing_items` won't necessarily be actually of `pack`,
            # But for mocking purposes it's enough.
            pack.relationships.add_batch(
                RelationshipType.IMPORTS,
                [
                    mock_relationship(
                        ci.object_id,
                        ci.content_type,
                        script.object_id,
                        script.content_type,
                    )
                    for ci in importing_items
                ],
            )

    return script


def mock_classifier(
    name: str = "SampleClassifier",
    path: Path = Path("Packs"),
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
) -> Classifier:
    classifier = Classifier(
        id=name,
        content_type=ContentType.CLASSIFIER,
        node_id=f"{ContentType.CLASSIFIER}:{name}",
        path=path,
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
    if pack:
        pack.content_items.classifier.append(classifier)
        build_in_pack_relationship(pack, classifier)
        add_uses_relationships(pack, classifier, uses)
    return classifier


def mock_playbook(
    name: str = "SamplePlaybook",
    path: Path = Path("Packs"),
    marketplaces: List[MarketplaceVersions] = [MarketplaceVersions.XSOAR],
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
) -> Playbook:
    playbook = Playbook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=path,
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=marketplaces,
        deprecated=False,
        is_test=False,
    )
    if pack:
        pack.content_items.playbook.append(playbook)
        build_in_pack_relationship(pack, playbook)
        add_uses_relationships(pack, playbook, uses)
    return playbook


def mock_test_playbook(
    name: str = "SampleTestPlaybook",
    path: Path = Path("Packs"),
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
    tested_items: List[ContentItem] = None,
) -> TestPlaybook:
    test_playbook = TestPlaybook(
        id=name,
        # content_type=ContentType.TEST_PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=path,
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        is_test=True,
    )
    if pack:
        pack.content_items.test_playbook.append(test_playbook)
        build_in_pack_relationship(pack, test_playbook)
        add_uses_relationships(pack, test_playbook, uses)
        if tested_items is not None:
            pack.relationships.add_batch(
                RelationshipType.TESTED_BY,
                [
                    mock_relationship(
                        ci.object_id,
                        ci.content_type,
                        test_playbook.object_id,
                        test_playbook.content_type,
                    )
                    for ci in tested_items
                ],
            )

    return test_playbook


def mock_widget(
    name: str = "SampleWidget",
    path: Path = Path("Packs"),
    pack: Pack = None,
    uses: List[Tuple[ContentItem, bool]] = None,
) -> Widget:
    widget = Widget(
        id=name,
        content_type=ContentType.WIDGET,
        node_id=f"{ContentType.WIDGET}:{name}",
        path=path,
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        widget_type="number",
        data_type="roi",
    )
    if pack:
        pack.content_items.widget.append(widget)
        build_in_pack_relationship(pack, widget)
        add_uses_relationships(pack, widget, uses)
    return widget


def mock_mapper(path: str, name: str = "SampleMapper", data: Dict = {}):
    return Mapper(
        id=name,
        content_type=ContentType.MAPPER,
        node_id=f"{ContentType.MAPPER}:{name}",
        path=path,
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
        data=data,
    )


def mock_layout(path: str, name: str = "SampleLayout", data: Dict = {}):
    return Layout(
        id=name,
        content_type=ContentType.LAYOUT,
        node_id=f"{ContentType.LAYOUT}:{name}",
        path=path,
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
        data=data,
        group="incident",
        edit=False,
        indicators_details=False,
        indicators_quick_view=False,
        quick_view=False,
        close=False,
        details=False,
        details_v2=True,
        mobile=False,
    )


def mock_incident_field(
    cli_name: str,
    path: str,
    marketplaces: List,
    data: Dict = {},
    name: str = "SampleIncidentField",
):
    return IncidentField(
        id=name,
        content_type=ContentType.INCIDENT_FIELD,
        node_id=f"{ContentType.INCIDENT_FIELD}:{name}",
        path=path,
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
        data=data,
        cli_name=cli_name,
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


def build_in_pack_relationship(
    pack: Pack,
    content_item: ContentItem,
) -> None:
    """Given a pack with content items,
    creates the "in pack" and "has command" basic relationships.

    Args:
        pack (Pack): a pack for which to build basic relationships.
    """
    pack.relationships.add(
        RelationshipType.IN_PACK,
        **mock_relationship(
            content_item.object_id,
            content_item.content_type,
            pack.object_id,
            ContentType.PACK,
        ),
    )
    if isinstance(content_item, Integration):
        for command in content_item.commands:
            pack.relationships.add(
                RelationshipType.HAS_COMMAND,
                **mock_relationship(
                    content_item.object_id,
                    content_item.content_type,
                    command.object_id,
                    ContentType.COMMAND,
                    description="",
                    deprecated=False,
                ),
            )


def add_uses_relationships(
    pack: Pack,
    content_item: ContentItem,
    used_content_items: List[Tuple[ContentItem, bool]] = None,
) -> None:
    if used_content_items is not None:
        pack.relationships.add_batch(
            RelationshipType.USES_BY_ID,
            [
                mock_relationship(
                    content_item.object_id,
                    content_item.content_type,
                    ci.object_id,
                    ci.content_type,
                    mandatorily=mandatorily,
                )
                for ci, mandatorily in used_content_items
            ],
        )


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
        mocker.patch.object(
            PackMetadata, "_get_tags_from_landing_page", retrun_value={}
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
            - Make sure the integrations are not recognized as duplicates and the command succeeds.
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
            - Make sure the integrations are not recognized as duplicates and the command succeeds.
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
            - Running neo4j_service.stop()
        Then:
            - Make sure no exception is raised.
        """
        neo4j_service.stop()

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
        mocker.patch.object(
            PackMetadata, "_get_tags_from_landing_page", retrun_value={}
        )

        pack = repo.create_pack("TestPack")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        pack.create_script(name="getIncident")
        pack.create_script(
            name="setIncident",
            skip_prepare=[SKIP_PREPARE_SCRIPT_NAME],
        )

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

    @pytest.mark.parametrize(
        "docker_image, expected_python_version, is_taken_from_dockerhub",
        [
            ("demisto/python3:3.10.11.54799", "3.10.11", False),
            ("demisto/pan-os-python:1.0.0.68955", "3.10.5", True),
        ],
    )
    def test_create_content_graph_with_python_version(
        self,
        mocker,
        repo: Repo,
        docker_image: str,
        expected_python_version: str,
        is_taken_from_dockerhub: bool,
    ):
        """
        Given:
            Case A: docker image that its python version exists in the dockerfiles metadata file
            Case B: docker image that its python version does not exist in the dockerfiles metadata file

        When:
            - Running create_content_graph()

        Then:
            - make sure that in both cases the python_version (lazy property) was loaded into the Integration
              model because we want it in the graph metadata
            Case A: the python version was taken from the dockerfiles metadata file
            Case B: the python version was taken from the dockerhub api
        """
        from packaging.version import Version

        dockerhub_api_mocker = mocker.patch(
            "demisto_sdk.commands.common.docker_helper._get_python_version_from_dockerhub_api",
            return_value=Version(expected_python_version),
        )

        pack = repo.create_pack()
        pack.create_integration(docker_image=docker_image)

        with ContentGraphInterface() as interface:
            create_content_graph(interface)
            integrations = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.INTEGRATION,
            )
        assert expected_python_version == integrations[0].to_dict()["python_version"]
        assert dockerhub_api_mocker.called == is_taken_from_dockerhub

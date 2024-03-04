from pathlib import Path
from typing import Any, Dict, List, Tuple
from zipfile import ZipFile

import pytest

from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    RelationshipType,
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
###### TO BE DELETED AFTER USING THE TestSuite OBJECTS IN ALL GRAPH TEST - START ######


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
        docker_image=DockerImage("demisto/python3:3.10.11.54799"),
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
        docker_image=DockerImage("demisto/python3:3.10.11.54799"),
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


###### TO BE DELETED AFTER USING THE TestSuite OBJECTS IN ALL GRAPH TEST - END ######
def create_mini_content(graph_repo: Repo):
    """
    Create the following content in the repo
    - A pack SamplePack, containing:
        - An integration SampleIntegration, which:
            1. Has a single command test-command.
            2. Imports TestApiModule in the code.
            3. Is tested by SampleTestPlaybook which defined in pack SamplePack2.
            4. A default classifier SampleClassifier which defined in pack SamplePack2.
        - A script SampleScript that uses SampleScript2.
    - A pack SamplePack2, containing:
        1. A script TestApiModule that uses SampleScript2 which defined in pack SamplePack2.
        2. A classifier SampleClassifier.
        3. A test playbook SampleTestPlaybook.
    - A pack SamplePack3, containing:
        1. A script SampleScript2

    Args:
        graph_repo (Repo): the repo to work with
    """
    sample_pack = graph_repo.create_pack("SamplePack")
    sample_pack.create_script(
        "SampleScript", code='demisto.execute_command("SampleScriptTwo", dArgs)'
    )
    integration = sample_pack.create_integration(
        name="SampleIntegration", code="from TestApiModule import *"
    )
    integration.set_commands(["test-command"])
    integration.set_data(
        tests=["SampleTestPlaybook"], defaultclassifier="SampleClassifier"
    )

    sample_pack_2 = graph_repo.create_pack("SamplePack2")
    sample_pack_2.create_script(
        "TestApiModule", code='demisto.execute_command("SampleScriptTwo", dArgs)'
    )
    sample_pack_2.create_test_playbook("SampleTestPlaybook")
    sample_pack_2.create_classifier("SampleClassifier")

    sample_pack_3 = graph_repo.create_pack("SamplePack3")
    sample_pack_3.create_script("SampleScriptTwo")


class TestCreateContentGraph:
    def test_create_content_graph_end_to_end(
        self, graph_repo: Repo, tmp_path: Path, mocker
    ):
        """
        Given:
            - A repository with a pack TestPack, containing an integration TestIntegration.
        When:
            - Running create_content_graph()
        Then:
            - Make sure the service remains available by querying for all content items in the graph.
            - Make sure there is a single integration in the query response.
        """
        repo = graph_repo
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

        interface = repo.create_graph(output_path=tmp_path)
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
        returned_integration = integration.get_graph_object(interface)
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

    def test_create_content_graph_relationships(self, graph_repo: Repo):
        """
        Given:
            - A repo contain content structure defined in create_mini_content
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph has all the corresponding nodes and relationships.
        """
        create_mini_content(graph_repo)

        interface = graph_repo.create_graph()

        sample_pack = graph_repo.packs[0]
        sample_pack_graph_obj = sample_pack.get_graph_object(interface)
        sample_pack_2_graph_obj = graph_repo.packs[1].get_graph_object(interface)
        sample_pack_3_graph_obj = graph_repo.packs[2].get_graph_object(interface)

        integration_graph_obj = sample_pack.integrations[0].get_graph_object(interface)
        sample_pack_script_graph_obj = sample_pack.scripts[0].get_graph_object(
            interface
        )
        # assert sample_pack depends on sample_pack_2 and sample_pack_3
        for rel_type, relations in sample_pack_graph_obj.relationships_data.items():
            for r in relations:
                if rel_type == RelationshipType.DEPENDS_ON:
                    assert r.content_item_to in [
                        sample_pack_2_graph_obj,
                        sample_pack_3_graph_obj,
                    ]
                elif rel_type == RelationshipType.IN_PACK:
                    assert r.content_item_to in [
                        integration_graph_obj,
                        sample_pack_script_graph_obj,
                    ]
                else:
                    assert False

        # assert integration relationships
        rel_map = {
            RelationshipType.USES: sample_pack_2_graph_obj.content_items.classifier[0],
            RelationshipType.TESTED_BY: sample_pack_2_graph_obj.content_items.test_playbook[
                0
            ],
            RelationshipType.IMPORTS: sample_pack_2_graph_obj.content_items.script[0],
            RelationshipType.IN_PACK: sample_pack_graph_obj,
        }
        for rel_type, rel_to_obj in rel_map.items():
            content_item_to = next(
                iter(integration_graph_obj.relationships_data[rel_type])
            ).content_item_to
            assert content_item_to == rel_to_obj or content_item_to.not_in_repository

    def test_create_content_graph_two_integrations_with_same_command(
        self,
        graph_repo: Repo,
    ):
        """
        Given:
            - A repo with pack, containing two integrations,
              each has a command named test-command.
        When:
            - Running create_content_graph().
        Then:
            - Make sure only one command node was created.
        """
        pack = graph_repo.create_pack()
        pack.create_integration("SampleIntegration1").set_commands(["test-command"])
        pack.create_integration("SampleIntegration2").set_commands(["test-command"])

        interface = graph_repo.create_graph()

        assert (
            pack.integrations[0].get_graph_object(interface).object_id
            == "SampleIntegration1"
        )
        assert (
            pack.integrations[1].get_graph_object(interface).object_id
            == "SampleIntegration2"
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
        self, graph_repo: Repo
    ):
        pack = graph_repo.create_pack()
        pack.create_playbook().add_default_task(task_script_name="NotExistingScript")

        interface = graph_repo.create_graph()
        script = interface.search(object_id="NotExistingScript")[0]

        assert script.not_in_repository

    def test_create_content_graph_duplicate_widgets(self, graph_repo: Repo):
        """
        Given:
            - A repository with a pack TestPack, containing two widgets
              with the exact same id, fromversion and marketplaces properties.
        When:
            - Running create_content_graph().
        Then:
            - Make sure both widgets exist in the graph.
        """
        pack = graph_repo.create_pack()

        pack.create_widget().set_data(id="SampleWidget")
        pack.create_widget().set_data(id="SampleWidget")

        interface = graph_repo.create_graph()

        assert len(interface.search(object_id="SampleWidget")) == 2

    def test_create_content_graph_duplicate_integrations_different_marketplaces(
        self, graph_repo: Repo
    ):
        pack = graph_repo.create_pack()
        pack.create_integration().set_data(
            **{
                "commonfields.id": "SampleIntegration",
                "marketplaces": [MarketplaceVersions.XSOAR.value],
            }
        )
        pack.create_integration().set_data(
            **{
                "commonfields.id": "SampleIntegration",
                "marketplaces": [MarketplaceVersions.MarketplaceV2.value],
            }
        )

        interface = graph_repo.create_graph()

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
        graph_repo: Repo,
    ):
        """
        Given:
            - A repository with a pack, containing two integrations
              with the exact same properties but have different version ranges.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the integrations are not recognized as duplicates and the command succeeds.
        """
        pack = graph_repo.create_pack()

        pack.create_integration().set_data(
            **{"commonfields.id": "SampleIntegration", "toversion": "6.0.0"}
        )
        pack.create_integration().set_data(
            **{"commonfields.id": "SampleIntegration", "toversion": "6.0.2"}
        )

        interface = graph_repo.create_graph()

        assert len(interface.search(object_id="SampleIntegration")) == 2

    def test_create_content_graph_empty_repository(self, graph_repo: Repo):
        """
        Given:
            - An empty repository.
        When:
            - Running create_content_graph().
        Then:
            - Make sure the graph are empty.
        """
        interface = graph_repo.create_graph()
        assert not interface.search()

    def test_create_content_graph_incident_to_alert_scripts(
        self, graph_repo: Repo, tmp_path: Path
    ):
        """
        Given:
            - A pack, containing two scripts,
            one (getIncident) is set with skipping the preparation of incident to alert
            and the other (setIncident) is not.
        When:
            - Running create_content_graph().
        Then:
            - Ensure that `getIncident` script has passed the prepare process as expected.
            - Ensure the 'setIncident' script has not passed incident to alert preparation.
        """
        pack = graph_repo.create_pack()
        pack.create_script(name="getIncident")
        pack.create_script(name="setIncident", skip_prepare=[SKIP_PREPARE_SCRIPT_NAME])

        interface = graph_repo.create_graph(output_path=tmp_path)
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

        with ChangeCWD(graph_repo.path):
            content_cto.dump(tmp_path, MarketplaceVersions.MarketplaceV2, zip=False)
        scripts_path = tmp_path / pack.name / "Scripts"
        assert (scripts_path / "script-getIncident.yml").exists()
        assert (scripts_path / "script-getAlert.yml").exists()
        assert (scripts_path / "script-setIncident.yml").exists()
        assert not (scripts_path / "script-setAlert.yml").exists()

    def test_create_content_graph_relationships_from_metadata(
        self,
        graph_repo: Repo,
    ):
        """
        Given:
            - A pack Core, which depends on NonCorePack according to the pack metadata
        When:
            - Running create_content_graph().
        Then:
            - Make sure the relationship's is_test is not null.
        """
        graph_repo.create_pack("NonCorePack")
        graph_repo.create_pack("Core").set_data(
            dependencies={
                "NonCorePack": {"mandatory": True, "display_name": "Non Core Pack"}
            }
        )

        interface = graph_repo.create_graph()

        where_test_null = "WHERE r.is_test IS NULL"
        query = "MATCH p=()-[r:DEPENDS_ON]->() {where} RETURN p"
        data = interface.run_single_query(query.format(where=""))[0]["p"]
        empty_data = interface.run_single_query(query.format(where=where_test_null))

        assert data[0]["object_id"] == "Core"
        assert data[1] == "DEPENDS_ON"
        assert data[2]["object_id"] == "NonCorePack"
        assert not empty_data

    @pytest.mark.parametrize(
        "docker_image, expected_python_version, is_taken_from_dockerhub",
        [
            ("demisto/python3:3.10.11.54799", "3.10.11", False),
            ("demisto/pan-os-python:1.0.0.68955", "3.10.12", True),
        ],
    )
    def test_create_content_graph_with_python_version(
        self,
        mocker,
        graph_repo: Repo,
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

        from demisto_sdk.commands.common.files.file import File

        dockerhub_api_mocker = mocker.patch(
            "demisto_sdk.commands.common.docker_helper._get_python_version_from_dockerhub_api",
            return_value=Version(expected_python_version),
        )
        mocker.patch(
            "demisto_sdk.commands.common.docker_images_metadata.DockerImagesMetadata._instance",
            None,
        )
        mocker.patch.object(
            File,
            "read_from_github_api",
            return_value={
                "docker_images": {
                    "python3": {
                        "3.10.11.54799": {"python_version": "3.10.11"},
                        "3.10.12.63474": {"python_version": "3.10.11"},
                    }
                }
            },
        )

        pack = graph_repo.create_pack()
        pack.create_integration(docker_image=docker_image)

        interface = graph_repo.create_graph()
        integrations = interface.search(
            marketplace=MarketplaceVersions.XSOAR,
            content_type=ContentType.INTEGRATION,
        )
        assert expected_python_version == integrations[0].python_version
        assert dockerhub_api_mocker.called == is_taken_from_dockerhub

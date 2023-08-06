from typing import List, Dict, Any
import logging
import pytest
from pathlib import Path
from demisto_sdk.commands.content_graph import neo4j_service
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.integration import Command
from demisto_sdk.commands.content_graph.tests.update_content_graph_test import _get_pack_by_id
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph,
    stop_content_graph,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects import Mapper, IncidentField, Integration, Layout
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.common.constants import MarketplaceVersions, OLDEST_SUPPORTED_VERSION
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import get_dict_from_file


FORMAT_CMD = "format"


@pytest.fixture(autouse=True)
def setup_method(mocker, repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
    stop_content_graph()


@pytest.fixture
def repository(mocker, repo) -> ContentDTO:
    repository = ContentDTO(
        path=Path(repo.path),
        packs=[],
    )
    relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SamplePack",
                ContentType.PACK,
            ),
            mock_relationship(
                "Mapper - Incoming Mapper",
                ContentType.MAPPER,
                "SamplePack",
                ContentType.PACK,
            ),
            mock_relationship(
                "Unknown Incident Field",
                ContentType.INCIDENT_FIELD,
                "SamplePack",
                ContentType.PACK,
            ),
            mock_relationship(
                "Layout",
                ContentType.LAYOUT,
                "SamplePack",
                ContentType.PACK,
            ),
            mock_relationship(
                "incidentfield",
                ContentType.INCIDENT_FIELD,
                "SamplePack",
                ContentType.PACK,
            ),
        ],
        RelationshipType.USES: [
            mock_relationship(
                "Mapper - Incoming Mapper",
                ContentType.MAPPER,
                "Unknown Incident Field",
                ContentType.INCIDENT_FIELD,
                name="Unknown Incident Field",
                description="",
                deprecated=False,
            ),
            mock_relationship(
                "Layout",
                ContentType.LAYOUT,
                "Unknown Incident Field",
                ContentType.INCIDENT_FIELD,
                name="Unknown Incident Field",
                description="",
                deprecated=False,
            ),
            mock_relationship(
                "Layout",
                ContentType.LAYOUT,
                "incidentfield",
                ContentType.INCIDENT_FIELD,
                name="Known Incident Field",
                description="",
                deprecated=False,
            )
        ],
    }

    relationships2 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "originalincidentfield",
                ContentType.INCIDENT_FIELD,
                "SamplePack2",
                ContentType.PACK,
            ),
            mock_relationship(
                "alias1incidentfield",
                ContentType.INCIDENT_FIELD,
                "SamplePack2",
                ContentType.PACK,
            ),
            mock_relationship(
                "alias2incidentfield",
                ContentType.INCIDENT_FIELD,
                "SamplePack2",
                ContentType.PACK,
            ),
        ]
    }

    mapper_data = {
        "description": "",
        "feed": False,
        "id": "Mapper - Incoming Mapper",
        "mapping": {
            "Mapper Finding": {
                "dontMapEventToLabels": True,
                "internalMapping": {
                    "Unknown Incident Field": {
                        "simple": "Item"
                    }
                }
            },
        },
        "name": "Mapper - Incoming Mapper",
        "type": "mapping-incoming",
        "version": -1,
        "fromVersion": OLDEST_SUPPORTED_VERSION
    }
    layout_content = {
        "detailsV2": {
            "tabs": [
                {
                    "id": "caseinfoid",
                    "name": "Incident Info",
                    "sections": [
                        {
                            "displayType": "ROW",
                            "h": 2,
                            "i": "caseinfoid-fce71720-98b0-11e9-97d7-ed26ef9e46c8",
                            "isVisible": True,
                            "items": [
                                {
                                    "endCol": 2,
                                    "fieldId": "Unknown Incident Field",
                                    "height": 22,
                                    "id": "id1",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0
                                },
                                {
                                    "endCol": 2,
                                    "fieldId": "incidentfield",
                                    "height": 22,
                                    "id": "id2",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "group": "incident",
        "id": "Layout",
        "name": "Layout",
        "system": False,
        "version": -1,
        "fromVersion": OLDEST_SUPPORTED_VERSION,
        "description": "",
        "marketplaces": ["xsoar"]
    }
    incident_field_content = {
        "cliName": "incidentfield",
        "id": "incident_incidentfield",
        "name": "Incident Field",
        "marketplaces": [
            MarketplaceVersions.XSOAR
        ]
    }
    original_incident_field_content = {
        "cliName": "originalincidentfield",
        "id": "incident_originalincidentfield",
        "name": "Original Incident Field",
        "Aliases": [
            {
                "cliName": "alias1incidentfield",
                "type": "shortText",
                "name": "Alias1 Incident Field"
            }
        ],
        "marketplaces": [
            MarketplaceVersions.MarketplaceV2
        ]
    }
    alias1_incident_field_content = {
        "cliName": "alias1incidentfield",
        "id": "incident_alias1incidentfield",
        "name": "Alias1 Incident Field",
        "marketplaces": [
            MarketplaceVersions.MarketplaceV2, MarketplaceVersions.XSOAR
        ]
    }
    alias2_incident_field_content = {
        "cliName": "alias2incidentfield",
        "id": "incident_alias2incidentfield",
        "name": "Alias2 Incident Field",
        "marketplaces": [
            MarketplaceVersions.XSOAR
        ]
    }
    pack_1 = repo.create_pack("PackName")
    mapper = pack_1.create_mapper(
        name="mapper",
        content=mapper_data
    )
    layout = pack_1.create_layoutcontainer(
        name="Layout",
        content=layout_content
    )
    incident_field = pack_1.create_incident_field(
        name="incidentfield",
        content=incident_field_content
    )

    pack_2 = repo.create_pack("PackName2")
    original_incident_field = pack_2.create_incident_field(
        name='originalincidentfield',
        content=original_incident_field_content
    )
    alias1_incident_field = pack_2.create_incident_field(
        name='alias1incidentfield',
        content=alias1_incident_field_content
    )
    alias2_incident_field = pack_2.create_incident_field(
        name='alias2incidentfield',
        content=alias2_incident_field_content
    )

    pack1 = mock_pack()
    pack1.relationships = relationships
    pack1.content_items.integration.append(mock_integration())
    pack1.content_items.mapper.append(mock_mapper(name='Mapper - Incoming Mapper', data=mapper_data, path=mapper.path))
    pack1.content_items.layout.append(mock_layout(name='Layout', data=layout_content, path=layout.path))
    pack1.content_items.incident_field.append(mock_incident_field(cli_name='incidentfield',
                                                                  path=incident_field.path,
                                                                  data=incident_field_content,
                                                                  name='incidentfield',
                                                                  marketplaces=[MarketplaceVersions.XSOAR]))
    pack2 = mock_pack('SamplePack2')
    pack2.relationships = relationships2
    pack2.content_items.incident_field.append(mock_incident_field(cli_name='originalincidentfield',
                                                                  path=original_incident_field.path,
                                                                  data=original_incident_field_content,
                                                                  name='originalincidentfield',
                                                                  marketplaces=[MarketplaceVersions.MarketplaceV2]))
    pack2.content_items.incident_field.append(mock_incident_field(cli_name='alias1incidentfield',
                                                                  path=alias1_incident_field.path,
                                                                  data=alias1_incident_field_content,
                                                                  name='alias1incidentfield',
                                                                  marketplaces=[MarketplaceVersions.MarketplaceV2,
                                                                                MarketplaceVersions.XSOAR]))
    pack2.content_items.incident_field.append(mock_incident_field(cli_name='alias2incidentfield',
                                                                  path=alias2_incident_field.path,
                                                                  data=alias2_incident_field_content,
                                                                  name='alias2incidentfield',
                                                                  marketplaces=[MarketplaceVersions.XSOAR]))
    repository.packs.extend([pack1, pack2])

    def mock__create_content_dto(packs_to_update: List[str]) -> List[ContentDTO]:
        if not packs_to_update:
            return [repository]
        repo_copy = repository.copy()
        repo_copy.packs = [p for p in repo_copy.packs if p.object_id in packs_to_update]
        return [repo_copy]

    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        side_effect=mock__create_content_dto,
    )

    return repository


def mock_relationship(
    source: str,
    source_type: ContentType,
    target: str,
    target_type: ContentType,
    source_fromversion: str = OLDEST_SUPPORTED_VERSION,
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
        fromversion=OLDEST_SUPPORTED_VERSION,
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


def mock_mapper(path: str, name: str = "SampleMapper", data: Dict = {}):
    return Mapper(
        id=name,
        content_type=ContentType.MAPPER,
        node_id=f"{ContentType.MAPPER}:{name}",
        path=path,
        fromversion=OLDEST_SUPPORTED_VERSION,
        display_name=name,
        toversion="99.99.99",
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        type="python3",
        docker_image="mock:docker",
        tags=[],
        is_test=False,
        data=data
    )

def mock_layout(path: str, name: str = "SampleLayout", data: Dict = {}):
    return Layout(
        id=name,
        content_type=ContentType.LAYOUT,
        node_id=f"{ContentType.LAYOUT}:{name}",
        path=path,
        fromversion=OLDEST_SUPPORTED_VERSION,
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
        group='incident',
        edit=False,
        indicators_details=False,
        indicators_quick_view=False,
        quick_view=False,
        close=False,
        details=False,
        details_v2=True,
        mobile=False
    )


def mock_incident_field(cli_name: str, path: str, marketplaces: List, data: Dict= {}, name: str = "SampleIncidentField"):
    return IncidentField(
        id=name,
        content_type=ContentType.INCIDENT_FIELD,
        node_id=f"{ContentType.INCIDENT_FIELD}:{name}",
        path=path,
        fromversion=OLDEST_SUPPORTED_VERSION,
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
        cli_name=cli_name
    )


def test_format_mapper_with_graph_remove_unknown_content(mocker, monkeypatch, repository, repo):
    """
    Given
    - A mapper.

    When
    - Running format command on it

    Then
    -  Ensure that the unknown field was removed from the mapper.
    """

    with ContentGraphInterface() as interface:
        create_content_graph(interface)

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")

    pack_graph_object = _get_pack_by_id(repository, "SamplePack")
    mapper_graph_object = pack_graph_object.content_items.mapper[0]
    mapper_path = str(mapper_graph_object.path)
    mocker.patch(
        "demisto_sdk.commands.format.format_module.ContentGraphInterface",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(main, [FORMAT_CMD, "-i", mapper_path, "-at", "-y"])
    message = "Removing the fields {'Unknown Incident Field'}" + f" from the mapper {mapper_path} " \
              f"because they aren't in the content repo."
    assert result.exit_code == 0
    assert not result.exception
    assert str_in_call_args_list(logger_info.call_args_list, message)

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(mapper_path)[0]
    assert file_content.get("mapping", {}).get('Mapper Finding', {}).get('internalMapping') == {}


def test_format_layout_with_graph_remove_unknown_content(mocker, monkeypatch, repository, repo):
    """
    Given
    - A layout.

    When
    - Running format command on it

    Then
    -  Ensure that the unknown field was removed from the layout.
    """

    with ContentGraphInterface() as interface:
        create_content_graph(interface)

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")

    pack_graph_object = _get_pack_by_id(repository, "SamplePack")
    layout_graph_object = pack_graph_object.content_items.layout[0]
    layout_path = str(layout_graph_object.path)
    mocker.patch(
        "demisto_sdk.commands.format.format_module.ContentGraphInterface",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(main, [FORMAT_CMD, "-i", layout_path, "-at", "-y"])
    message = "Removing the fields {'Unknown Incident Field'}" + f" from the layout {layout_path} " \
                                                                 f"because they aren't in the content repo."
    assert result.exit_code == 0
    assert not result.exception
    assert str_in_call_args_list(logger_info.call_args_list, message)

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(layout_path)[0]
    expected_layout_content = [{
        "endCol": 2,
        "fieldId": "incidentfield",
        "height": 22,
        "id": "id2",
        "index": 0,
        "sectionItemType": "field",
        "startCol": 0
    }]
    assert file_content.get('detailsV2', {}).get('tabs', [])[0].get('sections', {})[0].get('items', []) == \
           expected_layout_content


def test_format_incident_field_graph_fix_aliases_marketplace(mocker, monkeypatch, repository, repo):
    """
    Given
    - An incident field.

    When
    - Running format command on it

    Then
    -  Ensure that the aliases incident fields marketplaces field contains only xsoar.
    """

    with ContentGraphInterface() as interface:
        create_content_graph(interface)

    monkeypatch.setenv("COLUMNS", "1000")

    pack_graph_object = _get_pack_by_id(repository, "SamplePack2")
    original_incident_field_path = str(pack_graph_object.content_items.incident_field[0].path)  # original incident field
    alias1_incident_field_path = str(pack_graph_object.content_items.incident_field[1].path)
    alias2_incident_field_path = str(pack_graph_object.content_items.incident_field[2].path)
    mocker.patch(
        "demisto_sdk.commands.format.format_module.ContentGraphInterface",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(main, [FORMAT_CMD, "-i", original_incident_field_path, "-at", "-y"])

    assert result.exit_code == 0
    assert not result.exception

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    alias1_content = get_dict_from_file(alias1_incident_field_path)[0]
    alias2_content = get_dict_from_file(alias2_incident_field_path)[0]
    assert alias1_content.get('marketplaces', []) == ['xsoar']
    assert alias2_content.get('marketplaces', []) == ['xsoar']
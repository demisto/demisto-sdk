import logging
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_dict_from_file
from demisto_sdk.commands.content_graph import neo4j_service
from demisto_sdk.commands.content_graph.commands.create import create_content_graph
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_incident_field,
    mock_integration,
    mock_layout,
    mock_mapper,
    mock_pack,
    mock_relationship,
)
from demisto_sdk.commands.content_graph.tests.update_content_graph_test import (
    _get_pack_by_id,
)
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

FORMAT_CMD = "format"


@pytest.fixture(autouse=True)
def setup_method(mocker, tmp_path_factory, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc
    from demisto_sdk.commands.common.files.file import File

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
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
            ),
        ],
    }

    mapper_data = {
        "description": "",
        "feed": False,
        "id": "Mapper - Incoming Mapper",
        "mapping": {
            "Mapper Finding": {
                "dontMapEventToLabels": True,
                "internalMapping": {"Unknown Incident Field": {"simple": "Item"}},
            },
        },
        "name": "Mapper - Incoming Mapper",
        "type": "mapping-incoming",
        "version": -1,
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
                                    "startCol": 0,
                                },
                                {
                                    "endCol": 2,
                                    "fieldId": "incidentfield",
                                    "height": 22,
                                    "id": "id2",
                                    "index": 0,
                                    "sectionItemType": "field",
                                    "startCol": 0,
                                },
                            ],
                        }
                    ],
                }
            ]
        },
        "group": "incident",
        "id": "Layout",
        "name": "Layout",
        "system": False,
        "version": -1,
        "description": "",
        "marketplaces": ["xsoar"],
    }
    incident_field_content = {
        "cliName": "incidentfield",
        "id": "incident_incidentfield",
        "name": "Incident Field",
        "marketplaces": [MarketplaceVersions.XSOAR],
    }
    original_incident_field_content = {
        "cliName": "originalincidentfield",
        "id": "incident_originalincidentfield",
        "name": "Original Incident Field",
        "Aliases": [
            {
                "cliName": "alias1incidentfield",
                "type": "shortText",
                "name": "Alias1 Incident Field",
            },
            {
                "cliName": "alias2incidentfield",
                "type": "shortText",
                "name": "Alias2 Incident Field",
            },
        ],
        "marketplaces": [MarketplaceVersions.MarketplaceV2],
    }
    alias1_incident_field_content = {
        "cliName": "alias1incidentfield",
        "id": "incident_alias1incidentfield",
        "name": "Alias1 Incident Field",
        "marketplaces": [MarketplaceVersions.MarketplaceV2, MarketplaceVersions.XSOAR],
    }
    alias2_incident_field_content = {
        "cliName": "alias2incidentfield",
        "id": "incident_alias2incidentfield",
        "name": "Alias2 Incident Field",
        "marketplaces": [MarketplaceVersions.XSOAR],
    }
    pack_1 = repo.create_pack("SamplePack")
    mapper = pack_1.create_mapper(name="mapper", content=mapper_data)
    layout = pack_1.create_layoutcontainer(name="Layout", content=layout_content)
    incident_field = pack_1.create_incident_field(
        name="incidentfield", content=incident_field_content
    )

    pack_2 = repo.create_pack("SamplePack2")
    original_incident_field = pack_2.create_incident_field(
        name="originalincidentfield", content=original_incident_field_content
    )
    alias1_incident_field = pack_2.create_incident_field(
        name="alias1incidentfield", content=alias1_incident_field_content
    )
    alias2_incident_field = pack_2.create_incident_field(
        name="alias2incidentfield", content=alias2_incident_field_content
    )

    pack1 = mock_pack()
    pack1.relationships = relationships
    pack1.content_items.integration.append(mock_integration())
    pack1.content_items.mapper.append(
        mock_mapper(name="Mapper - Incoming Mapper", data=mapper_data, path=mapper.path)
    )
    pack1.content_items.layout.append(
        mock_layout(name="Layout", data=layout_content, path=layout.path)
    )
    pack1.content_items.incident_field.append(
        mock_incident_field(
            cli_name="incidentfield",
            path=incident_field.path,
            data=incident_field_content,
            name="incidentfield",
            marketplaces=[MarketplaceVersions.XSOAR],
        )
    )
    pack2 = mock_pack("SamplePack2")
    pack2.content_items.incident_field.append(
        mock_incident_field(
            cli_name="originalincidentfield",
            path=original_incident_field.path,
            data=original_incident_field_content,
            name="originalincidentfield",
            marketplaces=[MarketplaceVersions.MarketplaceV2],
        )
    )
    pack2.content_items.incident_field.append(
        mock_incident_field(
            cli_name="alias1incidentfield",
            path=alias1_incident_field.path,
            data=alias1_incident_field_content,
            name="alias1incidentfield",
            marketplaces=[MarketplaceVersions.MarketplaceV2, MarketplaceVersions.XSOAR],
        )
    )
    pack2.content_items.incident_field.append(
        mock_incident_field(
            cli_name="alias2incidentfield",
            path=alias2_incident_field.path,
            data=alias2_incident_field_content,
            name="alias2incidentfield",
            marketplaces=[MarketplaceVersions.XSOAR],
        )
    )
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


def test_format_mapper_with_graph_remove_unknown_content(
    mocker, monkeypatch, repository, repo
):
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
    mocker.patch(
        "demisto_sdk.commands.format.format_module.update_content_graph",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(
            main, [FORMAT_CMD, "-i", mapper_path, "-at", "-y", "-nv"]
        )
    message = (
        "Removing the fields {'Unknown Incident Field'}"
        + f" from the mapper {mapper_path} "
        f"because they aren't in the content repo."
    )
    assert result.exit_code == 0
    assert not result.exception
    assert str_in_call_args_list(logger_info.call_args_list, message)

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(mapper_path)[0]
    assert (
        file_content.get("mapping", {}).get("Mapper Finding", {}).get("internalMapping")
        == {}
    )


def test_format_layout_with_graph_remove_unknown_content(
    mocker, monkeypatch, repository, repo
):
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
    mocker.patch(
        "demisto_sdk.commands.format.format_module.update_content_graph",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(
            main, [FORMAT_CMD, "-i", layout_path, "-at", "-y", "-nv"]
        )
    message = (
        "Removing the fields {'Unknown Incident Field'}"
        + f" from the layout {layout_path} "
        f"because they aren't in the content repo."
    )
    assert result.exit_code == 0
    assert not result.exception
    assert str_in_call_args_list(logger_info.call_args_list, message)

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    file_content = get_dict_from_file(layout_path)[0]
    expected_layout_content = [
        {
            "endCol": 2,
            "fieldId": "incidentfield",
            "height": 22,
            "id": "id2",
            "index": 0,
            "sectionItemType": "field",
            "startCol": 0,
        }
    ]
    assert (
        file_content.get("detailsV2", {})
        .get("tabs", [])[0]
        .get("sections", {})[0]
        .get("items", [])
        == expected_layout_content
    )


def test_format_incident_field_graph_fix_aliases_marketplace(
    mocker, monkeypatch, repository, repo
):
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
    original_incident_field_path = str(
        pack_graph_object.content_items.incident_field[0].path
    )  # original incident field
    alias1_incident_field_path = str(
        pack_graph_object.content_items.incident_field[1].path
    )
    alias2_incident_field_path = str(
        pack_graph_object.content_items.incident_field[2].path
    )
    mocker.patch(
        "demisto_sdk.commands.format.format_module.ContentGraphInterface",
        return_value=interface,
    )
    mocker.patch(
        "demisto_sdk.commands.format.format_module.update_content_graph",
        return_value=interface,
    )
    with ChangeCWD(repo.path):
        runner = CliRunner()
        result = runner.invoke(
            main, [FORMAT_CMD, "-i", original_incident_field_path, "-at", "-y", "-nv"]
        )

    assert result.exit_code == 0
    assert not result.exception

    # get_dict_from_file returns a tuple of 2 object. The first is the content of the file,
    # the second is the type of the file.
    alias1_content = get_dict_from_file(alias1_incident_field_path)[0]
    alias2_content = get_dict_from_file(alias2_incident_field_path)[0]
    assert alias1_content.get("marketplaces", []) == ["xsoar"]
    assert alias2_content.get("marketplaces", []) == ["xsoar"]

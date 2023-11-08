from pathlib import Path
from typing import Callable, List

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.tests.graph_validator_test import mock_pack
from demisto_sdk.commands.validate.validators.GR_validators.GR106_duplicated_script_name import (
    DuplicatedScriptNameValidator,
)

GIT_PATH = Path(git_path())


# FIXTURES


@pytest.fixture(autouse=True)
def setup_method(mocker):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = GIT_PATH
    mocker.patch.object(neo4j_service, "REPO_PATH", GIT_PATH)
    mocker.patch.object(ContentGraphInterface, "repo_path", GIT_PATH)
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


@pytest.fixture
def repository(mocker) -> ContentDTO:
    repository = ContentDTO(
        path=GIT_PATH,
        packs=[],
    )
    pack1 = mock_pack(
        "SamplePack", [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2]
    )
    pack1.content_items.script.append(
        mock_script(
            "test_alert1",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_incident1",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_alert2", pack_name="pack1", marketplaces=[MarketplaceVersions.XSOAR]
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_incident2",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.XSOAR],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_alert3",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.MarketplaceV2],
            skip_prepare=[SKIP_PREPARE_SCRIPT_NAME],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_incident3",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.MarketplaceV2],
            skip_prepare=[SKIP_PREPARE_SCRIPT_NAME],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_alert4", pack_name="pack1", marketplaces=[MarketplaceVersions.XSOAR]
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "test_incident4",
            pack_name="pack1",
            marketplaces=[MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        )
    )

    repository.packs.extend([pack1])
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        return_value=[repository],
    )
    return repository


def update_repository(
    repository: ContentDTO,
    commit_func: Callable[[ContentDTO], List[Pack]],
) -> List[str]:
    updated_packs = commit_func(repository)
    pack_ids_to_update = [pack.object_id for pack in updated_packs]
    repository.packs = [
        pack for pack in repository.packs if pack.object_id not in pack_ids_to_update
    ]
    repository.packs.extend(updated_packs)
    return pack_ids_to_update


def mock_script(
    name,
    marketplaces=[MarketplaceVersions.XSOAR],
    skip_prepare=[],
    pack_name="pack_name",
):
    return Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=Path(f"Packs/{pack_name}/Scripts/{name}.yml"),
        fromversion="5.0.0",
        display_name=name,
        toversion="6.0.0",
        name=name,
        marketplaces=marketplaces,
        deprecated=False,
        type="python3",
        docker_image="demisto/python3:3.10.11.54799",
        tags=[],
        is_test=False,
        skip_prepare=skip_prepare,
    )


def test_validate_unique_script_name(repository: ContentDTO, mocker):
    """
    Given
        - A content repo with 8 scripts:
        - 2 scripts (test_alert1, test_incident1) supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert2, test_incident2) not supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert3, test_incident3) supported by MP V2 with SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert4, test_incident4) where only one is supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
    When
        - running DuplicatedScriptNameValidator is_valid function.
    Then
        - Validate that only the first pair of scripts appear in the results, and teh rest of the scripts is valid.
    """
    scripts = []
    for pack in repository.packs:
        scripts.extend(pack.content_items.script)
    create_content_graph(ContentGraphInterface())
    results = DuplicatedScriptNameValidator().is_valid(scripts)

    assert len(results) == 1
    assert str(results[0].content_object.path) == "Packs/pack1/Scripts/test_alert1.yml"

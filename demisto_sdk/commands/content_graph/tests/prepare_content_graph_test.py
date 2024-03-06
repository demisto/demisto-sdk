from pathlib import Path

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_pack,
    mock_playbook,
    mock_relationship,
    mock_script,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)
from TestSuite.repo import Repo

GIT_ROOT = git_path()


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


def create_mini_content(repository: ContentDTO):
    relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "TestPack",
                ContentType.PACK,
            )
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "getIncident",
                ContentType.SCRIPT,
                mandatorily=True,
            ),
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "setIncidentByID",
                ContentType.SCRIPT,
                mandatorily=True,
            ),
        ],
    }
    relationships2 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "setIncidentByID",
                ContentType.PLAYBOOK,
                "TestPack2",
                ContentType.PACK,
            ),
            mock_relationship(
                "getIncident",
                ContentType.PLAYBOOK,
                "TestPack2",
                ContentType.PACK,
            ),
        ]
    }
    pack1 = mock_pack("TestPack")
    pack2 = mock_pack("TestPack2")
    pack1.relationships = relationships
    pack2.relationships = relationships2
    pack1.content_items.playbook.append(
        mock_playbook(
            name="playbook_1",
        )
    )
    pack2.content_items.script.append(
        mock_script(
            "getIncident",
            skip_prepare=[SKIP_PREPARE_SCRIPT_NAME],
        )
    )
    pack2.content_items.script.append(
        mock_script(
            "setIncidentByID",
        )
    )
    repository.packs.extend([pack1, pack2])


def test_marketplace_version_is_xsiam_with_graph(repository: ContentDTO):
    """
    Given:
        - A playbook which contains scripts that names include incident/s.
        - One script is set as `skipprepare` and a second script is not set as skip.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed

    Then:
        - Ensure that only a script that is not set as skip has changed from incident to alert.
    """
    create_mini_content(repository)
    with ContentGraphInterface() as interface:
        create_content_graph(interface)
        playbooks = interface.search(content_type=ContentType.PLAYBOOK)
        data = get_yaml(
            f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_2.yml"
        )

        data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            playbook=playbooks[0],
            data=data,
            current_marketplace=MarketplaceVersions.MarketplaceV2,
            supported_marketplaces=[
                MarketplaceVersions.XSOAR,
                MarketplaceVersions.MarketplaceV2,
            ],
        )

    assert data["tasks"]["6"]["task"]["scriptName"] == "getIncident"
    assert data["tasks"]["7"]["task"]["scriptName"] == "setAlertByID"

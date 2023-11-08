import logging
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    GENERAL_DEFAULT_FROMVERSION,
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_relationship,
    mock_test_playbook,
)
from demisto_sdk.commands.validate.tests.test_tools import create_script_object
from demisto_sdk.commands.validate.validators.GR_validators.GR106_duplicated_script_name import (
    DuplicatedScriptNameValidator,
)
from TestSuite.test_tools import str_in_call_args_list

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
    relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SamplePack",
                ContentType.PACK,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            ),
            mock_relationship(
                "SampleScript",
                ContentType.SCRIPT,
                "SamplePack",
                ContentType.PACK,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            ),
        ],
        RelationshipType.HAS_COMMAND: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "test-command",
                ContentType.COMMAND,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
                name="test-command",
                description="",
                deprecated=False,
            ),
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "deprecated-command",
                ContentType.COMMAND,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
                name="deprecated-command",
                description="",
                deprecated=True,
            ),
        ],
        RelationshipType.IMPORTS: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "TestApiModule",
                ContentType.SCRIPT,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            )
        ],
        RelationshipType.TESTED_BY: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SampleTestPlaybook",
                ContentType.TEST_PLAYBOOK,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            )
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SampleClassifier",
                ContentType.CLASSIFIER,
                mandatorily=True,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            ),
            mock_relationship(
                "SampleIntegration",
                ContentType.INTEGRATION,
                "SampleClassifier2",
                ContentType.CLASSIFIER,
                mandatorily=True,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            ),
        ],
        RelationshipType.DEPENDS_ON: [
            mock_relationship(
                "SamplePack",
                ContentType.PACK,
                "SamplePack2",
                ContentType.PACK,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.MarketplaceV2,
                ],
            ),
        ],
        RelationshipType.USES: [
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "DeprecatedIntegration",
                ContentType.INTEGRATION,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.XPANSE,
                ],
                source_fromversion="6.5.0",
            ),
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "deprecated-command",
                ContentType.COMMAND,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.XPANSE,
                ],
                source_fromversion="6.5.0",
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
                "TestApiModule",
                ContentType.SCRIPT,
                "SamplePack2",
                ContentType.PACK,
                source_marketplaces=[MarketplaceVersions.XSOAR],
            ),
            mock_relationship(
                "SampleClassifier2",
                ContentType.CLASSIFIER,
                "SamplePack2",
                ContentType.PACK,
            ),
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "TestApiModule",
                ContentType.SCRIPT,
                "SampleScript2",
                ContentType.SCRIPT,
                mandatorily=True,
                source_marketplaces=[MarketplaceVersions.XSOAR],
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
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.XPANSE,
                ],
                source_fromversion="6.5.0",
            ),
            mock_relationship(
                "SamplePlaybook2",
                ContentType.PLAYBOOK,
                "SamplePack3",
                ContentType.PACK,
                source_fromversion=GENERAL_DEFAULT_FROMVERSION,
            ),
            mock_relationship(
                "SampleScript2",
                ContentType.SCRIPT,
                "SamplePack3",
                ContentType.PACK,
            ),
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "SamplePlaybook2",
                ContentType.PLAYBOOK,
                mandatorily=True,
                source_marketplaces=[
                    MarketplaceVersions.XSOAR,
                    MarketplaceVersions.XPANSE,
                ],
                source_fromversion="6.5.0",
            ),
        ],
    }
    relationship_pack4 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SamplePlaybook", ContentType.PLAYBOOK, "SamplePack4", ContentType.PACK
            )
        ]
    }
    pack1 = mock_pack(
        "SamplePack", [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2]
    )
    pack2 = mock_pack("SamplePack2", [MarketplaceVersions.XSOAR], hidden=True)
    pack3 = mock_pack(
        "SamplePack3",
        [
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
        ],
    )
    pack4 = mock_pack("SamplePack4", list(MarketplaceVersions))
    pack1.relationships = relationships
    pack2.relationships = relationship_pack2
    pack3.relationships = relationship_pack3
    pack4.relationships = relationship_pack4
    pack1.content_items.integration.append(mock_integration())
    pack1.content_items.integration.append(
        mock_integration(name="DeprecatedIntegration", deprecated=True)
    )
    pack1.content_items.script.append(
        mock_script(
            "SampleScript",
            [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        )
    )
    pack1.content_items.script.append(
        mock_script(
            "setIncident",
            [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        )
    )
    pack2.content_items.script.append(mock_script("TestApiModule"))
    pack2.content_items.script.append(
        mock_script(
            "getIncidents",
            marketplaces=[MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
            skip_prepare=[SKIP_PREPARE_SCRIPT_NAME],
        )
    )
    pack2.content_items.classifier.append(mock_classifier("SampleClassifier2"))
    pack2.content_items.test_playbook.append(mock_test_playbook())
    pack3.content_items.playbook.append(
        mock_playbook(
            "SamplePlaybook",
            [MarketplaceVersions.XSOAR, MarketplaceVersions.XPANSE],
            "6.5.0",
            GENERAL_DEFAULT_FROMVERSION,
        )
    )
    pack3.content_items.playbook.append(
        mock_playbook(
            "SamplePlaybook2",
            [MarketplaceVersions.XSOAR],
            GENERAL_DEFAULT_FROMVERSION,
            "6.5.0",
        )
    )
    pack3.content_items.script.append(mock_script("SampleScript2"))
    pack3.content_items.script.append(
        mock_script(
            "setAlert", [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2]
        )
    )
    pack3.content_items.script.append(
        mock_script(
            "getAlert", [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2]
        )
    )
    pack3.content_items.script.append(
        mock_script(
            "getAlerts", [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2]
        )
    )
    pack4.content_items.playbook.append(mock_playbook("SamplePlaybook"))
    repository.packs.extend([pack1, pack2, pack3, pack4])
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dtos",
        return_value=[repository],
    )
    return repository


# HELPERS


def mock_dependency(source: str, target: str, mandatory: bool = True) -> Dict[str, Any]:
    return {
        "source_id": source,
        "source_type": ContentType.PACK,
        "target": target,
        "target_type": ContentType.PACK,
        "mandatorily": mandatory,
    }


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


def _get_pack_by_id(repository: ContentDTO, pack_id: str) -> Pack:
    for pack in repository.packs:
        if pack.object_id == pack_id:
            return pack
    raise ValueError(f"Pack {pack_id} does not exist in the repository.")


def mock_pack(name, marketplaces, hidden=False):
    return Pack(
        object_id=name,
        content_type=ContentType.PACK,
        node_id=f"{ContentType.PACK}:{name}",
        path=Path("Packs"),
        name="pack_name",
        marketplaces=marketplaces,
        hidden=hidden,
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


def mock_playbook(
    name,
    marketplaces=[MarketplaceVersions.XSOAR],
    fromversion="5.0.0",
    toversion="99.99.99",
):
    return Playbook(
        id=name,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{name}",
        path=Path(name),
        fromversion=fromversion,
        toversion=toversion,
        display_name=name,
        name=name,
        marketplaces=marketplaces,
        deprecated=False,
        is_test=False,
    )


def mock_script(name, marketplaces=[MarketplaceVersions.XSOAR], skip_prepare=[]):
    return Script(
        id=name,
        content_type=ContentType.SCRIPT,
        node_id=f"{ContentType.SCRIPT}:{name}",
        path=Path("Packs"),
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


def mock_integration(name: str = "SampleIntegration", deprecated: bool = False):
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=Path(name),
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=name,
        name=name,
        marketplaces=[MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2],
        deprecated=deprecated,
        type="python3",
        docker_image="demisto/python3:3.10.11.54799",
        category="blabla",
        commands=[
            Command(name="test-command", description=""),
            Command(name="deprecated-command", description=""),
        ],
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


def test_validate_unique_script_name(repository: ContentDTO, mocker):
    """
    Given
        - A content repo
    When
        - running the validation "validate_unique_script_name"
    Then
        - Validate the existence of duplicate script names
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    scripts = []
    for pack in repository.packs:
        scripts.extend(pack.content_items.script)
    results = DuplicatedScriptNameValidator().is_valid(scripts)
    
    
    # with GraphValidator(update_graph=False) as graph_validator:
    #     create_content_graph(graph_validator.graph)
    #     is_valid = graph_validator.validate_unique_script_name()

    assert not len(results)

    assert str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name setAlert, "
        "because a script with the name setIncident already exists.\n",
    )

    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name getAlert, "
        "because a script with the name getIncident already exists.\n",
    )

    # Ensure that the script-name-incident-to-alert ignore is working
    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name getAlerts, "
        "because a script with the name getIncidents already exists.\n",
    )

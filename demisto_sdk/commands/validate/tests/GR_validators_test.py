import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    GENERAL_DEFAULT_FROMVERSION,
    SKIP_PREPARE_SCRIPT_NAME,
)
from demisto_sdk.commands.content_graph.commands.create import create_content_graph
from demisto_sdk.commands.content_graph.common import RelationshipType
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_relationship,
    mock_test_playbook,
)
from demisto_sdk.commands.validate.tests.graph_test_tools import *
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.GR_validators import (
    GR104_is_pack_display_name_already_exists,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place import (
    MarketplacesFieldValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place_all_files import (
    MarketplacesFieldValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_all_files import (
    IsPackDisplayNameAlreadyExistsValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_list_files import (
    IsPackDisplayNameAlreadyExistsValidatorListFiles,
)
from TestSuite.repo import Repo


def test_IsPackDisplayNameAlreadyExistsValidatorListFiles_is_valid(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorListFiles is_valid function, on one of the duplicate packs.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    mocker.patch.object(
        GR104_is_pack_display_name_already_exists,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    graph_repo.create_pack(name="pack1")

    graph_repo.create_pack(name="pack2")
    graph_repo.packs[1].pack_metadata.update(
        {
            "name": "pack1",
        }
    )

    graph_repo.create_pack(name="pack3")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsPackDisplayNameAlreadyExistsValidatorListFiles().is_valid(
        [graph_repo.packs[0], graph_repo.packs[2]]
    )

    assert len(results) == 1
    assert results[0].message == "Pack 'pack1' has a duplicate display_name as: pack2."


def test_IsPackDisplayNameAlreadyExistsValidatorAllFiles_is_valid(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorAllFiles is_valid function.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    mocker.patch.object(
        GR104_is_pack_display_name_already_exists,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    graph_repo.create_pack(name="pack1")

    graph_repo.create_pack(name="pack2")
    graph_repo.packs[1].pack_metadata.update(
        {
            "name": "pack1",
        }
    )

    graph_repo.create_pack(name="pack3")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsPackDisplayNameAlreadyExistsValidatorAllFiles().is_valid(
        [pack for pack in graph_repo.packs]
    )

    assert len(results) == 2


@pytest.fixture
def setup(mocker, tmp_path_factory):
    """Setup mocks for graph validators' tests"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc
    from demisto_sdk.commands.common.files.file import File

    bc.CONTENT_PATH = GIT_PATH
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", GIT_PATH)
    mocker.patch.object(ContentGraphInterface, "export_graph", return_value=None)
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
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


@pytest.mark.usefixtures("setup")
def test_MarketplacesFieldValidator_is_valid(repository):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidator is_valid() function.
    Then
    - Validate the existence of invalid marketplaces usages.
    - A single invalid content items shall be found, with expected error message listed in
        `expected_validation_results_messages`.
    """

    graph_interface = ContentGraphInterface()
    create_content_graph(graph_interface)
    BaseValidator.graph_interface = graph_interface

    expected_validation_results_messages = {
        "Content item 'SampleIntegration' can be used in the 'xsoar, marketplacev2' marketplaces, however it uses "
        "content items: 'SampleClassifier2' which are not supported in all of the marketplaces of 'SampleIntegration'.",
    }
    # T
    packs_to_validate = repository.packs[:2]
    validation_results = MarketplacesFieldValidator().is_valid(packs_to_validate)
    assert len(validation_results) == len(expected_validation_results_messages)
    for validation_result in validation_results:
        assert validation_result.message in expected_validation_results_messages


@pytest.mark.usefixtures("setup")
def test_MarketplacesFieldValidatorAllFiles_is_valid(repository):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidatorAllFiles is_valid() function.
    Then
    - Validate the validator ignores the provided specific packs and validates all content items in the content graph.
    - Validate the existence of invalid marketplaces usages.
    - Two invalid content items shall be found, with expected error message listed in
        `expected_validation_results_messages`.
    """
    graph_interface = ContentGraphInterface()
    create_content_graph(graph_interface)
    BaseValidator.graph_interface = graph_interface

    expected_validation_results_messages = {
        "Content item 'SamplePlaybook' can be used in the 'xsoar, xpanse' marketplaces, however it uses content items: "
        "'SamplePlaybook2' which are not supported in all of the marketplaces of 'SamplePlaybook'.",
        "Content item 'SampleIntegration' can be used in the 'xsoar, marketplacev2' marketplaces, however it uses "
        "content items: 'SampleClassifier2' which are not supported in all of the marketplaces of 'SampleIntegration'.",
    }
    packs_to_validate = repository.packs[:2]
    validation_results = MarketplacesFieldValidatorAllFiles().is_valid(
        packs_to_validate
    )
    assert len(validation_results) == len(expected_validation_results_messages)
    for validation_result in validation_results:
        assert validation_result.message in expected_validation_results_messages

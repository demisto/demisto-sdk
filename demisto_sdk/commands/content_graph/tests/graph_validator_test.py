import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import (
    GENERAL_DEFAULT_FROMVERSION,
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.graph_validator import GraphValidator
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
from TestSuite.test_tools import str_in_call_args_list

GIT_PATH = Path(git_path())


# FIXTURES


@pytest.fixture(autouse=True)
def setup_method(mocker, tmp_path_factory):
    """Auto-used fixture for setup before every test run"""
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
        display_name="pack_name",
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
        docker_image=DockerImage("demisto/python3:3.10.11.54799"),
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
        docker_image=DockerImage("demisto/python3:3.10.11.54799"),
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


# TESTS


def test_are_toversion_relationships_paths_valid(repository: ContentDTO):
    """
    Given
    - A content repo
    When
    - running the validation "are_toversion_relationships_paths_valid"
    Then
    - Validate the existance of invalid to_version relationships
    """

    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_toversion_fields()

    assert not is_valid


def test_are_fromversion_relationships_paths_valid(repository: ContentDTO, mocker):
    """
    Given
    - A content repo
    When
    - running the vaidation "are_fromversion_relationships_paths_valid"
    Then
    - Validate the existance of invalid from_version relationships
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_fromversion_fields()

    assert not is_valid
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "Content item 'SamplePlaybook' whose from_version is '6.5.0' uses the content"
        " items: 'SamplePlaybook2' whose from_version is higher",
    )


@pytest.mark.parametrize(
    "include_optional, is_valid",
    [
        pytest.param(
            False,
            True,
            id="Not providing git_files - should be valid (raised a warning)",
        ),
        pytest.param(
            True,
            False,
            id="providing git_files - should be invalid",
        ),
    ],
)
def test_is_file_using_unknown_content(
    mocker,
    repository: ContentDTO,
    include_optional: bool,
    is_valid: bool,
):
    """
    Given
    - A content repo
    - An integration SampleIntegration's default classifier is set to "SampleClassifier" which does not exist
    When
    - running the vaidation "is_file_using_unknown_content"
    Then
    - Check whether the graph is valid or not, based on whether optional content dependencies were included.
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    with GraphValidator(
        update_graph=False, git_files=[], include_optional_deps=include_optional
    ) as graph_validator:
        create_content_graph(graph_validator.graph)
        assert graph_validator.is_file_using_unknown_content() == is_valid

    logger_to_search = logger_warning if is_valid else logger_error

    assert str_in_call_args_list(
        logger_to_search.call_args_list,
        "Content item 'SampleIntegration' using content items: 'SampleClassifier' which"
        " cannot be found in the repository",
    )


def test_is_file_display_name_already_exists(repository: ContentDTO, mocker):
    """
    Given
    - A content repo
    When
    - running the vaidation "is_file_display_name_already_exists"
    Then
    - Validate the existance of duplicate display names
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.is_file_display_name_already_exists()

    assert not is_valid
    for i in range(1, 4):
        assert str_in_call_args_list(
            logger_error.call_args_list,
            f"Pack 'SamplePack{i if i != 1 else ''}' has a duplicate display_name",
        )


def test_validate_unique_script_name(repository: ContentDTO, mocker):
    """
    Given
        - A content repo
    When
        - running the vaidation "validate_unique_script_name"
    Then
        - Validate the existance of duplicate script names
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_unique_script_name()

    assert not is_valid

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


def test_are_marketplaces_relationships_paths_valid(
    repository: ContentDTO, caplog, mocker
):
    """
    Given
    - A content repo
    When
    - running the validation "is_file_display_name_already_exists"
    Then
    - Validate the existence invalid marketplaces uses
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_marketplaces_fields()

    assert not is_valid
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "Content item 'SamplePlaybook' can be used in the 'xsoar, xpanse' marketplaces"
        ", however it uses content items: 'SamplePlaybook2' which are not supported in"
        " all of the marketplaces of 'SamplePlaybook'",
    )


def test_validate_dependencies(repository: ContentDTO, caplog, mocker):
    """
    Given
    - A content repo
    When
    - running the vaidation "validate_dependencies"
    Then
    - Validate the existance invalid core pack dependency
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.graph_validator.get_marketplace_to_core_packs",
        return_value={MarketplaceVersions.XSOAR: {"SamplePack"}},
    )
    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_dependencies()

    assert not is_valid
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "The core pack SamplePack cannot depend on non-core packs: ",
    )


def test_validate_duplicate_id(repository: ContentDTO, mocker):
    """
    Given
    - A content repo with duplicate ids "SamplePlaybook" (configured on repository fixture)
    When
    - running the validation "validate_duplicate_id"
    Then
    - Validate the existence of duplicate ids
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

    with GraphValidator(update_graph=False) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = graph_validator.validate_duplicate_ids()

    assert not is_valid
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "[GR105] - The ID 'SamplePlaybook' already exists in",
    )


def test_pack_ids_collection():
    git_files = [
        "Tests/conf.json",
        "Packs/MicrosoftExchangeOnline/Integrations/EwsExtension/README.md",
    ]
    expected_pack_ids = ["MicrosoftExchangeOnline"]
    with GraphValidator(update_graph=False, git_files=git_files) as graph_validator:
        assert graph_validator.pack_ids == expected_pack_ids


def test_deprecated_usage__existing_content(repository: ContentDTO, mocker):
    """
    Given
    - A content repo with item using deprecated commands in existing content.
    When
    - running the validation validate_deprecated_items_usage
    Then
    - validate warning is display but it's considered as valid
    """

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    with GraphValidator(update_graph=False) as validator:
        create_content_graph(validator.graph)
        is_valid = validator.validate_deprecated_items_usage()

    assert is_valid
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "[GR107] - The Command 'deprecated-command' is deprecated but used in the following content item:",
    )
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "[GR107] - The Integration 'DeprecatedIntegration' is deprecated but used in the following content item:",
    )


def test_deprecated_usage__new_content(repository: ContentDTO, mocker):
    """
    Given
    - A content repo with the new item "SamplePlaybook" using a deprecated command.
    When
    - running the validation validate_deprecated_items_usage
    Then
    - validate the files considered as invalid.
    """
    mocker.patch.object(GitUtil, "added_files", return_value=[Path("SamplePlaybook")])
    with GraphValidator(update_graph=False) as validator:
        create_content_graph(validator.graph)
        is_valid = validator.validate_deprecated_items_usage()

    assert not is_valid


@pytest.mark.parametrize(
    "changed_pack", ["Packs/SamplePack", "Packs/SamplePack2", None]
)
def test_validate_hidden_pack_is_not_mandatory_dependency(
    repository: ContentDTO, mocker, changed_pack: Optional[str]
):
    """
    Given
    - A content repo which contains SamplePack that is dependent on
      SamplePack2 (which is hidden) as mandatory dependency

    When
    - Case A: the changed file was the hidden pack.
    - Case B: the changed file was the hidden pack's mandatory dependency
    - Case C: validate all triggered (no git files were sent)

    Then
    - validate that an error occurs with a message stating that SamplePack2 is hidden and has mandatory dependencies
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

    git_files = [Path(changed_pack)] if changed_pack else changed_pack

    with GraphValidator(update_graph=False, git_files=git_files) as graph_validator:
        create_content_graph(graph_validator.graph)
        is_valid = (
            graph_validator.validate_hidden_packs_do_not_have_mandatory_dependencies()
        )

    assert not is_valid
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "[GR108] - SamplePack pack(s) cannot have a mandatory dependency on the hidden pack SamplePack2",
    )

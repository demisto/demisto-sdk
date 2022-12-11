from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.content_graph_commands import create_content_graph, stop_content_graph, update_content_graph
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    find_model_for_id, mock_classifier, mock_integration, mock_pack, mock_playbook,
    mock_relationship, mock_script, mock_test_playbook)
from demisto_sdk.commands.common.legacy_git_tools import git_path


GIT_PATH = Path(git_path())


@pytest.fixture(autouse=True)
def setup(mocker):
    """Auto-used fixture for setup before every test run"""
    mocker.patch.object(neo4j_service, "REPO_PATH", GIT_PATH)
    mocker.patch.object(ContentGraphInterface, "repo_path", GIT_PATH)


@pytest.fixture
def repository(mocker) -> ContentDTO:
    repository = ContentDTO(
        path=Path(),
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
            mock_relationship("TestApiModule", ContentType.SCRIPT, "SamplePack2", ContentType.PACK),
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "TestApiModule", ContentType.SCRIPT, "SampleScript2", ContentType.SCRIPT, mandatorily=True
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
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


# HELPERS


def compare_content_items(
    content_items_list_a: List[ContentItem],
    content_items_list_b: List[ContentItem]
) -> None:
    assert len(content_items_list_a) == len(content_items_list_b)
    for ci_a, ci_b in zip(content_items_list_a, content_items_list_b):
        assert ci_a.dict() == ci_b.dict()


def compare_relationships(pack_a: Pack, pack_b: Pack) -> None:
    for relationship_type, relationships in pack_a.relationships.items():
        for relationship in relationships:
            content_item_source = find_model_for_id([pack_b], relationship.get("source_id"))
            content_item_target_id = relationship.get("target")
            assert content_item_source
            assert content_item_target_id
            if relationship_type == RelationshipType.IN_PACK:
                assert content_item_source.in_pack.object_id == content_item_target_id
            if relationship_type == RelationshipType.IMPORTS:
                assert content_item_source.imports[0].object_id == content_item_target_id
            if relationship_type == RelationshipType.USES_BY_ID:
                assert content_item_source.uses[0].content_item.object_id == content_item_target_id
            if relationship_type == RelationshipType.TESTED_BY:
                assert content_item_source.tested_by[0].object_id == content_item_target_id


def compare(packs_list_a: List[Pack], packs_list_b: List[Pack]) -> None:
    packs_list_a.sort(key=lambda pack: pack.object_id)
    packs_list_b.sort(key=lambda pack: pack.object_id)
    assert len(packs_list_a) == len(packs_list_b)
    for pack_a, pack_b in zip(packs_list_a, packs_list_b):
        assert pack_a.dict() == pack_b.dict()
        compare_content_items(list(pack_a.content_items), list(pack_b.content_items))
        compare_relationships(pack_a, pack_b)


def _get_pack_by_id(repository: ContentDTO, pack_id: str) -> Optional[Pack]:
    for pack in repository.packs:
        if pack.object_id == pack_id:
            return pack
    return None


def verify_dependencies_existence(
    packs: List[Pack],
    dependencies: List[Dict[str, Any]],
    should_exist: bool,
) -> None:
    for dependency in dependencies:
        for pack in packs:
            if pack.object_id == dependency["source_id"]:
                if should_exist:
                    assert any(r.target.object_id == dependency["target"] for r in pack.depends_on)
                else:
                    assert all(r.target.object_id != dependency["target"] for r in pack.depends_on)
                break
        else:
            assert False


# Test cases (commit functions)


def _testcase1__pack3_pack4__script2_uses_script4(
    repository: ContentDTO,
) -> Tuple[
    List[Pack],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """Test case for the following updates:
    * New pack: SamplePack4, with a script: SampleScript4
    * New relationship: SampleScript2 (of existing pack SamplePack3) USES SampleScript4 (of new pack SamplePack4)
    
    Returns:
        1. A list of the updated packs: pack3, pack4.
        2. New mandatory dependency: pack3->pack4.
    """
    pack4_relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "SampleScript4",
                ContentType.SCRIPT,
                "SamplePack4",
                ContentType.PACK,
            )
        ],
    }
    pack4 = mock_pack("SamplePack4")
    pack4.relationships = pack4_relationships
    pack4.content_items.script.append(mock_script("SampleScript4"))

    pack3 = _get_pack_by_id(repository, "SamplePack3")
    assert pack3
    pack3.relationships.setdefault(RelationshipType.USES_BY_ID, []).append(
        mock_relationship(
            "SampleScript2",
            ContentType.SCRIPT,
            "SampleScript4",
            ContentType.SCRIPT,
        )
    )

    updated_packs = [pack3, pack4]
    added_dependencies = [mock_relationship(
        "SamplePack3",
        ContentType.PACK,
        "SamplePack4",
        ContentType.PACK,
    )]
    return updated_packs, added_dependencies, []


def _testcase2__pack3__remove_relationship(
    repository: ContentDTO,
) -> Tuple[
    List[Pack],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """Test case for the following update:
    * Remove relationship: TestApiModule (of pack SamplePack2) USES SampleScript2 (of pack SamplePack3)

    Returns:
        1. A list of the updated pack: pack2.
        2. Removed mandatory dependency: pack2->pack3.
    """
    pack2 = _get_pack_by_id(repository, "SamplePack2")
    assert pack2
    uses_relationships = pack2.relationships.get(RelationshipType.USES_BY_ID, [])
    for rel in uses_relationships:
        if rel["source_id"] == "TestApiModule" and rel["target"] == "SampleScript2":
            uses_relationships.remove(rel)
            break

    updated_packs = [pack2]
    removed_dependencies = [mock_relationship(
        "SamplePack2",
        ContentType.PACK,
        "SamplePack3",
        ContentType.PACK,
    )]
    return updated_packs, [], removed_dependencies


class TestUpdateContentGraph:
    @pytest.mark.parametrize(
        "commit_func, start_service, stop_service",
        [
            (_testcase1__pack3_pack4__script2_uses_script4, True, False),
            (_testcase2__pack3__remove_relationship, False, True),
        ]
    )
    def test_update_content_graph(
        self,
        repository: ContentDTO,
        commit_func: Callable[
            [ContentDTO],
            Tuple[List[Pack], List[Dict[str, Any]], List[Dict[str, Any]]]
        ],
        start_service: bool,
        stop_service: bool,
    ):
        """
        Given:
            - A ContentDTO model representing the repository state on master branch.
            - A function representing a commit (an update of certain packs in the repository).
              This function returns:
              1. A list of the updated packs
              2. A list of the expected added dependencies due to the update.
              3. A list of the expected removed dependencies due to the update.
        When:
            - Running create_content_graph() on master.
            - Pushing a commit with the pack updates.
            - Running update_content_graph().
        Then:
            - Make sure the pack models from the interface are equal to the pack models from ContentDTO
                before and after the update.
            - Make sure the expected added dependencies actually don't exist before the update
                and exist after the update.
            - Make sure the expected removed dependencies actually exist before the update
                and don't exist after the update.

        """
        with ContentGraphInterface(start_service=start_service) as interface:
            create_content_graph(interface, export=True, dependencies=True)
            packs = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )
            compare(repository.packs, packs)

            updated_packs, added_dependencies, removed_dependencies = commit_func(repository)
            verify_dependencies_existence(packs, added_dependencies, should_exist=False)
            verify_dependencies_existence(packs, removed_dependencies, should_exist=True)

            pack_ids_to_update = [pack.object_id for pack in updated_packs]
            all_packs = [pack for pack in repository.packs if pack.object_id not in pack_ids_to_update] + updated_packs
            repository.packs = updated_packs

            update_content_graph(interface, packs_to_update=pack_ids_to_update, dependencies=True)
            packs = interface.search(
                marketplace=MarketplaceVersions.XSOAR,
                content_type=ContentType.PACK,
                all_level_dependencies=True,
            )
            compare(all_packs, packs)
            verify_dependencies_existence(packs, added_dependencies, should_exist=True)
            verify_dependencies_existence(packs, removed_dependencies, should_exist=False)
        if stop_service:
            stop_content_graph()

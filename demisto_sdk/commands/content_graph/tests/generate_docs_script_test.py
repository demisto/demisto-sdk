from pathlib import Path
from typing import List

import pytest

from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.content_graph import neo4j_service
from demisto_sdk.commands.content_graph.common import RelationshipType, ContentType
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import mock_relationship, mock_pack, \
    mock_script, mock_playbook
from demisto_sdk.commands.content_graph.commands.create import create_content_graph
from demisto_sdk.commands.content_graph.tests.update_content_graph_test import _get_pack_by_id
from demisto_sdk.commands.generate_docs.generate_script_doc import generate_script_doc

GIT_PATH = Path(git_path())


# FIXTURES


@pytest.fixture(autouse=True)
def setup_method(mocker, repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(neo4j_service, "REPO_PATH", Path(repo.path))
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))
    neo4j_service.stop()


@pytest.fixture
def repository(mocker, repo) -> ContentDTO:
    repository = ContentDTO(
        path=GIT_PATH,
        packs=[],
    )
    relationships = {
        RelationshipType.USES: [
            mock_relationship(
                "SampleScript",
                ContentType.SCRIPT,
                "UsesScript",
                ContentType.SCRIPT
            ),
            mock_relationship(
                "SamplePlaybook",
                ContentType.PLAYBOOK,
                "SampleScript",
                ContentType.SCRIPT
            )
        ]
    }

    repo_pack = repo.create_pack()
    script = repo_pack.create_script(name="SampleScript")

    pack = mock_pack()
    pack.relationships = relationships
    pack.content_items.script.append(mock_script(name="SampleScript", path=script.path))
    pack.content_items.script.append(mock_script("UsesScript"))
    pack.content_items.playbook.append(mock_playbook("SamplePlaybook"))
    repository.packs.extend([pack])

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


def test_generate_script_doc_passes_markdown_lint_graph(mocker, repository, tmp_path):
    """
        Given
        - A script (SampleScript) that uses another script (UsesScript)and is used by a playbook (SamplePlaybook).
        When
        - Running generate-docs command on the script.
        Then
        -  The generated readme will have no markdown errors
    """
    with ContentGraphInterface() as interface:
        create_content_graph(interface)

    pack_graph_object = _get_pack_by_id(repository, "SamplePack")
    input_script_object = pack_graph_object.content_items.script[0]  # SampleScript
    output_dir = tmp_path / "script_doc_out"
    output_dir.mkdir()
    mocker.patch(
        "demisto_sdk.commands.generate_docs.generate_script_doc.ContentGraphInterface",
        return_value=interface,
    )
    mocker.patch(
        "demisto_sdk.commands.generate_docs.generate_script_doc.update_content_graph",
        return_value=interface,
    )
    generate_script_doc(input_path=f"{str(input_script_object.path)}/SampleScript.yml",
                        examples="!Set key=k1 value=v1,!Set key=k2 value=v2 append=true",
                        output=str(output_dir))
    readme = output_dir / "README.md"
    with ReadMeValidator.start_mdx_server():
        with open(readme) as file:
            assert not run_markdownlint(file.read()).has_errors

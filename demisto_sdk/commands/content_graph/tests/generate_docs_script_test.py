import os
from pathlib import Path
from typing import List

import pytest

from demisto_sdk.commands.common.tests.docker_test import FILES_PATH
from demisto_sdk.commands.content_graph import neo4j_service
from demisto_sdk.commands.content_graph.commands.create import create_content_graph
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
from demisto_sdk.commands.content_graph.tests.update_content_graph_test import (
    _get_pack_by_id,
)
from demisto_sdk.commands.generate_docs.generate_script_doc import generate_script_doc
from demisto_sdk.commands.generate_docs.tests.generate_docs_test import handle_example
from TestSuite.repo import Repo

INPUT_SCRIPT = "SampleScript"
USES_SCRIPT = "UsesScript"
USED_BY_PLAYBOOK = "SamplePlaybook"

# FIXTURES


@pytest.fixture(autouse=True)
def setup_method(mocker, tmp_path_factory, repo: Repo):
    """Auto-used fixture for setup before every test run"""
    import demisto_sdk.commands.content_graph.objects.base_content as bc

    bc.CONTENT_PATH = Path(repo.path)
    mocker.patch.object(
        neo4j_service, "NEO4J_DIR", new=tmp_path_factory.mktemp("neo4j")
    )
    mocker.patch.object(ContentGraphInterface, "repo_path", Path(repo.path))


@pytest.fixture
def repository(mocker, repo) -> ContentDTO:
    repository = ContentDTO(
        path=Path(repo.path),
        packs=[],
    )
    relationships = {
        RelationshipType.USES: [
            mock_relationship(
                INPUT_SCRIPT, ContentType.SCRIPT, USES_SCRIPT, ContentType.SCRIPT
            ),
            mock_relationship(
                USED_BY_PLAYBOOK, ContentType.PLAYBOOK, INPUT_SCRIPT, ContentType.SCRIPT
            ),
        ]
    }

    repo_pack = repo.create_pack()
    in_script_yml = os.path.join(FILES_PATH, "docs_test", "script-Set.yml")
    script = repo_pack.create_script(name=INPUT_SCRIPT)
    with open(in_script_yml) as original_yml, open(
        f"{script.path}/{INPUT_SCRIPT}.yml", "w"
    ) as new_script_yml:
        for line in original_yml:
            new_script_yml.write(line)

    pack = mock_pack()
    pack.relationships = relationships
    pack.content_items.script.append(
        mock_script(name=INPUT_SCRIPT, path=Path(f"{script.path}/{INPUT_SCRIPT}.yml"))
    )
    pack.content_items.script.append(mock_script(USES_SCRIPT))
    pack.content_items.playbook.append(mock_playbook(USED_BY_PLAYBOOK))
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


def test_generate_script_doc_graph(mocker, repository, tmp_path):
    """
    Given
    - A script (SampleScript) that uses another script (UsesScript)and is used by a playbook (SamplePlaybook).
    When
    - Running generate-docs command on the script.
    Then
    -  The generated readme will have:
        1. no markdown errors.
        2. will contain the names of the script that the input script uses, and the name of the playbook the uses
            the script.
    """
    import demisto_sdk.commands.generate_docs.common as common

    with ContentGraphInterface() as interface:
        create_content_graph(interface)

    pack_graph_object = _get_pack_by_id(repository, "SamplePack")
    input_script_object = pack_graph_object.content_items.script[0]  # INPUTSCRIPT
    expected_readme = os.path.join(FILES_PATH, "docs_test", "set_expected-README.md")
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
    mocker.patch.object(common, "execute_command", side_effect=handle_example)

    generate_script_doc(
        input_path=str(input_script_object.path),
        examples="!Set key=k1 value=v1,!Set key=k2 value=v2 append=true",
        output=str(output_dir),
    )
    readme = output_dir / "README.md"
    readme_content = readme.read_text()
    # check the readme content
    with open(expected_readme) as expected_readme_file:
        assert readme_content == expected_readme_file.read()

    # Now try the same thing with a txt file
    command_examples = output_dir / "command_examples.txt"
    with command_examples.open("w") as f:
        f.write("!Set key=k1 value=v1\n!Set key=k2 value=v2 append=true")
    generate_script_doc(
        str(input_script_object.path), command_examples, str(output_dir)
    )
    with open(expected_readme) as expected_readme_file:
        assert readme_content == expected_readme_file.read()

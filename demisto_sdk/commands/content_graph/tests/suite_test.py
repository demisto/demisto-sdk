

import pytest
from pathlib import Path
from TestSuite.repo import Repo
from TestSuite.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO

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

def test_suite(tmpdir, repository):
    repo = Repo(Path(tmpdir))
    pack  = repo.create_pack()
    pack.create_integration()
    pack.object
    pack.object
    pack.object
    pack.object
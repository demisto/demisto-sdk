from pathlib import Path

import pytest

from demisto_sdk.scripts.validate_conf_json import ConfJsonValidator
from TestSuite.repo import Repo


def test_sanity(graph_repo: Repo):
    """
    Given   an empty repo with an empty conf.json
    When    calling validate
    Then    make sure it passes
    """
    graph_repo.create_pack()
    graph = graph_repo.create_graph()
    validator = ConfJsonValidator(Path(graph_repo.conf.path), graph)
    assert validator.validate()


@pytest.mark.parametrize("list_of_integrations", (True, False))
def test_integration_playbook_positive(
    graph_repo: Repo, list_of_integrations: bool
) -> None:
    """
    Given   a repo with one integration and one playbook
    When    calling validate
    Then    make sure it passes
    """
    pack = graph_repo.create_pack()
    playbook = pack.create_test_playbook("SamplePlaybookTest")
    integration = pack.create_integration()

    graph_repo.conf.write_json(
        tests=[
            {
                "playbookID": playbook.name,
                "integrations": [integration.name]
                if list_of_integrations
                else integration.name,
            }
        ]
    )
    graph = graph_repo.create_graph()
    validator = ConfJsonValidator(Path(graph_repo.conf.path), graph)
    assert validator._validate_content_exists()
    assert validator.validate()


def test_integration_mistyped(graph_repo: Repo) -> None:
    """
    Given   a repo with one integration, whose name is mistyped in conf.json
    When    calling validate
    Then    make sure it fails
    """
    pack = graph_repo.create_pack()
    pack.create_test_playbook("SamplePlaybookTest")
    pack.create_integration(name="foo")
    graph_repo.conf.write_json(
        tests=[
            {
                "playbookID": "SamplePlaybookTest",
                "integrations": "FOO",
            }
        ]
    )
    graph = graph_repo.create_graph()
    validator = ConfJsonValidator(Path(graph_repo.conf.path), graph)
    assert not validator._validate_content_exists()
    assert not validator.validate()


def test_invalid_skipped_integration(graph_repo: Repo) -> None:
    """
    Given   a repo with one skipped integration configured, but doesn't exist in the repo
    When    calling validate
    Then    make sure it fails
    """
    pack = graph_repo.create_pack()
    pack.create_test_playbook("SamplePlaybookTest")
    graph_repo.conf.write_json(skipped_integrations={"hello": "world"})
    graph = graph_repo.create_graph()
    validator = ConfJsonValidator(Path(graph_repo.conf.path), graph)
    assert not validator.validate()

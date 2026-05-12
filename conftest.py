"""Configuring tests for the content suite"""

import os
import shutil
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from _pytest.fixtures import FixtureRequest
from _pytest.tmpdir import TempPathFactory, _mk_tmp

import demisto_sdk.commands.common.tools as tools
from demisto_sdk.__main__ import register_commands
from demisto_sdk.commands.common.constants import DEMISTO_SDK_LOG_NO_COLORS
from demisto_sdk.commands.content_graph.interface.graph import ContentGraphInterface
from TestSuite.integration import Integration
from TestSuite.json_based import JSONBased
from TestSuite.pack import Pack
from TestSuite.playbook import Playbook
from TestSuite.repo import Repo
from TestSuite.yml import YAML

# Helper Functions


def get_repo(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Repo:
    tmp_dir = _mk_tmp(request, tmp_path_factory)
    return Repo(tmp_dir)


def get_git_repo(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Repo:
    tmp_dir = _mk_tmp(request, tmp_path_factory)
    return Repo(tmp_dir, init_git=True)


def get_pack(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Pack:
    """Mocking tmp_path"""
    return get_repo(request, tmp_path_factory).create_pack()


def get_integration(
    request: FixtureRequest, tmp_path_factory: TempPathFactory
) -> Integration:
    """Mocking tmp_path"""
    integration = get_pack(request, tmp_path_factory).create_integration()
    integration.create_default_integration()
    return integration


def get_playbook(
    request: FixtureRequest, tmp_path_factory: TempPathFactory
) -> Playbook:
    """Mocking tmp_path"""
    playbook = get_pack(request, tmp_path_factory).create_playbook()
    playbook.create_default_playbook()
    return playbook


def get_script(request: FixtureRequest, tmp_path_factory: TempPathFactory):
    script = get_pack(request, tmp_path_factory).create_script()
    script.create_default_script()
    return script


# Fixtures


@pytest.fixture
def pack(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Pack:
    """Mocking tmp_path"""
    return get_pack(request, tmp_path_factory)


@pytest.fixture()
def script(request: FixtureRequest, tmp_path_factory: TempPathFactory):
    return get_script(request, tmp_path_factory)


@pytest.fixture
def integration(
    request: FixtureRequest, tmp_path_factory: TempPathFactory
) -> Integration:
    """Mocking tmp_path"""
    return get_integration(request, tmp_path_factory)


@pytest.fixture
def repo(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Repo:
    """
    Initializes a repo without git.
    """
    return get_repo(request, tmp_path_factory)


@pytest.fixture
def graph_repo(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Generator:
    """
    Initializes a repo with graph required mocks.

    Patches CONTENT_PATH at every import site (not just base_content) so that
    Pydantic validators on Pack/ContentItem resolve relative paths against the
    temp test repo, not the runtime checkout. Without this, paths stored in
    the graph as `Packs/<pack_id>` get resolved to `<runtime_repo>/Packs/<pack_id>`,
    causing `FileNotFoundError` for pack ids that happen to exist in the runtime
    checkout (e.g. `Base`).

    Also clears the lru_cache on `BaseContent.from_path` and `get_file` so that
    cached `Path("Packs/<pack_id>")` keys from previous tests are not reused.
    """
    import demisto_sdk.commands.content_graph.objects.base_content as bc
    from demisto_sdk.commands.common import content_constant_paths as ccp
    from demisto_sdk.commands.common import tools as common_tools
    from demisto_sdk.commands.content_graph.interface import graph as graph_iface
    from demisto_sdk.commands.content_graph.objects import (
        content_item as ci,
        pack as pack_mod,
    )
    from demisto_sdk.commands.content_graph.parsers import (
        base_content as parsers_bc,
    )
    from demisto_sdk.commands.content_graph.objects.base_content import (
        BaseContent as _BaseContent,
    )

    repo = get_repo(request, tmp_path_factory)
    repo_path = Path(repo.path)

    # Save originals so we can restore them after the test.
    originals = {
        "bc": bc.CONTENT_PATH,
        "ccp": ccp.CONTENT_PATH,
        "ci": ci.CONTENT_PATH,
        "pack": pack_mod.CONTENT_PATH,
        "parsers_bc": parsers_bc.CONTENT_PATH,
        "graph_iface": graph_iface.CONTENT_PATH,
        "interface_repo_path": ContentGraphInterface.repo_path,
    }

    # Override CONTENT_PATH at *every* import site so Pydantic validators on
    # Pack/ContentItem resolve relative paths against the temp test repo, not
    # the runtime checkout. Without this, the path stored in the graph as
    # `Packs/<pack_id>` would resolve to `<runtime_repo>/Packs/<pack_id>`,
    # causing FileNotFoundError for pack ids that exist in the runtime
    # checkout (e.g. `Base`).
    bc.CONTENT_PATH = repo_path
    ccp.CONTENT_PATH = repo_path
    ci.CONTENT_PATH = repo_path
    pack_mod.CONTENT_PATH = repo_path
    parsers_bc.CONTENT_PATH = repo_path
    graph_iface.CONTENT_PATH = repo_path
    ContentGraphInterface.repo_path = repo_path

    neo4j_path = repo_path.parent.parent / "neo4j"

    # Clear lru_caches whose keys are paths that may collide with paths
    # constructed by other tests (notably `Path("Packs/Base")`). Without
    # this, a stale cached entry from another test can return a Pack with a
    # `path` pointing to the (non-existent) runtime `Packs/Base`.
    if hasattr(_BaseContent.from_path, "cache_clear"):
        _BaseContent.from_path.cache_clear()
    if hasattr(common_tools.get_file, "cache_clear"):
        common_tools.get_file.cache_clear()

    try:
        yield repo
    finally:
        # Restore originals so subsequent tests see the runtime values.
        bc.CONTENT_PATH = originals["bc"]
        ccp.CONTENT_PATH = originals["ccp"]
        ci.CONTENT_PATH = originals["ci"]
        pack_mod.CONTENT_PATH = originals["pack"]
        parsers_bc.CONTENT_PATH = originals["parsers_bc"]
        graph_iface.CONTENT_PATH = originals["graph_iface"]
        ContentGraphInterface.repo_path = originals["interface_repo_path"]

        if hasattr(_BaseContent.from_path, "cache_clear"):
            _BaseContent.from_path.cache_clear()
        if hasattr(common_tools.get_file, "cache_clear"):
            common_tools.get_file.cache_clear()

        if (neo4j_path / "neo4j-data/data").exists():
            shutil.rmtree(neo4j_path / "neo4j-data/data")


@pytest.fixture
def git_repo(request: FixtureRequest, tmp_path_factory: TempPathFactory):
    """
    Initializes a repo with git.
    """
    return get_git_repo(request, tmp_path_factory)


@pytest.fixture(scope="module")
def module_repo(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Repo:
    from demisto_sdk.commands.find_dependencies.tests.find_dependencies_test import (
        working_repo,
    )

    return working_repo(get_repo(request, tmp_path_factory))


@pytest.fixture
def playbook(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> Playbook:
    """Mocking tmp_path"""
    return get_playbook(request, tmp_path_factory)


@pytest.fixture()
def malformed_integration_yml(integration) -> YAML:
    """
    Provides an invalid integration yml structure.
    """
    integration.yml.write("1: 2\n//")
    return integration.yml


@pytest.fixture()
def malformed_incident_field(pack) -> JSONBased:
    """
    Provides an invalid incident field json structure.
    """
    incident_field = pack.create_incident_field("malformed")
    incident_field.write_as_text("{\n '1': '1'")
    return incident_field


@pytest.fixture(scope="session", autouse=True)
def mock_update_id_set_cpu_count() -> Generator:
    """
    Since Circle build has an issue in it's virtualization where it has only 2 vcpu's but the 'cpu_count' method returns
    all physical cpu's (36) it uses too many processes in the process pools.
    """
    with mock.patch(
        "demisto_sdk.commands.common.update_id_set.cpu_count", return_value=2
    ) as _fixture:
        yield _fixture


@pytest.fixture(scope="session", autouse=True)
def disable_log_colors():
    os.environ[DEMISTO_SDK_LOG_NO_COLORS] = "1"


@pytest.fixture(autouse=True)
def clear_cache():
    tools.get_file.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def register_sdk_commands():
    """
    Ensure that demisto-sdk Typer app commands are registered before each test session.
    """
    register_commands()

from contextlib import contextmanager
from filecmp import cmp, dircmp
from shutil import copyfile, copytree, rmtree

import pytest
from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PRIVATE_CONTENT_REPO = TEST_DATA / 'private_content_slim'
UNIT_TEST_DATA = (src_root() / 'commands' / 'create_artifacts' / 'tests' / 'data')
COMMON_SERVER = UNIT_TEST_DATA / 'modify_common_server_constants_test'
EXPECTED_ARTIFACT_CONTENT = UNIT_TEST_DATA / 'create_content_artifacts_test' / 'content_expected_artifact'
EXPECTED_ARTIFACT_PRIVATE_CONTENT = UNIT_TEST_DATA / 'create_content_artifacts_test' / 'content_private_expected_artifact'


def same_folders(dcmp):
    if dcmp.left_only or dcmp.right_only:
        assert False, f"\n{dcmp.right} only:\n{dcmp.right_only}\n{dcmp.left} only:\n{dcmp.left_only}"
    for sub_dcmp in dcmp.subdirs.values():
        same_folders(sub_dcmp)


@contextmanager
def destroy_by_suffix(suffix: str):
    if suffix == 'json':
        file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "Classifiers" / "classifier-sample_new.json"
    else:
        file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "TestPlaybooks" / "playbook-sample3_new.yml"
    old_data = file.read_text()
    file.write_text("{123dfdsf,}\nfdsfdsf")

    try:
        yield
    finally:
        file.write_text(old_data)


@contextmanager
def duplicate_file():
    file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "TestPlaybooks" / "playbook-sample3_new.yml"
    new_file = TEST_CONTENT_REPO / "Packs" / "Sample02" / "TestPlaybooks" / "playbook-sample3_new.yml"
    try:
        copyfile(file, new_file)
        yield
    finally:
        new_file.unlink()


@contextmanager
def temp_dir():
    temp = UNIT_TEST_DATA / 'temp'
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)


@pytest.fixture()
def mock_git(mocker):
    from demisto_sdk.commands.common.content import Content
    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = TEST_CONTENT_REPO
    yield


@pytest.fixture()
def private_repo():
    try:
        copytree(TEST_CONTENT_REPO, TEST_PRIVATE_CONTENT_REPO)
        test_playbook_dir = TEST_PRIVATE_CONTENT_REPO / TEST_PLAYBOOKS_DIR
        rmtree(test_playbook_dir)
        yield TEST_PRIVATE_CONTENT_REPO
    finally:
        rmtree(TEST_PRIVATE_CONTENT_REPO)


def test_modify_common_server_constants(datadir):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import modify_common_server_constants
    path_before = COMMON_SERVER / 'CommonServerPython.py'
    path_excepted = COMMON_SERVER / 'CommonServerPython_modified.py'
    old_data = path_before.read_text()
    modify_common_server_constants(path_before, '6.0.0', 'test')
    assert cmp(path_before, path_excepted)
    path_before.write_text(old_data)


def test_create_content_artifacts(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  content_packs=False)
        exit_code = create_content_artifacts(artifact_manager=config)

        assert exit_code == 0
        same_folders(dircmp(temp, EXPECTED_ARTIFACT_CONTENT))


def test_create_private_content_artifacts(private_repo):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager,
                                                                                 create_content_artifacts)
    from demisto_sdk.commands.common.content import Content

    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  content_packs=False)
        config.content = Content(private_repo)
        exit_code = create_content_artifacts(artifact_manager=config)

        same_folders(dircmp(temp, EXPECTED_ARTIFACT_PRIVATE_CONTENT))

    assert exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failue(suffix: str, mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  content_packs=False)

        with destroy_by_suffix(suffix):
            exit_code = create_content_artifacts(artifact_manager=config)

    assert exit_code == 1


def test_duplicate_file_failue(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  content_packs=False)

        with duplicate_file():
            exit_code = create_content_artifacts(artifact_manager=config)

    assert exit_code == 1

from wcmatch.pathlib import Path, NEGATE
from filecmp import cmp, dircmp
from shutil import rmtree, copyfile, copytree
from contextlib import contextmanager

import pytest

from demisto_sdk.commands.common.tools import path_test_files, src_root
from demisto_sdk.commands.common.constants import TEST_PLAYBOOKS_DIR


TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PRIVATE_CONTENT_REPO = TEST_DATA / 'private_content_slim'
UNIT_TEST_DATA = (src_root() / 'commands' / 'create_artifacts' / 'tests' / 'content_artifacts_creator_test'
                  / 'test_create_content_artifacts')
EXPECTED_ARTIFACT_CONTENT = UNIT_TEST_DATA / 'content_expected_artifact'
EXPECTED_ARTIFACT_PRIVATE_CONTENT = UNIT_TEST_DATA / 'content_private_expected_artifact'


def same_folders(dcmp):
    if dcmp.diff_files:
        return False
    for sub_dcmp in dcmp.subdirs.values():
        if not same_folders(sub_dcmp):
            return False
    return True


@contextmanager
def destroy_by_suffix(root_path: Path, suffix: str):
    file = next(root_path.glob(patterns=[rf"*/*/*/*.{suffix}", "!doc-*"], flags=NEGATE))
    old_data = file.read_text()
    file.write_text("{123dfdsf,}\nfdsfdsf")
    yield
    file.write_text(old_data)


@contextmanager
def duplicate_file():
    file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "TestPlaybooks" / "playbook-sample_new.yml"
    new_file = TEST_CONTENT_REPO / "Packs" / "Sample02" / "TestPlaybooks" / "playbook-sample_new.yml"
    copyfile(file, new_file)
    yield
    new_file.unlink()


@contextmanager
def temp_dir():
    temp = TEST_DATA / '.temp'
    temp.mkdir(parents=True, exist_ok=True)
    yield temp
    rmtree(temp)


@pytest.fixture()
def mock_git(mocker):
    from demisto_sdk.commands.common.content.content import Content
    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = TEST_CONTENT_REPO
    yield


@pytest.fixture()
def private_repo():
    copytree(TEST_CONTENT_REPO, TEST_PRIVATE_CONTENT_REPO)
    test_playbook_dir = TEST_PRIVATE_CONTENT_REPO / TEST_PLAYBOOKS_DIR
    rmtree(test_playbook_dir)
    yield TEST_PRIVATE_CONTENT_REPO
    rmtree(TEST_PRIVATE_CONTENT_REPO)


def test_modify_common_server_constants(datadir):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import modify_common_server_constants
    path_before = Path(datadir['CommonServerPython.py'])
    path_excepted = Path(datadir['CommonServerPython_modified.py'])
    old_data = path_before.read_text()
    modify_common_server_constants(path_before, 'test', '6.0.0')
    assert cmp(path_before, path_excepted)
    path_before.write_text(old_data)


def test_create_content_artifacts(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)

    expected_artifacts_path = UNIT_TEST_DATA / 'content_expected_artifact'
    with temp_dir() as temp:
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)
        exit_code = create_content_artifacts(artifact_conf=config)

        assert exit_code == 0
        assert same_folders(dircmp(temp, expected_artifacts_path))


def test_create_private_content_artifacts(private_repo):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    from demisto_sdk.commands.common.content.content import Content

    with temp_dir() as temp:
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)
        config.content = Content(private_repo)
        exit_code = create_content_artifacts(artifact_conf=config)
        assert not dircmp(temp, private_repo).diff_files

    assert exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failue(suffix: str, mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)

        with destroy_by_suffix(TEST_CONTENT_REPO, suffix):
            exit_code = create_content_artifacts(artifact_conf=config)

    assert exit_code == 1


def test_duplicate_file_failue(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)

        with duplicate_file():
            exit_code = create_content_artifacts(artifact_conf=config)

    assert exit_code == 1

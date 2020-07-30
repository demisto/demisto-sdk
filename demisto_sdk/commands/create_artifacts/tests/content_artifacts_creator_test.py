from wcmatch.pathlib import Path, NEGATE
from filecmp import cmp, dircmp
from shutil import rmtree, copyfile
from contextlib import contextmanager

import pytest

UNIT_TEST_DATA = Path(__file__).parent / 'content_artifacts_creator_test' / 'test_create_content_artifacts'
UNIT_TEST_CONTENT_REPO = UNIT_TEST_DATA / 'content'
UNIT_TEST_PRIVATE_CONTENT_REPO = UNIT_TEST_DATA / 'private_content'


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
    file = UNIT_TEST_CONTENT_REPO / "Packs" / "Sample01" / "TestPlaybooks" / "playbook-sample_new.yml"
    new_file = UNIT_TEST_CONTENT_REPO / "Packs" / "Sample02" / "TestPlaybooks" / "playbook-sample_new.yml"
    copyfile(file, new_file)
    yield
    new_file.unlink()


@contextmanager
def temp_dir():
    temp = UNIT_TEST_DATA / 'temp'
    yield temp
    rmtree(temp)


@pytest.fixture()
def mock_git(mocker):
    from demisto_sdk.commands.common.content.content import Content
    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = UNIT_TEST_CONTENT_REPO
    yield


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


def test_create_private_content_artifacts(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)

    with temp_dir() as temp:
        expected_artifacts_path = UNIT_TEST_DATA / 'content_expected_artifact'
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)
        exit_code = create_content_artifacts(artifact_conf=config)
        assert not dircmp(temp, expected_artifacts_path).diff_files

    assert exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failue(suffix: str, mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsConfiguration,
                                                                                 create_content_artifacts)
    with temp_dir() as temp:
        content_repo = UNIT_TEST_DATA / 'content'
        config = ArtifactsConfiguration(artifacts_path=temp,
                                        content_version='6.0.0',
                                        zip=False,
                                        suffix='',
                                        cpus=1,
                                        content_packs=False)

        with destroy_by_suffix(content_repo, suffix):
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

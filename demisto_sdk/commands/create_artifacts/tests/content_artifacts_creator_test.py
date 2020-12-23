from contextlib import contextmanager
from datetime import datetime
from filecmp import cmp, dircmp
from shutil import copyfile, copytree, rmtree

import pytest
from demisto_sdk.commands.common.constants import PACKS_DIR, TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.tools import src_root
from packaging.version import parse
from TestSuite.test_tools import ChangeCWD

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PRIVATE_CONTENT_REPO = TEST_DATA / 'private_content_slim'
UNIT_TEST_DATA = (src_root() / 'commands' / 'create_artifacts' / 'tests' / 'data')
COMMON_SERVER = UNIT_TEST_DATA / 'common_server'
ARTIFACTS_EXPECTED_RESULTS = TEST_DATA / 'artifacts'


def same_folders(src1, src2):
    """Assert if folder contains different files"""
    dcmp = dircmp(src1, src2)
    if dcmp.left_only or dcmp.right_only:
        return False
    for sub_dcmp in dcmp.subdirs.values():
        same_folders(sub_dcmp.left, sub_dcmp.right)

    return True


@contextmanager
def destroy_by_ext(suffix: str):
    """Modify file content to invalid by file extension - json/yaml.

     Open:
        - Choose file by file extension.
        - Modify file content to not valid.

    Close:
        - Modify content to the original state.
    """
    if suffix == 'json':
        file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "Classifiers" / "classifier-sample_new.json"
    else:
        file = TEST_CONTENT_REPO / "Packs" / "Sample01" / "TestPlaybooks" / "playbook-sample_test1.yml"
    old_data = file.read_text()
    file.write_text("{123dfdsf,}\nfdsfdsf")

    try:
        yield
    finally:
        file.write_text(old_data)


@contextmanager
def duplicate_file():
    """Create duplicate file name in content repository.

     Open:
        - Create copy of file in content.

    Close:
        - Delete copied file.
    """
    file = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / TEST_PLAYBOOKS_DIR / "playbook-sample_test1.yml"
    new_file = TEST_CONTENT_REPO / PACKS_DIR / "Sample02" / TEST_PLAYBOOKS_DIR / "playbook-sample_test1.yml"
    try:
        copyfile(file, new_file)
        yield
    finally:
        new_file.unlink()


@contextmanager
def temp_dir():
    """Create Temp directory for test.

     Open:
        - Create temp directory.

    Close:
        - Delete temp directory.
    """
    temp = UNIT_TEST_DATA / 'temp'
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)


@pytest.fixture()
def mock_git(mocker):
    """Mock git Repo object"""
    from demisto_sdk.commands.common.content import Content

    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = TEST_CONTENT_REPO
    yield


@pytest.fixture()
def private_repo():
    """Create Temp private repo structure from original content structure.

     Open:
        - Create a copy of regular content.
        - Delete - content/TestPlaybooks dir.

    Close:
        - Delete private content folder.
    """
    try:
        copytree(TEST_CONTENT_REPO, TEST_PRIVATE_CONTENT_REPO)
        test_playbook_dir = TEST_PRIVATE_CONTENT_REPO / TEST_PLAYBOOKS_DIR
        rmtree(test_playbook_dir)
        yield TEST_PRIVATE_CONTENT_REPO
    finally:
        rmtree(TEST_PRIVATE_CONTENT_REPO)


def test_modify_common_server_constants():
    """ Modify global variables in CommonServerPython.py

    When: CommonServerPython.py contains:
            - Global variable - CONTENT_RELEASE_VERSION = '0.0.0'
            - Global variable - CONTENT_BRANCH_NAME = ''

    Given: Parameters:
            - Content version x.x.x
            - Active branch - xxxx

    Then: CommonServerPython.py changes:
            - Global variable - CONTENT_RELEASE_VERSION = 'x.x.x'
            - Global variable - CONTENT_BRANCH_NAME = 'xxxx'

    Notes:
        - After test clean up changes.
    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        modify_common_server_constants
    path_before = COMMON_SERVER / 'CommonServerPython.py'
    path_excepted = COMMON_SERVER / 'CommonServerPython_modified.py'
    old_data = path_before.read_text()
    modify_common_server_constants(path_before, '6.0.0', 'test')

    assert cmp(path_before, path_excepted)

    path_before.write_text(old_data)


def test_load_user_metadata_basic(repo):
    """
    When:
        - Dumping a specific pack, processing the pack's metadata.

    Given:
        - Pack object.

    Then:
        - Verify that pack's metadata information was loaded successfully.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, load_user_metadata)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'description': 'A description for the pack',
            'created': '2020-06-08T15:37:54Z',
            'price': 0,
            'support': 'xsoar',
            'url': 'some url',
            'email': 'some email',
            'currentVersion': '1.1.1',
            'author': 'Cortex XSOAR',
            'tags': ['tag1'],
            'dependencies': [{'dependency': {'dependency': '1'}}]
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True)

    result = load_user_metadata(artifact_manager.content.packs['Pack1'])
    assert result.id == 'Pack1'
    assert result.name == 'Pack Number 1'
    assert result.description == 'A description for the pack'
    assert result.created == datetime(2020, 6, 8, 15, 37, 54)
    assert result.price == 0
    assert result.support == 'xsoar'
    assert result.url == 'some url'
    assert result.email == 'some email'
    assert result.certification == 'certified'
    assert result.current_version == parse('1.1.1')
    assert result.author == 'Cortex XSOAR'
    assert result.tags == ['tag1']
    assert result.dependencies == [{'dependency': {'dependency': '1'}}]


def test_dump_pack(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, Pack, create_dirs, dump_pack)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)

        create_dirs(artifact_manager=config)
        dump_pack(artifact_manager=config, pack=Pack(TEST_CONTENT_REPO / PACKS_DIR / 'Sample01'))

        assert same_folders(src1=temp / 'content_packs' / 'Sample01',
                            src2=ARTIFACTS_EXPECTED_RESULTS / 'content' / 'content_packs' / 'Sample01')


def test_create_content_artifacts(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)
        exit_code = config.create_content_artifacts()

        assert exit_code == 0
        assert same_folders(temp, ARTIFACTS_EXPECTED_RESULTS / 'content')


def test_create_private_content_artifacts(private_repo):
    from demisto_sdk.commands.common.content import Content
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager)

    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)
        config.content = Content(private_repo)
        exit_code = config.create_content_artifacts()

        assert same_folders(temp, ARTIFACTS_EXPECTED_RESULTS / 'private')
        assert exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failure(suffix: str, mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)

        with destroy_by_ext(suffix):
            exit_code = config.create_content_artifacts()

    assert exit_code == 1


def test_duplicate_file_failure(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (ArtifactsManager)
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)

        with duplicate_file():
            exit_code = config.create_content_artifacts()

    assert exit_code == 1

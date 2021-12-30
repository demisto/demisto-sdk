from contextlib import contextmanager
from filecmp import cmp, dircmp
from pathlib import Path
from shutil import copyfile, copytree, rmtree

import pytest

from demisto_sdk.commands.common.constants import PACKS_DIR, TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.logger import logging_setup
from demisto_sdk.commands.common.tools import (is_object_in_id_set,
                                               open_id_set_file, src_root)
from TestSuite.test_tools import ChangeCWD

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_PRIVATE_CONTENT_REPO = TEST_DATA / 'private_content_slim'
UNIT_TEST_DATA = (src_root() / 'commands' / 'create_artifacts' / 'tests' / 'data')
COMMON_SERVER = UNIT_TEST_DATA / 'common_server'
ARTIFACTS_EXPECTED_RESULTS = TEST_DATA / 'artifacts'
PARTIAL_ID_SET_PATH = UNIT_TEST_DATA / 'id_set_missing_packs_and_items.json'


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


def test_dump_pack(mock_git):
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, Pack, create_dirs, dump_pack)

    cca.logger = logging_setup(0)

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


def test_contains_indicator_type():
    """
    Given
    - A pack with old and new indicator type.

    When
    - Running zip-packs on it.

    Then
    - Ensure that the new indicator type is added to the zipped pack, and that the old one is not.
    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.zip_packs.packs_zipper import PacksZipper

    cca.logger = logging_setup(0)

    with temp_dir() as temp:
        packs_zipper = PacksZipper(pack_paths=str(TEST_DATA / PACKS_DIR / 'TestIndicatorTypes'),
                                   output=temp,
                                   content_version='6.0.0',
                                   zip_all=False)
        packs_zipper.zip_packs()
        assert packs_zipper.artifacts_manager.packs['TestIndicatorTypes'].metadata.content_items != {}
        assert packs_zipper.artifacts_manager.packs['TestIndicatorTypes'].metadata.content_items['reputation'] == [
            {
                "details": "Good Sample",
                "reputationScriptName": "",
                "enhancementScriptNames": []
            }
        ]


def test_create_content_artifacts(mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager
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


def test_create_content_artifacts_by_id_set(mock_git):
    """

    Test the case where content artifacts are being created by an id set.
    This test has the following cases:
    1. A pack is not exsiting in the id set - the pack will not exist as an artifact.
    2. An item of a pack does not exist under the pack's section in the id set - the item will not exist as an artifact.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager
    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False,
                                  filter_by_id_set=True,
                                  id_set_path=PARTIAL_ID_SET_PATH)
        exit_code = config.create_content_artifacts()

        assert exit_code == 0
        assert same_folders(temp, ARTIFACTS_EXPECTED_RESULTS / 'content_filtered_by_id_set')


def test_create_private_content_artifacts(private_repo):
    from demisto_sdk.commands.common.content import Content
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager

    with temp_dir() as temp:
        config = ArtifactsManager(artifacts_path=temp,
                                  content_version='6.0.0',
                                  zip=False,
                                  suffix='',
                                  cpus=1,
                                  packs=False)
        config.content = Content(private_repo)
        config.packs = config.content.packs
        exit_code = config.create_content_artifacts()

        assert same_folders(temp, ARTIFACTS_EXPECTED_RESULTS / 'private')
        assert exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failure(suffix: str, mock_git):
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager
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
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import \
        ArtifactsManager
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


@pytest.mark.parametrize('key, tool', [('some_key', False), ('', True)])
def test_sign_packs_failure(repo, capsys, key, tool):
    """
    When:
        - Signing a pack.

    Given:
        - Pack object.
        - Signature key without the signing tool, or vice-versa.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, sign_packs)

    cca.logger = logging_setup(2)

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True,
                                                signature_key=key)

            if tool:
                with open('./tool', 'w') as tool_file:
                    tool_file.write('some tool')

                artifact_manager.signDirectory = Path(temp / 'tool')

    sign_packs(artifact_manager)

    captured = capsys.readouterr()
    assert 'Failed to sign packs. In order to do so, you need to provide both signature_key and ' \
           'sign_directory arguments.' in captured.out


def test_is_object_in_id_set():
    """
    Given:
        - Pack object.
        - filtered id set.
    When:
        - filter-by-id-set flag is on and we are checking if the pack's items exsit in the id set.
    Then:
        - Return if the item is in the id set or not.

    """
    id_set = open_id_set_file(PARTIAL_ID_SET_PATH)
    packs_section = id_set.get('Packs')
    pack_name = 'Sample1'
    assert not is_object_in_id_set('indicator', packs_section[pack_name])
    assert is_object_in_id_set('scripts-sample_packs', packs_section[pack_name])
    with pytest.raises(Exception) as e:
        is_object_in_id_set('scripts-sample_packs', {"pack_name": {}})
        if not e:
            assert False

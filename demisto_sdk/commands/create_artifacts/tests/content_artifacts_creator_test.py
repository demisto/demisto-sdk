import os
from contextlib import contextmanager
from datetime import datetime
from filecmp import cmp, dircmp
from pathlib import Path
from shutil import copyfile, copytree, rmtree

import pytest
from demisto_sdk.commands.common.constants import PACKS_DIR, TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.logger import logging_setup
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


def test_load_user_metadata_advanced(repo):
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
            'price': 10,
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
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
    assert result.price == 10
    assert result.vendor_id == 'vendorId'
    assert result.vendor_name == 'vendorName'
    assert result.tags == ['tag1', 'Use Case']


def test_load_user_metadata_no_metadata_file(repo, capsys):
    """
    When:
        - Dumping a pack with no pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, load_user_metadata)

    cca.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'price': 'price',
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
        }
    )

    with ChangeCWD(repo.path):
        os.remove(pack_1.pack_metadata.path)
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True)

    load_user_metadata(artifact_manager.content.packs['Pack1'])

    captured = capsys.readouterr()
    assert 'Pack1 pack is missing pack_metadata.json file.' in captured.err


def test_load_user_metadata_invalid_price(repo, capsys):
    """
    When:
        - Dumping a pack with invalid price in pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, load_user_metadata)

    cca.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
            'price': 'price',
            'tags': ['tag1'],
            'useCases': ['usecase1'],
            'vendorId': 'vendorId',
            'vendorName': 'vendorName'
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

    load_user_metadata(artifact_manager.content.packs['Pack1'])

    captured = capsys.readouterr()
    assert 'Pack Number 1 pack price is not valid. The price was set to 0.' in captured.err


def test_load_user_metadata_bad_pack_metadata_file(repo, capsys):
    """
    When:
        - Dumping a pack with invalid pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, load_user_metadata)

    cca.logger = logging_setup(3)

    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_as_text('Invalid of course {')

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True)

    load_user_metadata(artifact_manager.content.packs['Pack1'])

    captured = capsys.readouterr()
    assert 'Failed loading Pack1 user metadata.' in captured.err


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

    cca.logger = logging_setup(3)

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
           'sign_directory arguments.' in captured.err


def test_sign_pack_exception_thrown(repo, capsys, mocker):
    """
    When:
        - Signing a pack.

    Given:
        - Pack object.
        - No signing executable.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import sign_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
    import subprocess

    mocker.patch.object(subprocess, 'Popen', autospec=True)

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    sign_pack(content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert 'Error while trying to sign pack Pack1' in captured.err


def test_sign_pack_error_from_subprocess(repo, capsys, fake_process):
    """
    When:
        - Signing a pack.

    Given:
        - Pack object.
        - subprocess is failing due to an error.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import sign_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    fake_process.register_subprocess(
        f'./signDirectory {pack.path} keyfile base64', stderr=["error"]
    )

    sign_pack(content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert 'Failed to sign pack for Pack1 -' in captured.err


def test_sign_pack_success(repo, capsys, fake_process):
    """
    When:
        - Signing a pack.

    Given:
        - Pack object.

    Then:
        - Verify that success is written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import sign_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    fake_process.register_subprocess(
        f'./signDirectory {pack.path} keyfile base64', stdout=['success']
    )

    sign_pack(content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert f'Signed {content_object_pack.path.name} pack successfully' in captured.err


@pytest.mark.parametrize('key, tool', [('some_key', False), ('', True)])
def test_encrypt_packs_failure(repo, capsys, key, tool):
    """
    When:
        - Encrypting a pack.

    Given:
        - Pack object.
        - Encryption key without the encryption tool, or vice-versa.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager, encrypt_packs)

    cca.logger = logging_setup(3)

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True,
                                                encryption_key=key)

            if tool:
                with open('./tool', 'w') as tool_file:
                    tool_file.write('some tool')

                artifact_manager.encryptor = Path(temp / 'tool')

    encrypt_packs(artifact_manager)

    captured = capsys.readouterr()
    assert 'Failed to encrypt packs. In order to do so, you need to provide both encryption_key and ' \
           'encryptor arguments.' in captured.err


def test_encrypt_pack_exception_thrown(repo, capsys):
    """
    When:
        - Encrypting a pack.

    Given:
        - Pack object.
        - Exception thrown.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import ArtifactsManager, encrypt_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True,
                                                encryption_key='key')

    encrypt_pack(artifact_manager, content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert 'Error while trying to encrypt pack Pack1.' in captured.err


def test_encrypt_pack_error_from_subprocess(repo, capsys, fake_process, mocker):
    """
    When:
        - Encrypting a pack.

    Given:
        - Pack object.
        - subprocess is failing due to an error.

    Then:
        - Verify that exceptions are written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import ArtifactsManager, encrypt_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
    import os

    mocker.patch.object(os, 'chdir', return_value=None)

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    fake_process.register_subprocess(
        f'encryptor_path {pack.path} {pack.path} "key"', stderr=["error"]
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True,
                                                encryption_key='key',
                                                encryptor=Path('encryptor_path'))

    encrypt_pack(artifact_manager, content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert 'Failed to encrypt pack for Pack1 -' in captured.err


def test_encrypt_pack_success(repo, capsys, fake_process, mocker):
    """
    When:
        - Encrypting a pack.

    Given:
        - Pack object.

    Then:
        - Verify that success is written to the logger.

    """
    import demisto_sdk.commands.create_artifacts.content_artifacts_creator as cca
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import ArtifactsManager, encrypt_pack
    from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
    import os

    mocker.patch.object(os, 'chdir', return_value=None)
    mocker.patch.object(os, 'remove', return_value=None)

    cca.logger = logging_setup(3)

    pack = repo.create_pack('Pack1')
    content_object_pack = Pack(pack.path)

    fake_process.register_subprocess(
        f'encryptor_path {pack.path} {pack.path} "key"', stdout=['success']
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(artifacts_path=temp,
                                                content_version='6.0.0',
                                                zip=False,
                                                suffix='',
                                                cpus=1,
                                                packs=True,
                                                encryption_key='key',
                                                encryptor=Path('encryptor_path'))

    encrypt_pack(artifact_manager, content_object_pack, content_object_pack.path, 'key')

    captured = capsys.readouterr()
    assert f'Encrypted {content_object_pack.path.name} pack successfully' in captured.err

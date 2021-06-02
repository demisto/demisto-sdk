import glob
import json
import os
from pathlib import Path
from typing import List, Union

import pytest
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, PACKS_DIR,
                                                   PACKS_PACK_IGNORE_FILE_NAME,
                                                   PLAYBOOKS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   FileType)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import (LOG_COLORS, arg_to_list,
                                               filter_files_by_type,
                                               filter_files_on_pack,
                                               filter_packagify_changes,
                                               find_type, get_code_lang,
                                               get_dict_from_file,
                                               get_entity_id_by_entity_type,
                                               get_entity_name_by_entity_type,
                                               get_file,
                                               get_file_displayed_name,
                                               get_files_in_dir,
                                               get_ignore_pack_skipped_tests,
                                               get_last_release_version,
                                               get_last_remote_release_version,
                                               get_latest_release_notes_text,
                                               get_pack_metadata,
                                               get_release_notes_file_path,
                                               get_ryaml, get_to_version,
                                               has_remote_configured,
                                               is_origin_content_repo,
                                               is_v2_file,
                                               retrieve_file_ending,
                                               run_command_os,
                                               server_version_compare)
from demisto_sdk.tests.constants_test import (IGNORED_PNG,
                                              INDICATORFIELD_EXTRA_FIELDS,
                                              SOURCE_FORMAT_INTEGRATION_COPY,
                                              VALID_BETA_INTEGRATION_PATH,
                                              VALID_DASHBOARD_PATH,
                                              VALID_INCIDENT_FIELD_PATH,
                                              VALID_INCIDENT_TYPE_PATH,
                                              VALID_INTEGRATION_TEST_PATH,
                                              VALID_LAYOUT_PATH, VALID_MD,
                                              VALID_PLAYBOOK_ID_PATH,
                                              VALID_REPUTATION_FILE,
                                              VALID_SCRIPT_PATH,
                                              VALID_WIDGET_PATH)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    LAYOUT, MAPPER, OLD_CLASSIFIER, REPUTATION)
from TestSuite.pack import Pack
from TestSuite.playbook import Playbook
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestGenericFunctions:
    PATH_TO_HERE = f'{git_path()}/demisto_sdk/tests/test_files/'
    FILE_PATHS = [
        (os.path.join(PATH_TO_HERE, 'fake_integration.yml'), tools.get_yaml),
        (os.path.join(PATH_TO_HERE, 'fake_json.json'), tools.get_json)
    ]

    @pytest.mark.parametrize('file_path, func', FILE_PATHS)
    def test_get_file(self, file_path, func):
        assert func(file_path)

    def test_get_file_exception(self):
        path_to_here = f'{git_path()}/demisto_sdk/tests/test_files/'
        assert get_file(json.load, os.path.join(path_to_here, 'fake_integration.yml'), ('yml', 'yaml')) == {}

    @pytest.mark.parametrize('dir_path', ['demisto_sdk', f'{git_path()}/demisto_sdk/tests/test_files'])
    def test_get_yml_paths_in_dir(self, dir_path):
        yml_paths, first_yml_path = tools.get_yml_paths_in_dir(dir_path, error_msg='')
        yml_paths_test = glob.glob(os.path.join(dir_path, '*yml'))
        assert sorted(yml_paths) == sorted(yml_paths_test)
        if yml_paths_test:
            assert first_yml_path == yml_paths_test[0]
        else:
            assert not first_yml_path

    data_test_get_dict_from_file = [
        (VALID_REPUTATION_FILE, 'json'),
        (VALID_SCRIPT_PATH, 'yml'),
        ('test', None),
        (None, None)
    ]

    @pytest.mark.parametrize('path, _type', data_test_get_dict_from_file)
    def test_get_dict_from_file(self, path, _type):
        output = get_dict_from_file(str(path))[1]
        assert output == _type, f'get_dict_from_file({path}) returns: {output} instead {_type}'

    data_test_find_type = [
        (VALID_DASHBOARD_PATH, FileType.DASHBOARD),
        (VALID_INCIDENT_FIELD_PATH, FileType.INCIDENT_FIELD),
        (VALID_INCIDENT_TYPE_PATH, FileType.INCIDENT_TYPE),
        (INDICATORFIELD_EXTRA_FIELDS, FileType.INDICATOR_FIELD),
        (VALID_INTEGRATION_TEST_PATH, FileType.INTEGRATION),
        (VALID_LAYOUT_PATH, FileType.LAYOUT),
        (VALID_PLAYBOOK_ID_PATH, FileType.PLAYBOOK),
        (VALID_REPUTATION_FILE, FileType.REPUTATION),
        (VALID_SCRIPT_PATH, FileType.SCRIPT),
        (VALID_WIDGET_PATH, FileType.WIDGET),
        (IGNORED_PNG, None),
        ('', None),
        ('Author_image.png', None),
    ]

    @pytest.mark.parametrize('path, _type', data_test_find_type)
    def test_find_type(self, path, _type):
        output = find_type(str(path))
        assert output == _type, f'find_type({path}) returns: {output} instead {_type}'

    def test_find_type_ignore_sub_categories(self):
        output = find_type(VALID_BETA_INTEGRATION_PATH)
        assert output == FileType.BETA_INTEGRATION, \
            f'find_type({VALID_BETA_INTEGRATION_PATH}) returns: {output} instead {FileType.BETA_INTEGRATION}'

        output = find_type(VALID_BETA_INTEGRATION_PATH, ignore_sub_categories=True)
        assert output == FileType.INTEGRATION, \
            f'find_type({VALID_BETA_INTEGRATION_PATH}) returns: {output} instead {FileType.INTEGRATION}'

    def test_find_type_no_file(self):
        """
        Given
        - A non existing file path.

        When
        - Running find_type.

        Then
        - Ensure None is returned
        """
        madeup_path = 'some/path'
        output = find_type(madeup_path)
        assert not output

    test_path_md = [
        VALID_MD
    ]

    @pytest.mark.parametrize('path', test_path_md)
    def test_filter_packagify_changes(self, path):
        modified, added, removed = filter_packagify_changes(modified_files=[], added_files=[], removed_files=[path])
        assert modified == []
        assert added == set()
        assert removed == [VALID_MD]

    test_content_path_on_pack = [
        ('AbuseDB',
         {'Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.py', 'Packs/Another_pack/Integrations/example/example.py'})
    ]

    @pytest.mark.parametrize('pack, file_paths_list', test_content_path_on_pack)
    def test_filter_files_on_pack(self, pack, file_paths_list):
        """
        Given
        - Set of files and pack name.
        When
        - Want to filter the list by specific pack.
        Then:
        - Ensure the set of file paths contains only files located in the given pack.
        """
        files_paths = filter_files_on_pack(pack, file_paths_list)
        assert files_paths == {'Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.py'}

    for_test_filter_files_by_type = [
        ({VALID_INCIDENT_FIELD_PATH, VALID_PLAYBOOK_ID_PATH}, [FileType.PLAYBOOK], {VALID_INCIDENT_FIELD_PATH}),
        ({VALID_INCIDENT_FIELD_PATH, VALID_INCIDENT_TYPE_PATH}, [],
         {VALID_INCIDENT_FIELD_PATH, VALID_INCIDENT_TYPE_PATH}),
        (set(), [FileType.PLAYBOOK], set())
    ]

    @pytest.mark.parametrize('files, types, output', for_test_filter_files_by_type)
    def test_filter_files_by_type(self, files, types, output, mocker):
        """
        Given
        - Sets of content files and file types to skip.
        When
        - Want to filter the lists by file typs.
        Then:
        - Ensure the list returned Whiteout the files to skip.
        """
        mocker.patch('demisto_sdk.commands.common.tools.is_file_path_in_pack', return_value='True')
        files = filter_files_by_type(files, types)

        assert files == output

    @pytest.mark.parametrize('path, output', [('demisto.json', 'json'), ('wow', '')])
    def test_retrieve_file_ending(self, path, output):
        assert retrieve_file_ending(path) == output

    @pytest.mark.parametrize('data, entity, output', [
        ({'script': {'type': 'javascript'}}, INTEGRATIONS_DIR, 'javascript'),
        ({'type': 'javascript'}, SCRIPTS_DIR, 'javascript'),
        ({}, LAYOUTS_DIR, '')
    ])
    def test_get_code_lang(self, data, entity, output):
        assert get_code_lang(data, entity) == output

    def test_camel_to_snake(self):
        snake = tools.camel_to_snake('CamelCase')

        assert snake == 'camel_case'


class TestGetRemoteFile:
    content_repo = 'demisto/content'

    def test_get_remote_file_sanity(self):
        hello_world_yml = tools.get_remote_file(
            'Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml',
            github_repo=self.content_repo
        )
        assert hello_world_yml
        assert hello_world_yml['commonfields']['id'] == 'HelloWorld'

    def test_get_remote_file_content_sanity(self):
        hello_world_py = tools.get_remote_file(
            'Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py',
            return_content=True,
            github_repo=self.content_repo
        )
        assert hello_world_py

    def test_get_remote_file_content(self):
        hello_world_py = tools.get_remote_file(
            'Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py',
            return_content=True,
            github_repo=self.content_repo
        )
        hello_world_text = hello_world_py.decode()
        assert isinstance(hello_world_py, bytes)
        assert hello_world_py
        assert 'main()' in hello_world_text
        assert hello_world_text.startswith('"""HelloWorld Integration for Cortex XSOAR (aka Demisto)')

    def test_get_remote_file_origin(self):
        hello_world_yml = tools.get_remote_file(
            'Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml',
            'master',
            github_repo=self.content_repo
        )
        assert hello_world_yml
        assert hello_world_yml['commonfields']['id'] == 'HelloWorld'

    def test_get_remote_file_tag(self):
        gmail_yml = tools.get_remote_file(
            'Integrations/Gmail/Gmail.yml',
            '19.10.0',
            github_repo=self.content_repo
        )
        assert gmail_yml
        assert gmail_yml['commonfields']['id'] == 'Gmail'

    def test_get_remote_file_origin_tag(self):
        gmail_yml = tools.get_remote_file(
            'Integrations/Gmail/Gmail.yml',
            'origin/19.10.0',
            github_repo=self.content_repo
        )
        assert gmail_yml
        assert gmail_yml['commonfields']['id'] == 'Gmail'

    def test_get_remote_file_invalid(self):
        invalid_yml = tools.get_remote_file(
            'Integrations/File/File.yml',
            '19.10.0',
            github_repo=self.content_repo
        )
        assert not invalid_yml

    def test_get_remote_file_invalid_branch(self):
        invalid_yml = tools.get_remote_file(
            'Integrations/Gmail/Gmail.yml',
            'NoSuchBranch',
            github_repo=self.content_repo
        )
        assert not invalid_yml

    def test_get_remote_file_invalid_origin_branch(self):
        invalid_yml = tools.get_remote_file(
            'Integrations/Gmail/Gmail.yml',
            'origin/NoSuchBranch',
            github_repo=self.content_repo
        )
        assert not invalid_yml

    def test_get_remote_md_file_origin(self):
        hello_world_readme = tools.get_remote_file(
            'Packs/HelloWorld/README.md',
            'master',
            github_repo=self.content_repo
        )
        assert hello_world_readme == {}

    def test_should_file_skip_validation_negative(self):
        should_skip = tools.should_file_skip_validation(
            'Packs/HelloWorld/Integrations/HelloWorld/search_alerts.json'
        )
        assert not should_skip

    SKIPPED_FILE_PATHS = [
        'some_text_file.txt',
        'pack_metadata.json',
        'testdata/file.json',
        'test_data/file.json',
        'data_test/file.json',
        'testcommandsfunctions/file.json',
        'testhelperfunctions/file.json',
        'StixDecodeTest/file.json',
        'TestCommands/file.json',
        'SetGridField_test/file.json',
        'IPNetwork_test/file.json',
        'test-data/file.json'
        'some_file/integration_DESCRIPTION.md'
        'some_file/integration_CHANGELOG.md'
        'some_file/integration_unified.md'
    ]

    @pytest.mark.parametrize("file_path", SKIPPED_FILE_PATHS)
    def test_should_file_skip_validation_positive(self, file_path):
        should_skip = tools.should_file_skip_validation(file_path)
        assert should_skip


class TestServerVersionCompare:
    V5 = "5.0.0"
    V0 = "0.0.0"
    EQUAL = 0
    LEFT_IS_LATER = 1
    RIGHT_IS_LATER = -1
    INPUTS = [
        (V0, V5, RIGHT_IS_LATER),
        (V5, V0, LEFT_IS_LATER),
        (V5, V5, EQUAL),
        ("4.5.0", "4.5", EQUAL)
    ]

    @pytest.mark.parametrize("left, right, answer", INPUTS)
    def test_server_version_compare(self, left, right, answer):
        assert server_version_compare(left, right) == answer


def test_pascal_case():
    res = tools.pascal_case("PowerShell Remoting")
    assert res == "PowerShellRemoting"
    res = tools.pascal_case("good life")
    assert res == "GoodLife"
    res = tools.pascal_case("good_life-here v2")
    assert res == "GoodLifeHereV2"


def test_capital_case():
    res = tools.capital_case("PowerShell Remoting")
    assert res == "PowerShell Remoting"
    res = tools.capital_case("good life")
    assert res == "Good Life"
    res = tools.capital_case("good_life-here v2")
    assert res == "Good_life-here V2"
    res = tools.capital_case("")
    assert res == ""


class TestPrintColor:
    def test_print_color(self, mocker):
        mocker.patch('builtins.print')

        tools.print_color('test', LOG_COLORS.GREEN)

        print_args = print.call_args[0][0]
        assert print_args == u'{}{}{}'.format(LOG_COLORS.GREEN, 'test', LOG_COLORS.NATIVE)


class TestReleaseVersion:
    def test_get_last_release(self, mocker):
        mocker.patch('demisto_sdk.commands.common.tools.run_command', return_value='1.2.3\n4.5.6\n3.2.1\n20.0.0')

        tag = get_last_release_version()

        assert tag == '20.0.0'


class TestEntityAttributes:
    @pytest.mark.parametrize('data, entity', [({'commonfields': {'id': 1}}, INTEGRATIONS_DIR),
                                              ({'typeId': 1}, LAYOUTS_DIR), ({'id': 1}, PLAYBOOKS_DIR)])
    def test_get_entity_id_by_entity_type(self, data, entity):
        assert get_entity_id_by_entity_type(data, entity) == 1

    @pytest.mark.parametrize('data, entity', [({'typeId': 'wow'}, LAYOUTS_DIR),
                                              ({'name': 'wow'}, LAYOUTS_DIR),
                                              ({'name': 'wow'}, PLAYBOOKS_DIR)])
    def test_get_entity_name_by_entity_type(self, data, entity):
        assert get_entity_name_by_entity_type(data, entity) == 'wow'


class TestGetFilesInDir:
    def test_project_dir_is_file(self):
        project_dir = 'demisto_sdk/commands/download/downloader.py'
        assert get_files_in_dir(project_dir, ['py']) == [project_dir]

    def test_not_recursive(self):
        project_dir = 'demisto_sdk/commands/download'
        files = [f'{project_dir}/__init__.py', f'{project_dir}/downloader.py', f'{project_dir}/README.md']
        assert sorted(get_files_in_dir(project_dir, ['py', 'md'], False)) == sorted(files)

    def test_recursive(self):
        integrations_dir = 'demisto_sdk/commands/download/tests/tests_env/content/Packs/TestPack/Integrations'
        integration_instance_dir = f'{integrations_dir}/TestIntegration'
        files = [f'{integration_instance_dir}/TestIntegration.py',
                 f'{integration_instance_dir}/TestIntegration_testt.py']
        assert sorted(get_files_in_dir(integrations_dir, ['py'])) == sorted(files)

    def test_recursive_pack(self):
        pack_dir = 'demisto_sdk/commands/download/tests/tests_env/content/Packs/TestPack'
        files = [f'{pack_dir}/Integrations/TestIntegration/TestIntegration.py',
                 f'{pack_dir}/Integrations/TestIntegration/TestIntegration_testt.py',
                 f'{pack_dir}/Scripts/TestScript/TestScript.py']
        assert sorted(get_files_in_dir(pack_dir, ['py'])) == sorted(files)


run_command_os_inputs = [
    ('ls', os.getcwd()),
    ('ls', Path(os.getcwd()))
]


@pytest.mark.parametrize('command, cwd', run_command_os_inputs)
def test_run_command_os(command, cwd):
    """Tests a simple command, to check if it works
    """
    stdout, stderr, return_code = run_command_os(
        command,
        cwd=cwd
    )
    assert 0 == return_code
    assert stdout
    assert not stderr


class TestGetFile:
    def test_get_ryaml(self):
        file_data = get_ryaml(SOURCE_FORMAT_INTEGRATION_COPY)
        assert file_data
        assert file_data.get('name') is not None


def test_get_latest_release_notes_text_invalid():
    """
    Given
    - Invalid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure None is returned
    """
    PATH_TO_HERE = f'{git_path()}/demisto_sdk/tests/test_files/'
    file_path = os.path.join(PATH_TO_HERE, 'empty-RN.md')
    assert get_latest_release_notes_text(file_path) is None


def test_get_release_notes_file_path_valid():
    """
    Given
    - Valid release notes path

    When
    - Running validation on release notes.

    Then
    - Ensure valid file path is returned
    """
    filepath = '/SomePack/1_1_1.md'
    assert get_release_notes_file_path(filepath) == filepath


def test_get_release_notes_file_path_invalid():
    """
    Given
    - Invalid release notes path

    When
    - Running validation on release notes.

    Then
    - Ensure None is returned
    """
    filepath = '/SomePack/1_1_1.json'
    assert get_release_notes_file_path(filepath) is None


remote_testbank = [
    ('origin  https://github.com/turbodog/content.git', False),
    ('upstream  https://github.com/demisto/content.git', True)
]


@pytest.mark.parametrize('git_value, response', remote_testbank)
def test_has_remote(mocker, git_value, response):
    """
    While: Testing if the remote upstream contains demisto/content
    Given:
      1. Origin string not containing demisto/content
      2. Upstream string containing demisto/content
    Expects:
      1. Test condition fails
      2. Test condition passes
    :param git_value: Git string from `git remotes -v`
    """
    mocker.patch('demisto_sdk.commands.common.tools.run_command', return_value=git_value)
    test_remote = has_remote_configured()
    assert response == test_remote


origin_testbank = [
    ('origin  https://github.com/turbodog/content.git', False),
    ('origin  https://github.com/demisto/content.git', True)
]


@pytest.mark.parametrize('git_value, response', origin_testbank)
def test_origin_content(mocker, git_value, response):
    """
    While: Testing if the remote origin contains demisto/content
    Given:
      1. Origin string not containing demisto/content
      2. Origin string containing demisto/content
    Expects:
      1. Test condition fails
      2. Test condition passes
    :param git_value: Git string from `git remotes -v`
    """
    mocker.patch('demisto_sdk.commands.common.tools.run_command', return_value=git_value)
    test_remote = is_origin_content_repo()
    assert response == test_remote


def test_get_ignore_pack_tests__no_pack():
    """
    Given
    - Pack that doesn't exist
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    nonexistent_pack = 'NonexistentFakeTestPack'
    ignore_test_set = get_ignore_pack_skipped_tests(nonexistent_pack)
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__no_ignore_pack(tmpdir):
    """
    Given
    - Pack doesn't have .pack-ignore file
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    fake_pack_name = 'FakeTestPack'

    # prepare repo
    repo = Repo(tmpdir)
    repo_path = Path(repo.path)
    pack = Pack(repo_path / PACKS_DIR, fake_pack_name, repo)
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # remove .pack-ignore if exists
    if os.path.exists(pack_ignore_path):
        os.remove(pack_ignore_path)

    ignore_test_set = get_ignore_pack_skipped_tests(fake_pack_name)
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__test_not_ignored(tmpdir):
    """
    Given
    - Pack have .pack-ignore file
    - There are no skipped tests in .pack-ignore
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    fake_pack_name = 'FakeTestPack'

    # prepare repo
    repo = Repo(tmpdir)
    repo_path = Path(repo.path)
    pack = Pack(repo_path / PACKS_DIR, fake_pack_name, repo)
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    open(pack_ignore_path, 'a').close()

    ignore_test_set = get_ignore_pack_skipped_tests(fake_pack_name)
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__ignore_test(tmpdir, mocker):
    """
    Given
    - Pack have .pack-ignore file
    - There are skipped tests in .pack-ignore
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns a list with the skipped tests
    """
    fake_pack_name = 'FakeTestPack'
    fake_test_name = 'FakeTestPlaybook'
    expected_id = 'sample playbook'

    # prepare repo
    repo = Repo(tmpdir)
    packs_path = Path(repo.path) / PACKS_DIR
    pack = Pack(packs_path, fake_pack_name, repo)
    test_playbook_path = packs_path / fake_pack_name / TEST_PLAYBOOKS_DIR
    test_playbook = Playbook(test_playbook_path, fake_test_name, repo, is_test_playbook=True)
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    with open(pack_ignore_path, 'a') as pack_ignore_f:
        pack_ignore_f.write("[file:TestIntegration.yml]\nignore=IN126\n\n"
                            f"[file:{test_playbook.name}]\nignore=auto-test")

    # prepare mocks
    mocker.patch.object(tools, "get_pack_ignore_file_path", return_value=pack_ignore_path)
    mocker.patch.object(os.path, "join", return_value=str(test_playbook_path / (test_playbook.name + ".yml")))

    ignore_test_set = get_ignore_pack_skipped_tests(fake_pack_name)
    assert len(ignore_test_set) == 1
    assert expected_id in ignore_test_set


def test_get_ignore_pack_tests__ignore_missing_test(tmpdir, mocker):
    """
    Given
    - Pack have .pack-ignore file
    - There are skipped tests in .pack-ignore
    - The tests are missing from the content pack
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns a list with the skipped tests
    """
    fake_pack_name = 'FakeTestPack'
    fake_test_name = 'FakeTestPlaybook.yml'

    # prepare repo
    repo = Repo(tmpdir)
    packs_path = Path(repo.path) / PACKS_DIR
    pack = Pack(packs_path, fake_pack_name, repo)
    test_playbook_path = packs_path / fake_pack_name / TEST_PLAYBOOKS_DIR
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    with open(pack_ignore_path, 'a') as pack_ignore_f:
        pack_ignore_f.write("[file:TestIntegration.yml]\nignore=IN126\n\n"
                            f"[file:{fake_test_name}]\nignore=auto-test")

    # prepare mocks
    mocker.patch.object(tools, "get_pack_ignore_file_path", return_value=pack_ignore_path)
    mocker.patch.object(os.path, "join", return_value=str(test_playbook_path / fake_test_name))

    ignore_test_set = get_ignore_pack_skipped_tests(fake_pack_name)
    assert len(ignore_test_set) == 0


@pytest.mark.parametrize(argnames="arg, expected_result",
                         argvalues=[["a1,b2,c3", ['a1', 'b2', 'c3']],
                                    ["[\"a1\",\"b2\",\"c3\"]", ["a1", "b2", "c3"]],
                                    [['a1', 'b2', 'c3'], ['a1', 'b2', 'c3']],
                                    ["", []],
                                    [[], []]
                                    ])
def test_arg_to_list(arg: Union[List[str], str], expected_result: List[str]):
    """
    Given
    - String or list of strings.
    Case a: comma-separated string.
    Case b: a string representing a list.
    Case c: python list.
    Case d: empty string.
    Case e: empty list.

    When
    - Convert given string to list of strings, for example at unify.add_contributors_support.

    Then:
    - Ensure a Python list is returned with the relevant values.
    """
    func_result = arg_to_list(arg=arg, separator=",")
    assert func_result == expected_result


V2_VALID = {"display": "integrationname v2", "name": "integrationname v2", "id": "integrationname v2"}
V2_WRONG_DISPLAY = {"display": "integrationname V2", "name": "integrationname v2", "id": "integrationname V2"}
NOT_V2_VIA_DISPLAY_NOR_NAME = {"display": "integrationname", "name": "integrationv2name", "id": "integrationv2name"}
NOT_V2_VIA_DISPLAY = {"display": "integrationname", "name": "integrationname v2", "id": "integrationv2name"}
NOT_V2_VIA_NAME = {"display": "integrationname V2", "name": "integrationname", "id": "integrationv2name"}
V2_NAME_INPUTS = [
    (V2_VALID, True),
    (V2_WRONG_DISPLAY, True),
    (NOT_V2_VIA_DISPLAY_NOR_NAME, False),
    (NOT_V2_VIA_NAME, False),
    (NOT_V2_VIA_DISPLAY, True)
]


@pytest.mark.parametrize("current, answer", V2_NAME_INPUTS)
def test_is_v2_file_via_name(current, answer):
    assert is_v2_file(current) is answer


V2_DISPLAY_INPUTS = [
    (V2_VALID, True),
    (V2_WRONG_DISPLAY, True),
    (NOT_V2_VIA_DISPLAY, False),
    (NOT_V2_VIA_NAME, True),
    (NOT_V2_VIA_DISPLAY_NOR_NAME, False)
]


@pytest.mark.parametrize("current, answer", V2_DISPLAY_INPUTS)
def test_is_v2_file_via_display(current, answer):
    assert is_v2_file(current, check_in_display=True) is answer


def test_get_to_version_with_to_version(repo):
    pack = repo.create_pack('Pack')
    integration = pack.create_integration('INT', yml={'toversion': '4.5.0'})
    with ChangeCWD(repo.path):
        to_ver = get_to_version(integration.yml.path)

        assert to_ver == '4.5.0'


def test_get_to_version_no_to_version(repo):
    pack = repo.create_pack('Pack')
    integration = pack.create_integration('INT', yml={})
    with ChangeCWD(repo.path):
        to_ver = get_to_version(integration.yml.path)

        assert to_ver == '99.99.99'


def test_get_file_displayed_name__integration(repo):
    """
    Given
    - The path to an integration.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the display field.
    """
    pack = repo.create_pack('MyPack')
    integration = pack.create_integration('MyInt')
    integration.create_default_integration()
    yml_content = integration.yml.read_dict()
    yml_content['display'] = 'MyDisplayName'
    integration.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(integration.yml.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__script(repo):
    """
    Given
    - The path to a script.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack('MyPack')
    script = pack.create_script('MyScr')
    script.create_default_script()
    yml_content = script.yml.read_dict()
    yml_content['name'] = 'MyDisplayName'
    script.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(script.yml.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__playbook(repo):
    """
    Given
    - The path to a playbook.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack('MyPack')
    playbook = pack.create_playbook('MyPlay')
    playbook.create_default_playbook()
    yml_content = playbook.yml.read_dict()
    yml_content['name'] = 'MyDisplayName'
    playbook.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(playbook.yml.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__mapper(repo):
    """
    Given
    - The path to a mapper.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack('MyPack')
    mapper = pack.create_mapper('MyMap', content=MAPPER)
    json_content = mapper.read_json_as_dict()
    json_content['name'] = 'MyDisplayName'
    mapper.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(mapper.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__old_classifier(repo):
    """
    Given
    - The path to an old classifier.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the brandName field.
    """
    pack = repo.create_pack('MyPack')
    old_classifier = pack.create_classifier('MyClas', content=OLD_CLASSIFIER)
    json_content = old_classifier.read_json_as_dict()
    json_content['brandName'] = 'MyDisplayName'
    old_classifier.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(old_classifier.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__layout(repo):
    """
    Given
    - The path to a layout.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the TypeName field.
    """
    pack = repo.create_pack('MyPack')
    layout = pack.create_layout('MyLay', content=LAYOUT)
    json_content = layout.read_json_as_dict()
    json_content['TypeName'] = 'MyDisplayName'
    layout.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(layout.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__reputation(repo):
    """
    Given
    - The path to a reputation.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the id field.
    """
    pack = repo.create_pack('MyPack')
    reputation = pack._create_json_based('MyRep', content=REPUTATION, prefix='reputation')
    json_content = reputation.read_json_as_dict()
    json_content['id'] = 'MyDisplayName'
    reputation.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(reputation.path)
        assert display_name == 'MyDisplayName'


def test_get_file_displayed_name__image(repo):
    """
    Given
    - The path to an image.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the file name.
    """
    pack = repo.create_pack('MyPack')
    integration = pack.create_integration('MyInt')
    integration.create_default_integration()
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(integration.image.path)
        assert display_name == os.path.basename(integration.image.rel_path)


def test_get_pack_metadata(repo):
    """
    Given
    - The path to some file in the repo.

    When
    - Running get_pack_metadata.

    Then:
    - Ensure the returned pack metadata of the file's pack.
    """
    metadata_json = {"name": "MyPack", "support": "xsoar", "currentVersion": "1.1.0"}

    pack = repo.create_pack('MyPack')
    pack_metadata = pack.pack_metadata
    pack_metadata.update(metadata_json)

    result = get_pack_metadata(pack.path)

    assert metadata_json == result


def test_get_last_remote_release_version(requests_mock):
    """
    When
    - Get latest release tag from remote pypi api

    Then:
    - Ensure the returned version is as expected
    """
    os.environ['DEMISTO_SDK_SKIP_VERSION_CHECK'] = ''
    os.environ['CI'] = ''
    expected_version = '1.3.8'
    requests_mock.get(r"https://pypi.org/pypi/demisto-sdk/json", json={'info': {'version': expected_version}})
    assert get_last_remote_release_version() == expected_version

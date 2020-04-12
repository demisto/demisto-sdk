import glob
import os

import pytest
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (PACKS_PLAYBOOK_YML_REGEX,
                                                   PACKS_TEST_PLAYBOOKS_REGEX)
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import (LOG_COLORS,
                                               filter_packagify_changes,
                                               find_type, get_dict_from_file,
                                               get_last_release_version,
                                               get_matching_regex,
                                               server_version_compare)
from demisto_sdk.tests.constants_test import (INDICATORFIELD_EXTRA_FIELDS,
                                              VALID_DASHBOARD_PATH,
                                              VALID_INCIDENT_FIELD_PATH,
                                              VALID_INCIDENT_TYPE_PATH,
                                              VALID_INTEGRATION_TEST_PATH,
                                              VALID_LAYOUT_PATH, VALID_MD,
                                              VALID_PLAYBOOK_ID_PATH,
                                              VALID_REPUTATION_FILE,
                                              VALID_SCRIPT_PATH,
                                              VALID_WIDGET_PATH)


class TestGenericFunctions:
    PATH_TO_HERE = f'{git_path()}/demisto_sdk/tests/test_files/'
    FILE_PATHS = [
        (os.path.join(PATH_TO_HERE, 'fake_integration.yml'), tools.get_yaml),
        (os.path.join(PATH_TO_HERE, 'fake_json.json'), tools.get_json)
    ]

    @pytest.mark.parametrize('file_path, func', FILE_PATHS)
    def test_get_file(self, file_path, func):
        assert func(file_path)

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
        (VALID_DASHBOARD_PATH, 'dashboard'),
        (VALID_INCIDENT_FIELD_PATH, 'incidentfield'),
        (VALID_INCIDENT_TYPE_PATH, 'incidenttype'),
        (INDICATORFIELD_EXTRA_FIELDS, 'indicatorfield'),
        (VALID_INTEGRATION_TEST_PATH, 'integration'),
        (VALID_LAYOUT_PATH, 'layout'),
        (VALID_PLAYBOOK_ID_PATH, 'playbook'),
        (VALID_REPUTATION_FILE, 'reputation'),
        (VALID_SCRIPT_PATH, 'script'),
        (VALID_WIDGET_PATH, 'widget'),
        ('', '')
    ]

    @pytest.mark.parametrize('path, _type', data_test_find_type)
    def test_find_type(self, path, _type):
        output = find_type(str(path))
        assert output == _type, f'find_type({path}) returns: {output} instead {_type}'

    test_path_md = [
        VALID_MD
    ]

    @pytest.mark.parametrize('path', test_path_md)
    def test_filter_packagify_changes(self, path):
        modified, added, removed = filter_packagify_changes(modified_files=[], added_files=[], removed_files=[path])
        assert modified == []
        assert added == set()
        assert removed == [VALID_MD]


class TestGetRemoteFile:
    def test_get_remote_file_sanity(self):
        hello_world_yml = tools.get_remote_file('Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml')
        assert hello_world_yml
        assert hello_world_yml['commonfields']['id'] == 'HelloWorld'

    def test_get_remote_file_origin(self):
        hello_world_yml = tools.get_remote_file('Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml', 'master')
        assert hello_world_yml
        assert hello_world_yml['commonfields']['id'] == 'HelloWorld'

    def test_get_remote_file_tag(self):
        gmail_yml = tools.get_remote_file('Integrations/Gmail/Gmail.yml', '19.10.0')
        assert gmail_yml
        assert gmail_yml['commonfields']['id'] == 'Gmail'

    def test_get_remote_file_origin_tag(self):
        gmail_yml = tools.get_remote_file('Integrations/Gmail/Gmail.yml', 'origin/19.10.0')
        assert gmail_yml
        assert gmail_yml['commonfields']['id'] == 'Gmail'

    def test_get_remote_file_invalid(self):
        invalid_yml = tools.get_remote_file('Integrations/File/File.yml', '19.10.0')
        assert not invalid_yml

    def test_get_remote_file_invalid_branch(self):
        invalid_yml = tools.get_remote_file('Integrations/Gmail/Gmail.yml', 'NoSuchBranch')
        assert not invalid_yml

    def test_get_remote_file_invalid_origin_branch(self):
        invalid_yml = tools.get_remote_file('Integrations/Gmail/Gmail.yml', 'origin/NoSuchBranch')
        assert not invalid_yml

    def test_get_remote_md_file_origin(self):
        hello_world_readme = tools.get_remote_file('Packs/HelloWorld/README.md', 'master')
        assert hello_world_readme == {}


class TestGetMatchingRegex:
    INPUTS = [
        ('Packs/XDR/Playbooks/XDR.yml', [PACKS_PLAYBOOK_YML_REGEX, PACKS_TEST_PLAYBOOKS_REGEX],
         PACKS_PLAYBOOK_YML_REGEX),
        ('Packs/XDR/NoMatch/XDR.yml', [PACKS_PLAYBOOK_YML_REGEX, PACKS_TEST_PLAYBOOKS_REGEX], False)
    ]

    @pytest.mark.parametrize("string_to_match, regexes, answer", INPUTS)
    def test_get_matching_regex(self, string_to_match, regexes, answer):
        assert get_matching_regex(string_to_match, regexes) == answer


class TestServerVersionCompare:
    V5 = "5.0.0"
    V0 = "0.0.0"
    EQUAL = 0
    LEFT_IS_LATER = 1
    RIGHT_IS_LATER = -1
    INPUTS = [
        (V0, V5, RIGHT_IS_LATER),
        (V5, V0, LEFT_IS_LATER),
        (V5, V5, EQUAL)
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

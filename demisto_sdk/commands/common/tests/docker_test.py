import os

import mock
import pytest

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from TestSuite.test_tools import ChangeCWD

RETURN_ERROR_TARGET = 'GetDockerImageLatestTag.return_error'

MOCK_TAG_LIST = [{
    u'last_updated': u'2019-10-23T09:13:30.84299Z',
    u'name': u'1.0.0.2876',
    u'repository': 7863337,
    u'creator': 4824052,
    u'image_id': None,
    u'v2': True,
    u'last_updater_username': u'containersci',
    u'last_updater': 4824052,
    u'images': [{
        u'features': u'',
        u'os_features': u'',
        u'variant': None,
        u'os_version': None,
        u'architecture': u'amd64',
        u'os': u'linux',
        u'digest': u'DIGEST',
        u'size': 79019268
    }],
    u'full_size': 79019268,
    u'id': 73482510
}, {
    u'last_updated': u'2019-10-16T06:47:29.631011Z',
    u'name': u'1.0.0.2689',
    u'repository': 7863337,
    u'creator': 4824052,
    u'image_id': None,
    u'v2': True,
    u'last_updater_username': u'containersci',
    u'last_updater': 4824052,
    u'images': [{
        u'features': u'',
        u'os_features': u'',
        u'variant': None,
        u'os_version': None,
        u'architecture': u'amd64',
        u'os': u'linux',
        u'digest': u'DIGEST',
        u'size': 77021619
    }],
    u'full_size': 77021619,
    u'id': 72714981
}]

FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
TEST_INTEGRATION_FILE = os.path.join(FILES_PATH, 'fake_integration.yml')
TEST_SCRIPT_FILE = os.path.join(FILES_PATH, 'fake-script.yml')


def mock_docker_image_validator():
    with mock.patch.object(DockerImageValidator, '__init__', lambda x, y, z, w: None):
        docker_image_validator = DockerImageValidator(None, None, None)
        docker_image_validator.yml_file = {}
        docker_image_validator.file_path = "PATH"
        docker_image_validator.ignored_errors = {}
        docker_image_validator.checked_files = set()
        docker_image_validator.suppress_print = False
        docker_image_validator.json_file_path = ''
        return docker_image_validator


class TestDockerImage:
    # demisto/python-deb doesn't contain a latest tag
    @pytest.mark.parametrize('image', ['python', 'python-deb', 'python3', 'python3-deb'])
    def test_get_docker_image_latest_tag(self, image):
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = '1.0.3'
        docker_image_validator.docker_image_name = 'demisto/python'
        tag = docker_image_validator.get_docker_image_latest_tag(docker_image_name=f'demisto/{image}',
                                                                 yml_docker_image='')
        # current latest tag is 2.7.16.2728 or 3.7.2.2728 disable-secrets-detection
        assert int(tag.split('.')[3]) >= 2728

    data_test_none_demisto_docker = [
        ('blabla/google-api-py3', '1.0.0.5992', ''),
        ('unknownvuser/v-alpine', 'at_v_commit-b17ade1257cfe086c1742c91deeb6c606037b893', ''),
        ('feedparser', 'latest', '')
    ]

    @pytest.mark.parametrize('docker, docker_tag, expected_output', data_test_none_demisto_docker)
    def test_none_demisto_docker(self, docker, docker_tag, expected_output):
        docker_image_validator = mock_docker_image_validator()
        assert docker_image_validator.get_docker_image_latest_tag(docker_image_name=docker,
                                                                  yml_docker_image='{}:{}'.format(docker,
                                                                                                  docker_tag)) == expected_output

    # disable-secrets-detection-start
    def test_get_docker_image_from_yml(self):
        docker_validator = mock_docker_image_validator()
        docker_validator.yml_file = get_yaml(TEST_INTEGRATION_FILE)
        docker_validator.is_integration = True
        docker_image = docker_validator.get_docker_image_from_yml()
        assert docker_image == "demisto/pyjwt:1.0"
        # Test script case
        docker_validator.yml_file = get_yaml(TEST_SCRIPT_FILE)
        docker_validator.is_integration = False
        docker_image = docker_validator.get_docker_image_from_yml()
        assert docker_image == "demisto/stix2:1.0.0.204"

    # disable-secrets-detection-end

    def test_lexical_find_latest_tag(self):
        tag_list = ["2.0.2000", "2.1.2700", "2.1.373", "latest"]
        tag = DockerImageValidator.lexical_find_latest_tag(tag_list)
        assert tag == "2.1.2700"

    def test_find_latest_tag_by_date(self):
        tag = DockerImageValidator.find_latest_tag_by_date(MOCK_TAG_LIST)
        assert tag == "1.0.0.2876"

    @pytest.mark.parametrize('www_auth, expected', [('AAArealm="2",service="3"AAA', ('2', '3')), ('bbb', ())])
    def test_parse_www_auth(self, www_auth, expected):
        assert expected == DockerImageValidator.parse_www_auth(www_auth)

    # disable-secrets-detection-start
    @pytest.mark.parametrize('input_tags, output_tags',
                             [(['1.2.3.0', '4.5.6.0', '7.8.9.0'], ['4.5.6.0', '1.2.3.0', '7.8.9.0']),
                              (['1.2.3.0', '4.a.6.0', '7.8.9.0'], ['7.8.9.0', '1.2.3.0']),
                              (['aaa', 'bbb'], []), (['6a.7.6'], []), (['6..4'], [])])
    # disable-secrets-detection-end
    def test_clear_non_numbered_tags(self, input_tags, output_tags):
        assert sorted(output_tags) == sorted(DockerImageValidator.clear_non_numbered_tags(input_tags))

    # disable-secrets-detection-start
    def test_parse_docker_image(self):
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = '1.0.3'
        docker_image_validator.docker_image_name = 'demisto/python'
        assert 'demisto/python', '1.3-alpine' == docker_image_validator.parse_docker_image(
            docker_image='demisto/python:1.3-alpine')
        assert 'demisto/slack', '1.2.3.4' == docker_image_validator.parse_docker_image(
            docker_image='demisto/slack:1.2.3.4')
        assert 'demisto/python', '' == docker_image_validator.parse_docker_image(
            docker_image='demisto/python/1.2.3.4')
        assert ('', '') == docker_image_validator.parse_docker_image(docker_image='blah/blah:1.2.3.4')

    # disable-secrets-detection-end
    def test_is_docker_image_latest_tag_with_default_image(self):
        """
        Given
        - The default docker image - 'demisto/python:1.3-alpine'

        When
        - The most updated docker image in docker-hub is '1.0.3'

        Then
        -  If the docker image is numeric and the most update one, it is Valid
        -  If the docker image is not numeric and labeled "latest", it is Invalid
       """
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.code_type = 'python'
        docker_image_validator.docker_image_latest_tag = '1.0.3'
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.is_latest_tag = True
        docker_image_validator.is_modified_file = False
        docker_image_validator.docker_image_tag = '1.3-alpine'
        docker_image_validator.is_valid = True
        docker_image_validator.yml_docker_image = 'demisto/python:1.3-alpine'

        assert docker_image_validator.is_docker_image_latest_tag() is False
        assert docker_image_validator.is_latest_tag is False
        assert docker_image_validator.is_docker_image_valid() is False

    def test_is_docker_image_latest_tag_with_tag_labeled_latest(self):
        """
        Given
        - A docker image with "latest" as tag

        When
        - The most updated docker image in docker-hub is '1.0.3'

        Then
        -  If the docker image is numeric and the most update one, it is Valid
        -  If the docker image is not numeric and labeled "latest", it is Invalid
       """
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = 'latest'
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.code_type = 'python'
        docker_image_validator.is_latest_tag = True
        docker_image_validator.is_valid = True
        docker_image_validator.docker_image_tag = 'latest'
        docker_image_validator.yml_docker_image = 'demisto/python:latest'

        assert docker_image_validator.is_docker_image_latest_tag() is False
        assert docker_image_validator.is_latest_tag is False
        assert docker_image_validator.is_docker_image_valid() is False

    def test_is_docker_image_latest_tag_with_latest_tag(self):
        """
       Given
       - A docker image with '1.0.3' as tag

       When
       - The most updated docker image in docker-hub is '1.0.3'

       Then
       -  If the docker image is numeric and the most update one, it is Valid
       -  If the docker image is not numeric and labeled "latest", it is Invalid
      """
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = '1.0.3'
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.code_type = 'python'
        docker_image_validator.is_latest_tag = True
        docker_image_validator.is_valid = True
        docker_image_validator.docker_image_tag = '1.0.3'
        docker_image_validator.yml_docker_image = 'demisto/python:1.0.3'

        assert docker_image_validator.is_docker_image_latest_tag() is True
        assert docker_image_validator.is_latest_tag is True
        assert docker_image_validator.is_docker_image_valid() is True

    def test_is_docker_image_latest_tag_with_numeric_but_not_most_updated(self):
        """
       Given
       - A docker image with '1.0.2' as tag

       When
       - The most updated docker image in docker-hub is '1.0.3'

       Then
       -  If the docker image is numeric and the most update one, it is Valid
       -  If the docker image is not numeric and labeled "latest", it is Invalid
       - If the docker image is not the most updated one it is invalid
      """
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = '1.0.3'
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.code_type = 'python'
        docker_image_validator.is_latest_tag = True
        docker_image_validator.docker_image_tag = '1.0.2'
        docker_image_validator.is_valid = True
        docker_image_validator.yml_docker_image = 'demisto/python:1.0.2'
        docker_image_validator.is_iron_bank = False
        assert docker_image_validator.is_docker_image_latest_tag() is False
        assert docker_image_validator.is_latest_tag is False
        assert docker_image_validator.is_docker_image_valid() is False

    def test_is_docker_image_latest_tag_without_tag(self):
        """
       Given
       - A latest docker image has an empty tag

       When
       - The most updated docker image in docker-hub is '1.0.3'

       Then
       -  If the docker image is numeric and the most update one, it is Valid
       -  If the docker image is not numeric and labeled "latest", it is Invalid
      """
        docker_image_validator = mock_docker_image_validator()
        docker_image_validator.docker_image_latest_tag = ''
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.code_type = 'python'
        docker_image_validator.is_latest_tag = True
        docker_image_validator.docker_image_tag = '1.0.2'
        docker_image_validator.is_valid = True
        docker_image_validator.yml_docker_image = 'demisto/python:1.0.2'

        assert docker_image_validator.is_docker_image_latest_tag() is False
        assert docker_image_validator.is_latest_tag is False
        assert docker_image_validator.is_docker_image_valid() is False

    @pytest.mark.parametrize('code_type, expected', [('javascript', True), ('python', False)])
    def test_no_dockerimage_in_yml_file(self, code_type, expected):
        """
        Given
        - A yml file (integration/script) written in [javascript, python] with no dockerimage.

        When
        - Running DockerImageValidator

        Then
        -  If the integration / script is written in javascript, it is valid
        -  If the integration / script is written in python, it is invalid
        """
        docker_image_validator = mock_docker_image_validator()

        docker_image_validator.is_valid = True
        docker_image_validator.is_latest_tag = True
        docker_image_validator.yml_docker_image = None
        docker_image_validator.docker_image_latest_tag = None
        docker_image_validator.docker_image_name = None
        docker_image_validator.docker_image_tag = None
        docker_image_validator.code_type = code_type

        assert docker_image_validator.is_docker_image_valid() is expected

    @pytest.mark.parametrize('code_type', ['javascript', 'python'])
    def test_dockerimage_in_yml_file(self, code_type):
        """
        Given
        - A yml file (integration/script) written in [javascript, python] with correct dockerimage.

        When
        - Running DockerImageValidator

        Then
        -  If the integration / script is written in javascript, it is valid
        -  If the integration / script is written in python, it is valid
        """
        docker_image_validator = mock_docker_image_validator()

        docker_image_validator.is_valid = True
        docker_image_validator.is_latest_tag = True
        docker_image_validator.yml_docker_image = 'demisto/python:1.0.2'
        docker_image_validator.docker_image_latest_tag = '1.0.2'
        docker_image_validator.docker_image_name = 'demisto/python'
        docker_image_validator.docker_image_tag = '1.0.2'
        docker_image_validator.code_type = code_type

        assert docker_image_validator.is_docker_image_valid() is True

    def test_non_existing_docker(self, integration, capsys, requests_mock, mocker):
        docker_image = 'demisto/nonexistingdocker:1.4.0'
        integration.yml.write_dict(
            {
                'script': {
                    'subtype': 'python3',
                    'type': 'python',
                    'dockerimage': docker_image
                }
            }
        )
        error, code = Errors.non_existing_docker(docker_image)
        mocker.patch.object(DockerImageValidator, 'docker_auth', return_value='auth')
        requests_mock.get(
            "https://hub.docker.com/v2/repositories/demisto/nonexistingdocker/tags",
            json={'results': []}
        )
        with ChangeCWD(integration.repo_path):
            validator = DockerImageValidator(integration.yml.path, True, True)
            assert validator.is_docker_image_valid() is False
            captured = capsys.readouterr()
            assert validator.is_valid is False
            assert error in captured.out
            assert code in captured.out

    class TestIronBankDockerParse:
        def test_get_latest_commit(self, integration, requests_mock):
            """
            Given:
                An example existing project with successful commits in master in Iron Bank.
            When:
                Validating docker image of Iron Bank pack.
            Then:
                Validates we extract correctly the commit id.
            """
            api_url = 'https://repo1.dso.mil/api/v4/projects/dsop%2Fopensource%2Fpalo-alto-networks%2Ftest%2Ftest_project/pipelines'
            requests_mock.get(
                api_url,
                json=[{'id': 433333,
                       'project_id': 7070,
                       'sha': 'sha_1',
                       'ref': 'master',
                       'status': 'success',
                       'created_at': '2021-08-19T09:18:35.547Z',
                       'updated_at': '2021-08-19T09:38:21.743Z',
                       'web_url': 'https://repo1.dso.mil/dsop/opensource/palo-alto-networks/test/test_project/-/pipelines/433333'},
                      {'id': 432507,
                       'project_id': 7070,
                       'sha': 'sha_2',
                       'ref': 'master',
                       'status': 'success',
                       'created_at': '2021-08-18T22:19:19.843Z',
                       'updated_at': '2021-08-18T22:40:29.950Z',
                       'web_url': 'https://repo1.dso.mil/dsop/opensource/palo-alto-networks/test/test_project/-/pipelines/432507'}]
            )

            DockerImageValidator.file_path = integration.yml.path
            DockerImageValidator.is_iron_bank = True
            docker_image_name = 'test/test_project:1.0.2'
            DockerImageValidator.yml_docker_image = docker_image_name
            res = DockerImageValidator._get_latest_commit(api_url, docker_image_name)
            assert 'sha_1' == res

        FAIL_CASES_GET_COMMIT = [
            ([], 200,
             'The docker image in your integration/script does not have a tag in Iron Bank. '
             'Please create or update to an updated versioned image In Iron Bank.'),
            ({}, 404,
             'The docker image in your integration/script cannot be found in Iron Bank. '
             'Please create image test/test_project:1.0.2 In Iron Bank.'),
        ]

        @pytest.mark.parametrize('mock_results, mocked_status, expected', FAIL_CASES_GET_COMMIT)
        def test_get_latest_commit_fails(self, mocker, integration, requests_mock,
                                         mock_results, mocked_status, expected):
            """
            Given:
                - A project with no successful commit in master in Iron Bank.
                - A project that does not exists in Iron Bank.
            When:
                Validating docker image of Iron Bank pack.
            Then:
                Validates we show the correct error.
            """
            api_url = 'https://repo1.dso.mil/api/v4/projects/dsop%2Fopensource%2Fpalo-alto-networks%2Ftest%2Ftest_project/pipelines'
            requests_mock.get(
                api_url,
                status_code=mocked_status,
                json=mock_results
            )

            DockerImageValidator.is_iron_bank = True
            docker_image_name = 'test/test_project:1.0.2'
            DockerImageValidator.yml_docker_image = docker_image_name
            DockerImageValidator.file_path = integration.yml.path

            with pytest.raises(Exception) as e:
                DockerImageValidator._get_latest_commit(api_url, docker_image_name)

            assert str(e.value) == expected

        def test_get_manifest_from_commit(self, integration, requests_mock):
            """
            Given:
                An example existing commit with successful commits in master with Manifest file in Iron Bank.
            When:
                Validating docker image of Iron Bank pack.
            Then:
                Validates we send the correct request to Iron Bank.
            """
            manifest_url = 'https://repo1.dso.mil/api/v4/projects/dsop%2Fopensource%2Fpalo-alto-networks%2Ftest%2F'\
                           'test_project/repository/files/hardening_manifest.yaml/raw'
            request_mock = requests_mock.get(
                manifest_url,
                text="""apiVersion: v1\nname: opensource/palo-alto-networks/test/test_project\ntags:\n- 1.0.1.23955\n"""
            )

            DockerImageValidator.file_path = integration.yml.path
            DockerImageValidator.is_iron_bank = True
            docker_image_name = 'test/test_project:1.0.2'
            DockerImageValidator.yml_docker_image = docker_image_name
            DockerImageValidator._get_manifest_from_commit(manifest_url, 'sha1')
            assert request_mock.last_request.query == 'ref=sha1'
            assert request_mock.last_request.path == '/api/v4/projects/dsop%2fopensource%2fpalo-alto-networks%2f' \
                                                     'test%2ftest_project/repository/files/hardening_manifest.yaml/raw'

        FAIL_CASES_GET_MANIFEST = [
            ('', 404,
             'Missing manifest file in the latest successful commit.'),
        ]

        @pytest.mark.parametrize('mock_results, mocked_status, expected', FAIL_CASES_GET_MANIFEST)
        def test_get_manifest_from_commit_fails(self, mocker, integration, requests_mock,
                                                mock_results, mocked_status, expected):
            """
            Given:
                - A project without manifest file in master in Iron Bank.
            When:
                Validating docker image of Iron Bank pack.
            Then:
                Validates we show the correct error.
            """
            manifest_url = 'https://repo1.dso.mil/api/v4/projects/dsop%2Fopensource%2Fpalo-alto-networks%2Ftest%2F' \
                           'test_project/repository/files/hardening_manifest.yaml/raw'
            requests_mock.get(
                manifest_url,
                status_code=mocked_status,
                text=mock_results
            )

            DockerImageValidator.is_iron_bank = True
            docker_image_name = 'test/test_project:1.0.2'
            DockerImageValidator.yml_docker_image = docker_image_name
            DockerImageValidator.file_path = integration.yml.path
            with pytest.raises(Exception) as e:
                DockerImageValidator._get_manifest_from_commit(manifest_url, 'sha1')
            assert str(e.value) == expected

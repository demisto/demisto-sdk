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

        assert docker_image_validator.is_docker_image_latest_tag() is False
        assert docker_image_validator.is_latest_tag is False
        assert docker_image_validator.is_docker_image_valid() is False

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

    def test_docker_image_does_not_exist_in_yml_file(self, integration):
        """
        Given
        - An integration/script yml file.

        When
        - The dockerimage key is not set

        Then
        - Ensure the YML file is invalid.
        - Ensure the resulting error messages are correctly formatted.
        - Ensure the error code is 'DO108'.
        """
        integration.yml.write_dict(
            {
                'script': {
                    'subtype': 'python3',
                    'type': 'python'
                }
            }
        )
        error, code = Errors.docker_image_does_not_exist_in_yml_file(integration.yml.path)

        with ChangeCWD(integration.repo_path):
            validator = DockerImageValidator(integration.yml.path, True, True)
            assert validator.is_docker_image_valid() is False
            assert validator.is_valid is False
            assert 'The docker image does not exist in the yml file' in error
            assert code == 'DO108'

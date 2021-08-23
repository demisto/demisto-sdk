import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

import requests
from pkg_resources import parse_version

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_yaml

# disable insecure warnings
requests.packages.urllib3.disable_warnings()

ACCEPT_HEADER = {
    'Accept': 'application/json, '
              'application/vnd.docker.distribution.manifest.v2+json, '
              'application/vnd.docker.distribution.manifest.list.v2+json'
}

# use 10 seconds timeout for requests
TIMEOUT = 10
DEFAULT_REGISTRY = 'registry-1.docker.io'


class DockerImageValidator(BaseValidator):

    def __init__(self, yml_file_path, is_modified_file, is_integration, ignored_errors=None, print_as_warnings=False,
                 suppress_print: bool = False, json_file_path: Optional[str] = None, is_iron_bank:bool = False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.is_valid = True
        self.is_modified_file = is_modified_file
        self.is_integration = is_integration
        self.file_path = yml_file_path
        self.yml_file = get_yaml(yml_file_path)
        self.py_version = self.get_python_version()
        self.code_type = self.get_code_type()
        self.yml_docker_image = self.get_docker_image_from_yml()
        self.from_version = self.yml_file.get('fromversion', '0')
        self.docker_image_name, self.docker_image_tag = self.parse_docker_image(self.yml_docker_image)
        self.is_latest_tag = True
        self.is_iron_bank = is_iron_bank
        self.docker_image_latest_tag = self.get_docker_image_latest_tag(self.docker_image_name, self.yml_docker_image,
                                                                        self.is_iron_bank)

    def is_docker_image_valid(self):
        # javascript code should not check docker
        if self.code_type == 'javascript':
            return True

        if not self.yml_docker_image:
            error_message, error_code = Errors.dockerimage_not_in_yml_file(self.file_path)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False

        if not self.docker_image_latest_tag:
            error_message, error_code = Errors.non_existing_docker(self.yml_docker_image)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False

        elif not self.is_docker_image_latest_tag():
            self.is_valid = False

        return self.is_valid

    def is_docker_image_latest_tag(self):
        if 'demisto/python:1.3-alpine' == f'{self.docker_image_name}:{self.docker_image_tag}':
            # the docker image is the default one
            error_message, error_code = Errors.default_docker_error()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_latest_tag = False

            return self.is_latest_tag

        # ignore tag or non-demisto docker issues
        if self.docker_image_latest_tag == "no-tag-required":
            return self.is_latest_tag

        if not self.docker_image_name or not self.docker_image_latest_tag:
            # If the docker image isn't in the format we expect it to be or we failed fetching the tag
            # We don't want to print any error msgs to user because they have already been printed
            # see parse_docker_image for the errors
            self.is_latest_tag = False
            return self.is_latest_tag

        if self.docker_image_latest_tag != self.docker_image_tag:
            # If docker image tag is not the most updated one that exists in docker-hub
            error_message, error_code = Errors.docker_not_on_the_latest_tag(self.docker_image_tag,
                                                                            self.docker_image_latest_tag,
                                                                            self.is_iron_bank)
            suggested_fix = Errors.suggest_docker_fix(self.docker_image_name, self.file_path, self.is_iron_bank)
            if self.handle_error(error_message, error_code, file_path=self.file_path, suggested_fix=suggested_fix):
                self.is_latest_tag = False

            else:
                # if this error is ignored - do print it as a warning
                self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)

        # the most updated tag should be numeric and not labeled "latest"
        if self.docker_image_latest_tag == "latest":
            error_message, error_code = Errors.latest_docker_error(self.docker_image_tag, self.docker_image_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_latest_tag = False

        return self.is_latest_tag

    def get_code_type(self):
        if self.is_integration:
            code_type = self.yml_file.get('script').get('type', 'python')
        else:
            code_type = self.yml_file.get('type', 'python')
        return code_type

    def get_python_version(self):
        if self.is_integration:
            python_version = self.yml_file.get('script').get('subtype', 'python2')
        else:
            python_version = self.yml_file.get('subtype', 'python2')
        return python_version

    def get_docker_image_from_yml(self):
        if self.is_integration:
            docker_image = self.yml_file.get('script').get('dockerimage', '')
        else:
            docker_image = self.yml_file.get('dockerimage', '')
        return docker_image

    @staticmethod
    def parse_www_auth(www_auth):
        """Parse realm and service from www-authenticate string of the form:
        Bearer realm="https://auth.docker.io/token",service="registry.docker.io"

        :param www_auth: www-authenticate header value
        :type www_auth: string
        """
        match = re.match(r'.*realm="(.+)",service="(.+)".*', www_auth, re.IGNORECASE)
        if not match:
            return ()
        return match.groups()

    @staticmethod
    def docker_auth(image_name, verify_ssl=True, registry=DEFAULT_REGISTRY):
        """
        Authenticate to the docker service. Return an authentication token if authentication is required.
        """
        res = requests.get(
            'https://{}/v2/'.format(registry),
            headers=ACCEPT_HEADER,
            timeout=TIMEOUT,
            verify=verify_ssl
        )
        if res.status_code == 401:  # need to authenticate
            # defaults in case we fail for some reason
            realm = 'https://auth.docker.io/token'
            service = 'registry.docker.io'
            # Should contain header: Www-Authenticate
            www_auth = res.headers.get('www-authenticate')
            if www_auth:
                parse_auth = DockerImageValidator.parse_www_auth(www_auth)
                if parse_auth:
                    realm, service = parse_auth
            params = {
                'scope': 'repository:{}:pull'.format(image_name),
                'service': service
            }
            res = requests.get(
                url=realm,
                params=params,
                headers=ACCEPT_HEADER,
                timeout=TIMEOUT,
                verify=verify_ssl
            )
            res.raise_for_status()
            res_json = res.json()
            return res_json.get('token')
        else:
            res.raise_for_status()
            return None

    @staticmethod
    def clear_non_numbered_tags(tags):
        """Clears a given tags list to only keep numbered tags

        Args:
            tags(list): list of docker image tag names - ordered in lexical order

        Returns:
            a tag list with only numbered tags
        """
        return [tag for tag in tags if re.match(r'^(?:\d+\.)*\d+$', tag) is not None]

    @staticmethod
    def lexical_find_latest_tag(tags):
        """Will return the latest numeric docker image tag if possible - otherwise will return the last lexical tag.

        for example for the tag list: [2.0.2000, 2.1.2700 2.1.373, latest], will return 2.1.2700

        Args:
            tags(list): list of docker image tag names - ordered in lexical order
        """

        only_numbered_tags = DockerImageValidator.clear_non_numbered_tags(tags)

        if len(only_numbered_tags) == 0:
            return tags[-1]

        max_tag = only_numbered_tags[0]

        for num_tag in only_numbered_tags:
            if parse_version(max_tag) < parse_version(num_tag):
                max_tag = num_tag

        return max_tag

    @staticmethod
    def find_latest_tag_by_date(tags: list) -> str:
        """Get the latest tags by datetime comparison.
        Args:
            tags(list): List of dictionaries representing the docker image tags

        Returns:
            The last updated docker image tag name
        """
        latest_tag_name = 'latest'
        latest_tag_date = datetime.now() - timedelta(days=400000)
        for tag in tags:
            tag_date = datetime.strptime(tag.get('last_updated'), '%Y-%m-%dT%H:%M:%S.%fZ')
            if tag_date >= latest_tag_date and tag.get('name') != 'latest':
                latest_tag_date = tag_date
                latest_tag_name = tag.get('name')
        return latest_tag_name

    @staticmethod
    @lru_cache(256)
    def get_docker_image_latest_tag_request(docker_image_name: str) -> str:
        """
        Get the latest tag for a docker image by request to docker hub.
        Args:
            docker_image_name: The docker image name.

        Returns:
            The latest tag for the docker image.
        """
        tag = ''
        auth_token = DockerImageValidator.docker_auth(docker_image_name, False, DEFAULT_REGISTRY)
        headers = ACCEPT_HEADER.copy()
        if auth_token:
            headers['Authorization'] = 'Bearer {}'.format(auth_token)
        # first try to get the docker image tags using normal http request
        res = requests.get(
            url='https://hub.docker.com/v2/repositories/{}/tags'.format(docker_image_name),
            verify=False,
            timeout=TIMEOUT,
        )
        if res.status_code == 200:
            tags = res.json().get('results', [])
            # if http request successful find the latest tag by date in the response
            if tags:
                tag = DockerImageValidator.find_latest_tag_by_date(tags)

        else:
            # if http request did not succeed than get tags using the API.
            # See: https://docs.docker.com/registry/spec/api/#listing-image-tags
            res = requests.get(
                'https://{}/v2/{}/tags/list'.format(DEFAULT_REGISTRY, docker_image_name),
                headers=headers,
                timeout=TIMEOUT,
                verify=False
            )
            res.raise_for_status()
            # the API returns tags in lexical order with no date info - so try an get the numeric highest tag
            tags = res.json().get('tags', [])
            if tags:
                tag = DockerImageValidator.lexical_find_latest_tag(tags)
        return tag

    def get_docker_image_latest_tag(self, docker_image_name, yml_docker_image, is_iron_bank=False):
        """Returns the docker image latest tag of the given docker image

        Args:
            docker_image_name: The name of the docker image
            yml_docker_image: The docker image as it appears in the yml file

        Returns:
            The last updated docker image tag
        """
        if yml_docker_image:
            if not yml_docker_image.startswith('demisto/'):
                error_message, error_code = Errors.not_demisto_docker()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return ''
                return "no-tag-required"
        try:
            if is_iron_bank:
                return self.get_docker_image_latest_tag_from_iron_bank_request(docker_image_name)
            else:
                return self.get_docker_image_latest_tag_request(docker_image_name)
        except (requests.exceptions.RequestException, Exception):
            if not docker_image_name:
                docker_image_name = yml_docker_image
            error_message, error_code = Errors.docker_tag_not_fetched(docker_image_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return ''

            return "no-tag-required"

    def parse_docker_image(self, docker_image):
        """Verify that the docker image is of demisto format & parse the name and tag

        Args:
            docker_image: String representation of the docker image name and tag

        Returns:
            The name and the tag of the docker image
        """
        if docker_image:
            tag = ''
            image = ''
            try:
                image_regex = re.findall(r'(demisto\/.+)', docker_image, re.IGNORECASE)
                if image_regex:
                    image = image_regex[0]
                if ':' in image:
                    image_split = image.split(':')
                    image = image_split[0]
                    tag = image_split[1]
                else:
                    error_message, error_code = Errors.no_docker_tag(docker_image)
                    self.handle_error(error_message, error_code, file_path=self.file_path)

            except IndexError:
                error_message, error_code = Errors.docker_not_formatted_correctly(docker_image)
                self.handle_error(error_message, error_code, file_path=self.file_path)

            return image, tag
        else:
            if self.py_version == 'python2':
                # If the yml file has no docker image we provide a default one with numeric tag
                return 'demisto/python', self.get_docker_image_latest_tag('demisto/python', None)
            else:
                return 'demisto/python3', self.get_docker_image_latest_tag('demisto/python3', None)

    @staticmethod
    def get_docker_image_latest_tag_from_iron_bank_request(docker_image_name):
        """
        Get the latest tag for a docker image by request to Iron Bank Repo.
        Args:
            docker_image_name: The docker image name.

        Returns:
            The latest tag for the docker image.
        """
        project_name = docker_image_name.replace('demisto/', '')
        api_url = 'https://repo1.dso.mil/api/v4/projects/dsop%2Fopensource%2Fpalo-alto-networks%2Fdemisto%2F'
        commits_url = api_url + f'{project_name}/pipelines'
        manifest_url = api_url + f'{project_name}/repository/files/hardening_manifest.yaml/raw'

        try:
            last_commit = DockerImageValidator._get_latest_commit(commits_url, docker_image_name)
            if not last_commit:
                return ''
            manifest_file_content = DockerImageValidator._get_manifest_from_commit(manifest_url, last_commit)
            if not manifest_file_content:
                return ''
        except Exception as e:
            raise(e)

        version_pattern = 'tags:\n- (.*)\n'
        latest_version = re.findall(version_pattern, manifest_file_content)

        # If manifest file does not contain the tag:
        if not latest_version:
            raise Exception('(Iron Bank) Manifest file does not contain tag in expected format.')

        return latest_version[0].strip('"')

    @staticmethod
    def _get_manifest_from_commit(manifest_url, commit_id):
        # gets the manifest file from the specified commit in Iron Bank:
        res = requests.get(url=manifest_url, params={'ref': commit_id}, verify=False, timeout=TIMEOUT)

        # If file does not exists in the last commit:
        if res.status_code != 200:
            raise Exception("Missing manifest file in the latest successful commit.")

        return res.text

    @staticmethod
    def _get_latest_commit(commits_url, docker_image_name):
        # Get latest commit in master which passed the pipeline of the project in Iron Bank:
        res = requests.get(url=commits_url, params={'ref': 'master', 'status': 'success'}, verify=False,
                           timeout=TIMEOUT)

        # Project may not be existing and needs to be created.
        if res.status_code != 200:
            raise Exception('The docker image in your integration/script cannot be found in Iron Bank.'
                            f' Please create image {docker_image_name} In Iron Bank.')

        list_of_commits = res.json()

        # Project seems to have no succeed pipeline for master branch, meaning the image is not in Iron Bank.
        if not list_of_commits:
            raise Exception('The docker image in your integration/script does not have a tag in Iron Bank.'
                            f' Please create or update to an updated versioned image In Iron Bank.')

        list_of_commits = sorted(list_of_commits, key=lambda x: x['updated_at'], reverse=True)
        return list_of_commits[0]['sha']
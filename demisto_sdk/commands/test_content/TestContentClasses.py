import ast
import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import uuid
from copy import deepcopy
from distutils.version import LooseVersion
from math import ceil
from pprint import pformat
from queue import Empty, Queue
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import demisto_client
import prettytable
import requests
import urllib3
from demisto_client.demisto_api import DefaultApi, Incident
from demisto_client.demisto_api.rest import ApiException
from slack import WebClient as SlackClient

from demisto_sdk.commands.common.constants import (DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION,
                                                   FILTER_CONF, PB_Status)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import get_demisto_version
from demisto_sdk.commands.test_content.constants import CONTENT_BUILD_SSH_USER, LOAD_BALANCER_DNS
from demisto_sdk.commands.test_content.Docker import Docker
from demisto_sdk.commands.test_content.IntegrationsLock import acquire_test_lock
from demisto_sdk.commands.test_content.mock_server import RESULT, MITMProxy, run_with_mock
from demisto_sdk.commands.test_content.ParallelLoggingManager import ParallelLoggingManager
from demisto_sdk.commands.test_content.tools import get_ui_url, is_redhat_instance, update_server_configuration

json = JSON_Handler()

ENV_RESULTS_PATH = './artifacts/env_results.json'
FAILED_MATCH_INSTANCE_MSG = "{} Failed to run.\n There are {} instances of {}, please select one of them by using " \
                            "the instance_name argument in conf.json. The options are:\n{}"
ENTRY_TYPE_ERROR = 4
DEFAULT_INTERVAL = 4
MAX_RETRIES = 3
RETRIES_THRESHOLD = ceil(MAX_RETRIES / 2)

SLACK_MEM_CHANNEL_ID = 'CM55V7J8K'
XSIAM_SERVER_TYPE = 'XSIAM'
# For now we run all xsiam tests
IS_XSIAM = False

__all__ = ['BuildContext',
           'Conf',
           'Integration',
           'IntegrationConfiguration',
           'SecretConf',
           'TestConfiguration',
           'TestContext',
           'TestPlaybook',
           'TestResults',
           'ServerContext']


class IntegrationConfiguration:
    def __init__(self, integration_configuration):
        self.raw_dict = integration_configuration
        self.name: str = integration_configuration.get('name', '')
        self.instance_name: str = integration_configuration.get('instance_name', self.name)
        self.is_byoi: bool = integration_configuration.get('byoi', True)
        self.should_validate_test_module: bool = integration_configuration.get('validate_test', True)
        self.has_integration: bool = integration_configuration.get('has_integration', True)
        self.params: dict = integration_configuration.get('params', {})

    def __str__(self):
        return json.dumps(self.raw_dict)

    def __repr__(self):
        return str(self)


class SecretConf:
    def __init__(self, secret_conf: dict):
        """
        Args:
            secret_conf: The contents of the content-test-conf conf.json file.
        """
        self.server_username = secret_conf['username']
        self.server_password = secret_conf['userPassword']
        self.integrations = [
            IntegrationConfiguration(integration_configuration=configuration) for configuration in
            secret_conf['integrations']
        ]


class TestConfiguration:
    def __init__(self, test_configuration: dict, default_test_timeout: int):
        """
        Args:
            test_configuration: A record of a test from 'tests' list in conf.json file in content repo..
            default_test_timeout: The default timeout to use in case no timeout is specified in the configuration
        """
        self.raw_dict = test_configuration
        self.playbook_id = test_configuration.get('playbookID', '')
        self.nightly_test = test_configuration.get('nightly', False)
        self.from_version = test_configuration.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION)
        self.to_version = test_configuration.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)
        self.timeout = test_configuration.get('timeout', default_test_timeout)
        self.memory_threshold = test_configuration.get('memory_threshold', Docker.DEFAULT_CONTAINER_MEMORY_USAGE)
        self.pid_threshold = test_configuration.get('pid_threshold', Docker.DEFAULT_CONTAINER_PIDS_USAGE)
        self.runnable_on_docker_only: bool = test_configuration.get('runnable_on_docker_only', False)
        self.is_mockable = test_configuration.get('is_mockable')
        self.context_print_dt = test_configuration.get('context_print_dt')
        self.test_integrations: List[str] = self._parse_integrations_conf(test_configuration)
        self.test_instance_names: List[str] = self._parse_instance_names_conf(test_configuration)
        self.instance_configuration: dict = test_configuration.get('instance_configuration', {})
        self.external_playbook_config: dict = test_configuration.get('external_playbook_config', {})
        self.is_first_playback_failed: bool = False
        self.number_of_executions: int = 0
        self.number_of_successful_runs: int = 0

    @staticmethod
    def _parse_integrations_conf(test_configuration):
        integrations_conf = test_configuration.get('integrations', [])
        if not isinstance(integrations_conf, list):
            integrations_conf = [integrations_conf]
        return integrations_conf

    @staticmethod
    def _parse_instance_names_conf(test_configuration):
        instance_names_conf = test_configuration.get('instance_names', [])
        if not isinstance(instance_names_conf, list):
            instance_names_conf = [instance_names_conf]
        return instance_names_conf

    def __str__(self):
        return str(self.raw_dict)


class Conf:
    def __init__(self, conf: dict):
        """
        Args:
            conf: The contents of the content conf.json file.
        """
        self.default_timeout: int = conf.get('testTimeout', 30)
        self.tests: list = [
            TestConfiguration(test_configuration, self.default_timeout) for test_configuration in conf.get('tests', [])
        ]
        self.skipped_tests: Dict[str, str] = conf.get('skipped_tests')  # type: ignore
        self.skipped_integrations: Dict[str, str] = conf.get('skipped_integrations')  # type: ignore
        self.unmockable_integrations: Dict[str, str] = conf.get('unmockable_integrations')  # type: ignore
        self.parallel_integrations: List[str] = conf['parallel_integrations']
        self.docker_thresholds = conf.get('docker_thresholds', {}).get('images', {})


class TestPlaybook:

    def __init__(self,
                 build_context,
                 test_configuration: TestConfiguration):
        """
        This class has all the info related to a test playbook during test execution
        Args:
            build_context (BuildContext): The build context to use in the build
            test_configuration: The configuration from content conf.json file
        """
        self.build_context = build_context
        self.configuration: TestConfiguration = test_configuration
        self.is_mockable: bool = self.configuration.playbook_id not in build_context.unmockable_test_ids
        self.integrations: List[Integration] = [
            Integration(self.build_context, integration_name, self.configuration.test_instance_names)
            for integration_name in self.configuration.test_integrations]
        self.integrations_to_lock = [
            integration for integration in self.integrations if
            integration.name not in self.build_context.conf.parallel_integrations]

    def __str__(self):
        return f'"{self.configuration.playbook_id}"'

    def __repr__(self):
        return str(self)

    def should_test_run(self):
        skipped_tests_collected = self.build_context.tests_data_keeper.skipped_tests

        def in_filtered_tests():
            """
            Checks if there are a list of filtered tests that the playbook is in them.
            """
            if not self.build_context.filtered_tests or self.configuration.playbook_id not in self.build_context.filtered_tests:
                self.build_context.logging_module.debug(f'Skipping {self} because it\'s not in filtered tests')
                skipped_tests_collected[self.configuration.playbook_id] = 'not in filtered tests'
                return False
            return True

        def nightly_test_in_non_nightly_build():
            """
            Checks if we are on a build which is not nightly, and the test should run only on nightly builds.
            """
            if self.configuration.nightly_test and not self.build_context.is_nightly:
                log_message = f'Skipping {self} because it\'s a nightly test in a non nightly build'
                if self.configuration.playbook_id in self.build_context.filtered_tests:
                    self.build_context.logging_module.warning(log_message)
                else:
                    self.build_context.logging_module.debug(log_message)
                skipped_tests_collected[self.configuration.playbook_id] = 'nightly test in a non nightly build'
                return True
            return False

        def skipped_test():
            if self.configuration.playbook_id in self.build_context.conf.skipped_tests:
                if self.configuration.playbook_id in self.build_context.filtered_tests:
                    # Add warning log, as the playbook is supposed to run according to the filters, but it's skipped
                    self.build_context.logging_module.warning(f'Skipping test {self} because it\'s in skipped test list')
                else:
                    self.build_context.logging_module.debug(f'Skipping test {self} because it\'s in skipped test list')
                reason = self.build_context.conf.skipped_tests[self.configuration.playbook_id]
                skipped_tests_collected[self.configuration.playbook_id] = reason
                return True
            return False

        def version_mismatch():
            if not (LooseVersion(self.configuration.from_version) <= LooseVersion(
                    self.build_context.server_numeric_version) <= LooseVersion(self.configuration.to_version)):
                self.build_context.logging_module.warning(
                    f'Test {self} ignored due to version mismatch '
                    f'(test versions: {self.configuration.from_version}-{self.configuration.to_version})\n')
                skipped_tests_collected[self.configuration.playbook_id] = \
                    f'(test versions: {self.configuration.from_version}-{self.configuration.to_version})'
                return True
            return False

        def test_has_skipped_integration():
            for integration in self.configuration.test_integrations:
                # So now we know that the test is in the filtered tests
                if integration in self.build_context.conf.skipped_integrations:
                    self.build_context.logging_module.debug(f'Skipping {self} because it has a skipped integration {integration}')
                    # The playbook should be run but has a skipped integration
                    if self.build_context.filtered_tests and self.configuration.playbook_id in self.build_context.filtered_tests:
                        # Adding the playbook ID to playbook_skipped_integration so that we can send a PR comment about it
                        skip_reason = self.build_context.conf.skipped_integrations[integration]
                        self.build_context.tests_data_keeper.playbook_skipped_integration.add(
                            f'{self.configuration.playbook_id} - reason: {skip_reason}')
                        self.build_context.logging_module.warning(
                            f'The integration {integration} is skipped and critical for the test {self}.')
                        skipped_tests_collected[self.configuration.playbook_id] = f'The integration {integration} is skipped'
                    return True

            return False

        return in_filtered_tests() and \
            not nightly_test_in_non_nightly_build() and \
            not skipped_test() and \
            not version_mismatch() and \
            not test_has_skipped_integration()

    def run_test_module_on_integrations(self, client: DefaultApi) -> bool:
        """
        runs 'test-module' on all integrations that the playbook uses and return a boolean indicating the result
        Args:
            client: The demisto_client to use

        Returns:
            True if all integrations was test-module execution was successful else False
        """
        for integration in self.integrations:
            success = integration.test_integration_instance(client)
            if not success:
                return False
        return True

    def configure_integrations(self, client: DefaultApi, server_context: 'ServerContext',
                               instance_configuration: dict) -> bool:
        """
        Configures all integrations that the playbook uses and return a boolean indicating the result
        Args:
            client: The demisto_client to use
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in

        Returns:
            True if all integrations was configured else False
        """
        configured_integrations: List[Integration] = []
        for integration in self.integrations:
            instance_created = integration.create_integration_instance(client,
                                                                       self.configuration.playbook_id,
                                                                       self.is_mockable,
                                                                       server_context,
                                                                       instance_configuration,
                                                                       )
            if not instance_created:
                self.build_context.logging_module.error(
                    f'Cannot run playbook {self}, integration {integration} failed to configure')
                # Deleting all the already configured integrations
                for configured_integration in configured_integrations:
                    configured_integration.delete_integration_instance(client)
                return False
            configured_integrations.append(integration)
        return True

    def disable_integrations(self, client: DefaultApi, server_context: 'ServerContext') -> None:
        """
        Disables all integrations that the playbook uses
        Clears server configurations set for the integration if there are such
        Reset containers if server configurations were cleared

        Args:
            client: The demisto_client to use
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in
        """
        for integration in self.integrations:
            integration.disable_integration_instance(client)
        updated_keys = False
        if not IS_XSIAM:
            updated_keys = self._set_prev_server_keys(client, server_context)
        if updated_keys:
            server_context._reset_containers()

    def _set_prev_server_keys(self, client: DefaultApi, server_context: 'ServerContext') -> bool:
        """Sets previous stored system (server) config, if existed

        Args:
            client (DefaultApi): The demisto_client to use
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in

        Returns:
             bool: Whether server configurations were updated to indicate if reset containers is required
        """
        updated = False
        for integration in self.integrations:
            if integration.configuration and 'server_keys' not in integration.configuration.params:
                continue
            if server_context.prev_system_conf:
                update_server_configuration(
                    client=client,
                    server_configuration=server_context.prev_system_conf,
                    error_msg='Failed to set server keys',
                    logging_manager=integration.build_context.logging_module,
                )
                server_context.prev_system_conf = {}
                updated = True
            else:
                integration.build_context.logging_module.error(
                    f'Failed clearing system conf. Found server_keys for integration {integration.name} but could not'
                    'find previous system conf stored'
                )
        return updated

    def delete_integration_instances(self, client: DefaultApi):
        """
        Deletes all integrations that the playbook uses
        Args:
            client: The demisto_client to use
        """
        for integration in self.integrations:
            integration.delete_integration_instance(client)

    def create_incident(self, client: DefaultApi) -> Optional[Incident]:
        """
        Creates an incident with the current playbook ID
        Args:
            client: The demisto_client to use

        Returns:
            - The created incident or None
        """
        # Preparing the incident request

        incident_name = f'inc-{self.configuration.playbook_id}--build_number:' \
                        f'{self.build_context.build_number}--{uuid.uuid4()}'
        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = True
        create_incident_request.playbook_id = self.configuration.playbook_id
        create_incident_request.name = incident_name

        try:
            response = client.create_incident(create_incident_request=create_incident_request)
        except ApiException:
            self.build_context.logging_module.exception(
                f'Failed to create incident with name {incident_name} for playbook {self}')
        try:
            inc_id = response.id
        except Exception:
            inc_id = 'incCreateErr'
        # inc_id = response_json.get('id', 'incCreateErr')
        if inc_id == 'incCreateErr':
            error_message = f'Failed to create incident for playbookID: {self}.' \
                            'Possible reasons are:\nMismatch between playbookID in conf.json and ' \
                            'the id of the real playbook you were trying to use,' \
                            'or schema problems in the TestPlaybook.'
            self.build_context.logging_module.error(error_message)
            return None

        # get incident
        search_filter = demisto_client.demisto_api.SearchIncidentsData()
        inc_filter = demisto_client.demisto_api.IncidentFilter()
        inc_filter.query = f'id: {inc_id}'
        if IS_XSIAM:
            # in xsiam `create_incident` response don`t return created incident id.
            inc_filter.query = f'name:"{incident_name}"'
        # inc_filter.query
        search_filter.filter = inc_filter

        incident_search_responses = []

        found_incidents = 0
        # poll the incidents queue for a max time of 300 seconds
        timeout = time.time() + 300
        while found_incidents < 1:
            try:
                incidents = client.search_incidents(filter=search_filter)
                found_incidents = incidents.total
                incident_search_responses.append(incidents)
            except ApiException:
                if IS_XSIAM:
                    self.build_context.logging_module.exception(f'Searching incident with name {incident_name} failed')
                else:
                    self.build_context.logging_module.exception(f'Searching incident with id {inc_id} failed')
            if time.time() > timeout:
                if IS_XSIAM:
                    self.build_context.logging_module.error(f'Got timeout for searching incident with name '
                                                            f'{incident_name}')
                else:
                    self.build_context.logging_module.error(f'Got timeout for searching incident id {inc_id}')

                self.build_context.logging_module.error(f'Incident search responses: {incident_search_responses}')
                return None

            time.sleep(10)

        return incidents.data[0]

    def delete_incident(self, client: DefaultApi, incident_id: str) -> bool:
        """
        Deletes a Demisto incident
        Args:
            client: demisto_client instance to use
            incident_id: Incident to delete

        Returns:
            True if incident was deleted else False
        """
        try:
            body = {
                'ids': [incident_id],
                'filter': {},
                'all': False
            }
            res = demisto_client.generic_request_func(self=client, method='POST',
                                                      path='/incident/batchDelete', body=body)
        except ApiException:
            self.build_context.logging_module.exception(
                'Failed to delete incident, error trying to communicate with demisto server')
            return False

        if int(res[1]) != 200:
            self.build_context.logging_module.error(f'delete incident failed with Status code {res[1]}')
            self.build_context.logging_module.error(pformat(res))
            return False

        return True

    def close_incident(self, client: DefaultApi, incident_id: str) -> bool:
        """
        Closes a Demisto incident
        Args:
            client: demisto_client instance to use
            incident_id: Incident to close

        Returns:
            True if incident was closed else False
        """
        try:
            body = {
                'id': incident_id,
                'CustomFields': {}
            }
            res = demisto_client.generic_request_func(self=client, method='POST',
                                                      path='/incident/close', body=body)
            self.build_context.logging_module.info(f'Closed incident: {incident_id}.')
        except ApiException:
            self.build_context.logging_module.warning(
                'Failed to close incident, error trying to communicate with demisto server.')
            return False

        if int(res[1]) != 200:
            self.build_context.logging_module.warning(f'Close incident failed with Status code {res[1]}')
            self.build_context.logging_module.warning(pformat(res))
            return False

        return True

    def print_context_to_log(self, client: DefaultApi, incident_id: str) -> None:
        try:
            body = {
                "query": f"${{{self.configuration.context_print_dt}}}"
            }
            res = demisto_client.generic_request_func(self=client, method='POST',
                                                      path=f'/investigation/{incident_id}/context', body=body)
            if int(res[1]) != 200:
                self.build_context.logging_module.error(f'incident context fetch failed with Status code {res[1]}')
                self.build_context.logging_module.error(pformat(res))
                return
            try:
                self.build_context.logging_module.info(json.dumps(ast.literal_eval(res[0]), indent=4))
            except ValueError:
                self.build_context.logging_module.error(f"unable to parse result for result with value: {res[0]}")
        except ApiException:
            self.build_context.logging_module.exception(
                'Failed to get context, error trying to communicate with demisto server')


class BuildContext:
    def __init__(self, kwargs: dict, logging_module: ParallelLoggingManager):
        global IS_XSIAM
        self.is_xsiam = True if kwargs['server_type'] == XSIAM_SERVER_TYPE else False
        IS_XSIAM = self.is_xsiam
        self.logging_module: ParallelLoggingManager = logging_module
        self.server = kwargs['server']
        self.xsiam_machine = kwargs.get('xsiam_machine')
        self.xsiam_servers_path = kwargs.get('xsiam_servers_path')
        self.conf, self.secret_conf = self._load_conf_files(kwargs['conf'], kwargs['secret'])
        if self.is_xsiam:
            with open(kwargs.get('xsiam_servers_api_keys_path'), 'r') as json_file:  # type: ignore[arg-type]
                xsiam_servers_api_keys = json.loads(json_file.read())
            self.xsiam_conf = self._load_xsiam_file(self.xsiam_servers_path)
            self.env_json = [self.xsiam_conf.get(self.xsiam_machine, {})]
            self.api_key = xsiam_servers_api_keys.get(self.xsiam_machine)
            self.auth_id = self.env_json[0].get('x-xdr-auth-id')
            self.xsiam_ui_path = self.env_json[0].get('ui_url')
        else:
            self.api_key = kwargs['api_key']
            self.env_json = self._load_env_results_json()
            self.xsiam_conf = None
            self.auth_id = None
            self.xsiam_ui_path = None
        self.is_nightly = kwargs['nightly']
        self.slack_client = SlackClient(kwargs['slack'])
        self.circleci_token = kwargs['circleci']
        self.build_number = kwargs['build_number']
        self.build_name = kwargs['branch_name']
        self.isAMI = kwargs['is_ami'] if not self.is_xsiam else False
        self.memCheck = kwargs['mem_check']
        self.server_version = kwargs['server_version']  # AMI Role
        self.is_local_run = (self.server is not None)
        self.server_numeric_version = self._get_server_numeric_version()
        self.instances_ips = self._get_instances_ips()
        self.filtered_tests = self._extract_filtered_tests()
        self.tests_data_keeper = TestResults(self.conf.unmockable_integrations)
        self.conf_unmockable_tests = self._get_unmockable_tests_from_conf()
        self.unmockable_test_ids: Set[str] = set()
        self.mockable_tests_to_run, self.unmockable_tests_to_run = self._get_tests_to_run()
        self.test_retries_queue: Queue = Queue()
        self.slack_user_id = self._retrieve_slack_user_id()
        self.all_integrations_configurations = self._get_all_integration_config(self.instances_ips)

    def _get_all_integration_config(self, instances_ips: dict) -> Optional[list]:
        """
        Gets all integration configuration as it exists on the demisto server
        Since in all packs are installed the data returned from this request is very heavy and we want to avoid
        running it in multiple threads.
        Args:
            instances_ips: The mapping of the urls to the ports used to tunnel it's traffic

        Returns:
            A dict containing the configuration for the integration if found, else empty list
        """
        if not self.is_nightly:
            return []
        url, port = list(instances_ips.items())[0]
        if IS_XSIAM:
            server_url = url
        else:
            server_url = f'https://localhost:{port}' if port else f'https://{url}'
        return self.get_all_installed_integrations_configurations(server_url)

    def get_all_installed_integrations_configurations(self, server_url: str) -> list:
        """
        Gets all integration configuration as it exists on the demisto server
        Args:
            server_url: The url of the server to create integration in

        Returns:
            A dict containing the configuration for the integration if found else empty list
        """
        if IS_XSIAM:
            # in xsiam we dont use demisto username
            os.environ.pop('DEMISTO_USERNAME', None)
        tmp_client = demisto_client.configure(base_url=server_url,
                                              auth_id=self.auth_id,
                                              api_key=self.api_key,
                                              verify_ssl=False)
        self.logging_module.debug('Getting all integrations instances')
        try:
            res_raw = demisto_client.generic_request_func(self=tmp_client, path='/settings/integration/search',
                                                          method='POST', body={})
        except ApiException:
            self.logging_module.exception('failed to get all integrations configuration')
            return []
        res = ast.literal_eval(res_raw[0])
        TIMEOUT = 180
        SLEEP_INTERVAL = 5
        total_sleep = 0
        while 'configurations' not in res:
            if total_sleep == TIMEOUT:
                self.logging_module.error(
                    f"Timeout - failed to get all integration configuration. Error: {res}")
                return []

            time.sleep(SLEEP_INTERVAL)
            total_sleep += SLEEP_INTERVAL
        all_configurations = res['configurations']
        return all_configurations

    def _generate_tests_queue(self, tests_to_run: List[TestConfiguration]) -> Queue:
        """
        Generates a queue containing test playbooks to run
        Args:
            tests_to_run: A list containing playbook names
        """
        queue: Queue = Queue()
        for test in tests_to_run:
            playbook = TestPlaybook(self, test)
            if playbook.should_test_run():
                queue.put(playbook)
        return queue

    def _get_tests_to_run(self) -> Tuple[Queue, Queue]:
        """
        Gets tests to run in the current build and updates the unmockable tests ids set
        Returns:
            - A queue with mockable TestPlaybook instances to run in the current build
            - A queue with unmockable TestPlaybook instances to run in the current build
        """
        unmockable_tests = []
        all_tests = self._get_all_tests()
        # for xsiam, set all tests to unmockable.
        if self.server or not self.isAMI or self.is_xsiam:
            unmockable_tests = all_tests
            self.unmockable_test_ids = {test.playbook_id for test in all_tests}
        elif self.isAMI:
            unmockable_tests = self.conf_unmockable_tests
            self.unmockable_test_ids = {test.playbook_id for test in self.conf_unmockable_tests}
        self.logging_module.debug(f'Unmockable tests selected: {pformat(self.unmockable_test_ids)}')
        mockable_tests = [test for test in all_tests if test.playbook_id not in self.unmockable_test_ids]
        self.logging_module.debug(f'Mockable tests selected: {pformat([test.playbook_id for test in mockable_tests])}')
        mockable_tests_queue = self._generate_tests_queue(mockable_tests)
        unmockable_tests_queue = self._generate_tests_queue(unmockable_tests)
        return mockable_tests_queue, unmockable_tests_queue

    @staticmethod
    def _extract_filtered_tests() -> list:
        """
        Reads the content from ./artifacts/filter_file.txt and parses it into a list of test playbook IDs that should be run
        in the current build
        Returns:
            A list of playbook IDs that should be run in the current build
        """
        with open(FILTER_CONF, 'r') as filter_file:
            filtered_tests = [line.strip('\n') for line in filter_file.readlines()]

        return filtered_tests

    def _get_unmockable_tests_from_conf(self) -> list:
        """
        Extracts the unmockable test playbook by looking at all playbooks that has unmockable integrations
        Returns:
            A with unmockable playbook names
        """
        unmockable_integrations = self.conf.unmockable_integrations
        tests = self.conf.tests
        unmockable_tests = []
        for test_record in tests:
            test_name = test_record.playbook_id
            unmockable_integrations_used = [integration_name for integration_name in test_record.test_integrations if
                                            integration_name in unmockable_integrations]
            if test_name and (not test_record.test_integrations or unmockable_integrations_used) or not self.isAMI:
                unmockable_tests.append(test_record)
                # In case a test has both - an unmockable integration and is configured with is_mockable=False -
                # it will be added twice if we don't continue.
                continue
            if test_record.is_mockable is False:
                unmockable_tests.append(test_record)
        return unmockable_tests

    @staticmethod
    def _get_used_integrations(test_configuration: dict) -> list:
        """
        Gets the integration used in a test playbook configurations
        Args:
            test_configuration: A test configuration from content conf.json file.

        Returns:
            A list with integration names
        """
        tested_integrations = test_configuration.get("integrations", [])
        if isinstance(tested_integrations, list):
            return tested_integrations
        else:
            return [tested_integrations]

    def _get_all_tests(self) -> List[TestConfiguration]:
        """
        Gets a list of all playbooks configured in content conf.json
        Returns:
            A list with playbook names
        """
        tests_records = self.conf.tests
        return [test for test in tests_records if test.playbook_id]

    def _get_instances_ips(self) -> Dict[str, Any]:
        """
        Parses the env_results.json and extracts the instance ip from each server configured in it.
        Returns:
            A dict contains a mapping from server internal ip to the port used to tunnel it.
        """
        if self.server:
            return {self.server: None}
        if self.is_xsiam:
            return {env.get('base_url'): None for env in self.env_json}
        instances_ips = {env.get('InstanceDNS'): env.get('TunnelPort') for env in self.env_json if
                         env.get('Role') == self.server_version}
        return instances_ips

    def get_public_ip_from_server_url(self, server_url: str) -> str:
        """
        Gets a tunnel server url in the form of https://localhost:<port>, from that url checks in self.instance_ips
        if there is a url that is mapped into that port and return that url if found.
        Args:
            server_url: The server url to parse the port from.

        Returns:
            A URL with the private IP of the server.
        """
        port_pattern = re.compile(r'https://localhost:([0-9]+)')
        port_match = port_pattern.findall(server_url)
        if port_match:
            port = int(port_match[0])
        else:
            # If the server URL has no port in the end - it means it's a local build or XSIAM, and we can return the
            # server URL as is.
            return server_url
        for server_private_ip, tunnel_port in self.instances_ips.items():
            if tunnel_port == port:
                return f'https://{server_private_ip}'
        raise Exception(f'Could not find private ip for the server mapped to port {port}')

    @staticmethod
    def _parse_tests_list_arg(tests_list: str):
        """
        Parses the test list arguments if present.

        :param tests_list: CSV string of tests to run.
        :return: List of tests if there are any, otherwise empty list.
        """
        tests_to_run = tests_list.split(",") if tests_list else []
        return tests_to_run

    @staticmethod
    def _load_env_results_json():
        if not os.path.isfile(ENV_RESULTS_PATH):
            return {}

        with open(ENV_RESULTS_PATH, 'r') as json_file:
            return json.load(json_file)

    def _get_server_numeric_version(self) -> str:
        """
        Gets the current server version

        Returns:
            Server numeric version
        """
        default_version = '99.99.98'
        if self.is_local_run:
            self.logging_module.info(f'Local run, assuming server version is {default_version}', real_time=True)
            return default_version

        if not self.env_json:
            self.logging_module.warning(
                f'Did not find {ENV_RESULTS_PATH} file, assuming server version is {default_version}.',
                real_time=True)
            return default_version

        server_version_mapping = {
            'Server 5.0': '5.0.0',
            'Server 5.5': '5.5.0',
            'Server 6.0': '6.0.0',
            'Server 6.1': '6.1.0',
            'Server 6.2': '6.2.0',
            'Server 6.5': '6.5.0',
            'Server 6.6': '6.6.0',
            'Server 6.8': '6.8.0',
            'Server 6.9': '6.9.0',
            'Server Master': default_version,
            'XSIAM 1.2': '6.9.0',
            'XSIAM Master': default_version
        }
        server_numeric_version = server_version_mapping.get(self.server_version, default_version)
        self.logging_module.info(f'Server version: {server_numeric_version}', real_time=True)
        return server_numeric_version

    @staticmethod
    def _load_xsiam_file(xsiam_servers_path):
        conf = None
        if xsiam_servers_path:
            with open(xsiam_servers_path) as data_file:
                conf = json.load(data_file)

        return conf

    @staticmethod
    def _load_conf_files(conf_path, secret_conf_path):
        with open(conf_path) as data_file:
            conf = Conf(json.load(data_file))

        secret_conf = None
        if secret_conf_path:
            with open(secret_conf_path) as data_file:
                secret_conf = SecretConf(json.load(data_file))

        return conf, secret_conf

    def _get_user_name_from_circle(self):
        url = f'https://circleci.com/api/v1.1/project/github/demisto/content/{self.build_number}'
        res = self._http_request(url, params_dict={'circle-token': self.circleci_token})

        user_details = res.get('user', {})
        return user_details.get('name', '')

    @staticmethod
    def _http_request(url, params_dict=None):
        res = requests.request("GET",
                               url,
                               verify=True,
                               params=params_dict,
                               )
        res.raise_for_status()

        return res.json()

    def _retrieve_slack_user_id(self):
        """
        Gets the user id of the circle user who triggered the current build
        """
        user_id = ''
        try:
            user_name = os.getenv('GITLAB_USER_LOGIN') or self._get_user_name_from_circle()
            res = self.slack_client.api_call('users.list')

            user_list = res.get('members', [])  # type: ignore
            for user in user_list:
                profile = user.get('profile', {})
                name = profile.get('real_name_normalized', '')
                if name == user_name:
                    user_id = user.get('id', '')
        except Exception as exc:
            logging.debug(f'failed to retrieve the slack user ID.\nError: {exc}')

        return user_id


class TestResults:

    def __init__(self, unmockable_integrations):
        self.succeeded_playbooks = []
        self.failed_playbooks = set()
        self.playbook_report = dict()
        self.skipped_tests = dict()
        self.skipped_integrations = dict()
        self.rerecorded_tests = []
        self.empty_files = []
        self.unmockable_integrations = unmockable_integrations
        self.playbook_skipped_integration = set()

    def add_proxy_related_test_data(self, proxy):
        # Using multiple appends and not extend since append is guaranteed to be thread safe
        for playbook_id in proxy.rerecorded_tests:
            self.rerecorded_tests.append(playbook_id)
        for playbook_id in proxy.empty_files:
            self.empty_files.append(playbook_id)

    def create_result_files(self):
        with open("./Tests/succeeded_tests.txt", "w") as succeeded_tests_file:
            succeeded_tests_file.write('\n'.join(self.succeeded_playbooks))
        with open("./Tests/failed_tests.txt", "w") as failed_tests_file:
            failed_tests_file.write('\n'.join(self.failed_playbooks))
        with open('./Tests/skipped_tests.txt', "w") as skipped_tests_file:
            skipped_tests_file.write('\n'.join(self.skipped_tests))
        with open('./Tests/skipped_integrations.txt', "w") as skipped_integrations_file:
            skipped_integrations_file.write('\n'.join(self.skipped_integrations))
        with open('./Tests/test_playbooks_report.json', "w") as test_playbooks_report_file:
            json.dump(self.playbook_report, test_playbooks_report_file, indent=4)

    def print_test_summary(self,
                           is_ami: bool = True,
                           logging_module: Union[Any, ParallelLoggingManager] = logging) -> None:
        """
        Takes the information stored in the tests_data_keeper and prints it in a human readable way.
        Args:
            is_ami: indicating if the server running the tests is an AMI or not.
            logging_module: Logging module to use for test_summary
        """
        succeed_playbooks = self.succeeded_playbooks
        failed_playbooks = self.failed_playbooks
        skipped_tests = self.skipped_tests
        unmocklable_integrations = self.unmockable_integrations
        skipped_integration = self.skipped_integrations
        rerecorded_tests = self.rerecorded_tests
        empty_files = self.empty_files

        succeed_count = len(succeed_playbooks)
        failed_count = len(failed_playbooks)
        rerecorded_count = len(rerecorded_tests) if is_ami else 0
        empty_mocks_count = len(empty_files) if is_ami else 0
        logging_module.real_time_logs_only = True
        logging_module.info('TEST RESULTS:')
        logging_module.info(f'Number of playbooks tested - {succeed_count + failed_count}')
        if failed_count:
            logging_module.error(f'Number of failed tests - {failed_count}:')
            logging_module.error('Failed Tests: {}'.format(
                ''.join([f'\n\t\t\t\t\t\t\t - {playbook_id}' for playbook_id in failed_playbooks])))
        if succeed_count:
            logging_module.success(f'Number of succeeded tests - {succeed_count}')
            logging_module.success('Successful Tests: {}'.format(
                ''.join([f'\n\t\t\t\t\t\t\t - {playbook_id}' for playbook_id in succeed_playbooks])))
        if rerecorded_count > 0:
            logging_module.debug(
                f'Number of tests with failed playback and successful re-recording - {rerecorded_count}')
            logging_module.debug('Tests with failed playback and successful re-recording: {}'.format(
                ''.join([f'\n\t\t\t\t\t\t\t - {playbook_id}' for playbook_id in rerecorded_tests])))

        if empty_mocks_count > 0:
            logging_module.debug(f'Successful tests with empty mock files count- {empty_mocks_count}:\n')
            proxy_explanation = \
                '\t\t\t\t\t\t\t (either there were no http requests or no traffic is passed through the proxy.\n' \
                '\t\t\t\t\t\t\t Investigate the playbook and the integrations.\n' \
                '\t\t\t\t\t\t\t If the integration has no http traffic, add to unmockable_integrations in conf.json)'
            logging_module.debug(proxy_explanation)
            logging_module.debug('Successful tests with empty mock files: {}'.format(
                ''.join([f'\n\t\t\t\t\t\t\t - {playbook_id}' for playbook_id in empty_files])))

        if skipped_integration:
            self.print_table("Skipped Integrations", skipped_integration, logging_module.debug)

        if skipped_tests:
            self.print_table("Skipped Tests", skipped_tests, logging_module.debug)

        if unmocklable_integrations:
            self.print_table("Unmockable Integrations", unmocklable_integrations, logging_module.debug)

    @staticmethod
    def print_table(table_name: str, table_data: dict, logging_method: Callable) -> None:
        table = prettytable.PrettyTable()
        table.field_names = ['Index', 'Name', 'Reason']
        for index, record in enumerate(table_data, start=1):
            row = [index, record, table_data[record]]
            table.add_row(row)
        logging_method(f'{table_name}:\n{table}', real_time=True)


class Integration:
    def __init__(self, build_context: BuildContext, integration_name: str, potential_integration_instance_names: list):
        """
        An integration class that should represent the integrations during the build
        Args:
            build_context: The context of the build
            integration_name: The name of the integration
            potential_integration_instance_names: A list of instance names, one of those names should be the actual reason
            but we won't know for sure until we will try to filter it with conf.json from content-test-conf repo
        """
        self.build_context = build_context
        self.name = integration_name
        self.instance_names = potential_integration_instance_names
        self.instance_name = ''
        self.configuration: Optional[IntegrationConfiguration] = IntegrationConfiguration(
            {'name': self.name,
             'params': {}})
        self.docker_image: list = []
        self.integration_configuration_from_server: dict = {}
        self.integration_type: str = ""
        self.module_instance: dict = {}

    @staticmethod
    def _change_placeholders_to_values(server_url: str,
                                       config_item: IntegrationConfiguration) -> IntegrationConfiguration:
        """Some integration should be configured on the current server as host and has the string '%%SERVER_HOST%%'
        in the content-test-conf conf.json configuration.
        This method replaces these placeholders in the configuration to their real values

        Args:
            server_url: The server url that should be inserted instead of the placeholder in the configuration params
            config_item: Integration configuration object.

        Returns:
            IntegrationConfiguration class with the modified params
        """
        placeholders_map = {'%%SERVER_HOST%%': server_url}
        item_as_string = json.dumps(config_item.params)
        for key, value in placeholders_map.items():
            item_as_string = item_as_string.replace(key, value)
        config_item.params = json.loads(item_as_string)
        return config_item

    def _set_integration_params(self, server_url: str, playbook_id: str, is_mockable: bool) -> bool:
        """
        Finds the matching configuration for the integration in content-test-data conf.json file
        in accordance with the configured instance name if exist and configures the proxy parameter if needed
        Args:
            server_url: The url of the demisto server to configure the integration in
            playbook_id: The ID of the playbook for which the integration should be configured
            is_mockable: Should the proxy parameter be set to True or not

        Returns:
            True if found a matching configuration else False if found more that one configuration candidate returns False
        """
        self.build_context.logging_module.debug(f'Searching integration configuration for {self}')

        # Finding possible configuration matches
        integration_params: List[IntegrationConfiguration] = [
            deepcopy(conf) for conf in
            self.build_context.secret_conf.integrations if
            conf.name == self.name
        ]
        # Modifying placeholders if exists
        integration_params: List[IntegrationConfiguration] = [
            self._change_placeholders_to_values(server_url, conf) for conf in integration_params]

        if integration_params:
            # If we have more then one configuration for this integration - we will try to filter by instance name
            if len(integration_params) != 1:
                found_matching_instance = False
                for item in integration_params:
                    if item.instance_name in self.instance_names:
                        self.configuration = item
                        found_matching_instance = True
                        break

                if not found_matching_instance:
                    optional_instance_names = [optional_integration.instance_name
                                               for optional_integration in integration_params]
                    error_msg = FAILED_MATCH_INSTANCE_MSG.format(playbook_id,
                                                                 len(integration_params),
                                                                 self.name,
                                                                 '\n'.join(optional_instance_names))
                    self.build_context.logging_module.error(error_msg)
                    return False
            else:
                self.configuration = integration_params[0]

        elif self.name == 'Demisto REST API':
            if IS_XSIAM:
                self.build_context.logging_module.warning('Trying to configure "Demisto REST API" for XSIAM server, '
                                                          'this integration will not work on XSIAM, '
                                                          'consider using CoreRestAPI.')
            self.configuration.params = {  # type: ignore
                'url': 'https://localhost',
                'apikey': self.build_context.api_key,
                'insecure': True,
            }
        if is_mockable:
            self.build_context.logging_module.debug(f'configuring {self} with proxy params')
            for param in ('proxy', 'useProxy', 'useproxy', 'insecure', 'unsecure'):
                self.configuration.params[param] = True  # type: ignore
        return True

    def _get_integration_config(self, server_url: str) -> Optional[dict]:
        """
        Gets integration configuration as it exists on the demisto server
        Args:
            server_url: The url of the server to create integration in

        Returns:
            A dict containing the configuration for the integration if found, else None
        """
        if self.build_context.all_integrations_configurations:
            match_configurations = [x for x in self.build_context.all_integrations_configurations if
                                    x['name'] == self.name]
        else:
            all_configurations = self.build_context.get_all_installed_integrations_configurations(server_url)
            match_configurations = [x for x in all_configurations if x['name'] == self.name]

        if not match_configurations:
            self.build_context.logging_module.error('integration was not found')
            return None

        return deepcopy(match_configurations[0])

    def _delete_integration_instance_if_determined_by_name(self, client: DefaultApi, instance_name: str) -> None:
        """Deletes integration instance by it's name.

        Args:
            client (demisto_client): The configured client to use.
            instance_name (str): The name of the instance to delete.

        Notes:
            This function is needed when the name of the instance is pre-defined in the tests configuration, and the test
            itself depends on the instance to be called as the `instance name`.
            In case we need to configure another instance with the same name, the client will throw an error, so we
            will call this function first, to delete the instance with this name.

        """
        try:
            int_resp = demisto_client.generic_request_func(self=client, method='POST',
                                                           path='/settings/integration/search',
                                                           body={'size': 1000})
            int_instances = ast.literal_eval(int_resp[0])
        except ApiException:
            self.build_context.logging_module.exception(
                f'Failed to delete integration {self} instance, error trying to communicate with demisto server')
            return
        if int(int_resp[1]) != 200:
            self.build_context.logging_module.error(
                f'Get integration {self} instance failed with status code: {int_resp[1]}')
            return
        if 'instances' not in int_instances:
            self.build_context.logging_module.info(f'No integrations instances found to delete for {self}')
            return

        for instance in int_instances['instances']:
            if instance.get('name') == instance_name:
                self.build_context.logging_module.info(
                    f'Deleting integration instance {instance_name} since it is defined by name')
                self.delete_integration_instance(client, instance.get('id'))

    def _set_server_keys(self, client: DefaultApi, server_context: 'ServerContext') -> None:
        """In case the the params of the test in the content-test-conf repo has 'server_keys' key:
            Resets containers
            Adds server configuration keys using the demisto_client.

        Args:
            client (demisto_client): The configured client to use.
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in
        """
        if 'server_keys' not in self.configuration.params:  # type: ignore
            return

        server_context._reset_containers()

        self.build_context.logging_module.debug(f'Setting server keys for integration: {self}')

        data = {
            'data': {},
            'version': -1
        }

        for key, value in self.configuration.params.get('server_keys').items():  # type: ignore
            data['data'][key] = value  # type: ignore

        _, _, prev_system_conf = update_server_configuration(
            client=client,
            server_configuration=self.configuration.params.get('server_keys'),  # type: ignore
            error_msg='Failed to set server keys',
            logging_manager=self.build_context.logging_module
        )
        server_context.prev_system_conf = prev_system_conf

    def create_module(self, instance_name: str, configuration: dict, incident_configuration: dict = None):
        module_configuration = configuration['configuration']

        # If incident_type is given in Test Playbook configuration on test-conf, we change the default configuration.
        if incident_configuration and incident_configuration.get('incident_type'):
            incident_type_configuration = list(
                filter(lambda config: config.get('name') == 'incidentType', module_configuration))

            incident_type_configuration[0]['value'] = incident_configuration.get('incident_type')

        module_instance = {
            'brand': configuration['name'],
            'category': configuration['category'],
            'configuration': configuration,
            'data': [],
            'enabled': "true",
            'engine': '',
            'id': '',
            'isIntegrationScript': self.configuration.is_byoi,  # type: ignore
            'name': instance_name,
            'passwordProtected': False,
            'version': 0,
            'incomingMapperId': configuration.get('defaultMapperIn', ''),
            'mappingId': configuration.get('defaultClassifier', ''),
            'outgoingMapperId': configuration.get('defaultMapperOut', '')
        }

        # If default mapper or classifier are given in test-conf we ignore defaultMapperIn or defaultClassifier from yml.
        if incident_configuration and incident_configuration.get('classifier_id'):
            module_instance['mappingId'] = incident_configuration.get('classifier_id')
        if incident_configuration and incident_configuration.get('incoming_mapper_id'):
            module_instance['incomingMapperId'] = incident_configuration.get('incoming_mapper_id')

        return module_instance

    def create_integration_instance(self,
                                    client: DefaultApi,
                                    playbook_id: str,
                                    is_mockable: bool,
                                    server_context: 'ServerContext',
                                    instance_configuration: dict
                                    ) -> bool:
        """
        Create an instance of the integration in the server specified in the demisto client instance.
        Args:
            client: The demisto_client instance to use
            playbook_id: The playbook id for which the instance should be created
            is_mockable: Indicates whether the integration should be configured with proxy=True or not
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in

        Returns:
            The integration configuration as it exists on the server after it was configured
        """
        server_url = self.build_context.get_public_ip_from_server_url(client.api_client.configuration.host)
        self._set_integration_params(server_url, playbook_id, is_mockable)
        configuration = self._get_integration_config(client.api_client.configuration.host)
        if not configuration:
            self.build_context.logging_module.error(f'Could not find configuration for integration {self}')
            return False

        module_configuration = configuration['configuration']
        if not module_configuration:
            module_configuration = []

        if 'integrationInstanceName' in self.configuration.params:  # type: ignore
            instance_name = self.configuration.params['integrationInstanceName']  # type: ignore
            self._delete_integration_instance_if_determined_by_name(client, instance_name)
        else:
            instance_name = f'{self.configuration.instance_name.replace(" ", "_")}_test_{uuid.uuid4()}'  # type: ignore

        self.build_context.logging_module.info(
            f'Configuring instance for {self} (instance name: {instance_name}, '  # type: ignore
            f'validate "test-module": {self.configuration.should_validate_test_module})'
        )

        # define module instance:
        params = self.configuration.params  # type: ignore

        module_instance = self.create_module(instance_name, configuration, instance_configuration)

        # set server keys
        if not IS_XSIAM:
            self._set_server_keys(client, server_context)

        # set module params
        for param_conf in module_configuration:
            if param_conf['display'] in params or param_conf['name'] in params:
                # param defined in conf
                key = param_conf['display'] if param_conf['display'] in params else param_conf['name']
                if key == 'credentials':
                    credentials = params[key]
                    param_value = {
                        'credential': '',
                        'identifier': credentials['identifier'],
                        'password': credentials['password'],
                        'passwordChanged': False
                    }
                else:
                    param_value = params[key]

                param_conf['value'] = param_value
                param_conf['hasvalue'] = True
            elif param_conf['defaultValue']:
                # param is required - take default value
                param_conf['value'] = param_conf['defaultValue']
            module_instance['data'].append(param_conf)
        try:
            res = demisto_client.generic_request_func(self=client, method='PUT',
                                                      path='/settings/integration',
                                                      body=module_instance)
        except ApiException:
            self.build_context.logging_module.exception(f'Error trying to create instance for integration: {self}')
            return False

        if res[1] != 200:
            self.build_context.logging_module.error(f'create instance failed with status code  {res[1]}')
            self.build_context.logging_module.error(pformat(res[0]))
            return False

        integration_config = ast.literal_eval(res[0])
        self.integration_configuration_from_server = integration_config
        self.module_instance = module_instance
        integration_script = integration_config.get('configuration', {}).get('integrationScript', {}) or {}
        self.integration_type = integration_script.get('type', '')
        return True

    def delete_integration_instance(self, client, instance_id: Optional[str] = None) -> bool:
        """
        Deletes an integration with the given ID
        Args:
            client: Demisto client instance
            instance_id: The instance ID to Delete

        Returns:
            True if integration was deleted else False
        """
        self.build_context.logging_module.debug(f'Deleting {self} instance')
        instance_id = instance_id or self.integration_configuration_from_server.get('id')
        if not instance_id:
            self.build_context.logging_module.debug(f'no instance ID for integration {self} was supplied')
            return True
        try:
            res = demisto_client.generic_request_func(self=client, method='DELETE',
                                                      path='/settings/integration/' + urllib.parse.quote(
                                                          instance_id))
        except ApiException:
            self.build_context.logging_module.exception(
                'Failed to delete integration instance, error trying to communicate with demisto.')
            return False
        if int(res[1]) != 200:
            self.build_context.logging_module.error(f'delete integration instance failed\nStatus code {res[1]}')
            self.build_context.logging_module.error(pformat(res))
            return False
        if self.module_instance:
            self.module_instance = {}
        return True

    def test_integration_instance(self, client: DefaultApi) -> bool:
        """Runs test module on the integration instance
        Args:
            client: The demisto_client instance to use

        Returns:
            The integration configuration as it exists on the server after it was configured
        """
        if not self.configuration.should_validate_test_module:  # type: ignore
            self.build_context.logging_module.debug(
                f'Skipping test-module on {self} because the "validate_test" flag is set to False')
            return True

        connection_retries = 3
        response_code = 0
        integration_of_instance = self.integration_configuration_from_server.get('brand', '')
        instance_name = self.integration_configuration_from_server.get('name', '')
        self.build_context.logging_module.info(
            f'Running "test-module" for instance "{instance_name}" of integration "{integration_of_instance}".')
        for i in range(connection_retries):
            try:
                response_data, response_code, _ = demisto_client.generic_request_func(self=client, method='POST',
                                                                                      path='/settings/integration/test',
                                                                                      body=self.module_instance,
                                                                                      _request_timeout=120)
                break
            except ApiException:
                self.build_context.logging_module.exception(
                    f'Failed to test integration {self} instance, error trying to communicate with demisto server: '
                    f'{get_ui_url(client.api_client.configuration.host)}')
                return False
            except urllib3.exceptions.ReadTimeoutError:
                self.build_context.logging_module.warning(f"Could not connect. Trying to connect for the {i + 1} time")

        if int(response_code) != 200:
            self.build_context.logging_module.error(
                f'Integration-instance test-module failed. Bad status code: {response_code}.\n'
                f'Sever URL: {get_ui_url(client.api_client.configuration.host)}')
            return False

        result_object = ast.literal_eval(response_data)
        success, failure_message = bool(result_object.get('success')), result_object.get('message')
        if not success:
            server_url = get_ui_url(client.api_client.configuration.host)
            test_failed_msg = f'Test integration failed - server: {server_url}.\n' \
                              f'Failure message: {failure_message}' if failure_message else ' No failure message.'
            self.build_context.logging_module.error(test_failed_msg)
        return success

    def disable_integration_instance(self, client) -> None:
        """Disables the integration
        Args:
            client: The demisto_client instance to use

        Returns:
            The integration configuration as it exists on the server after it was configured
        """
        # tested with POSTMAN, this is the minimum required fields for the request.
        module_instance = {
            key: self.integration_configuration_from_server[key] for key in
            ['id', 'brand', 'name', 'data', 'isIntegrationScript', ]
        }
        module_instance['enable'] = "false"
        module_instance['version'] = -1
        self.build_context.logging_module.debug(f'Disabling integration instance "{module_instance.get("name")}"')
        try:
            res = demisto_client.generic_request_func(self=client, method='PUT',
                                                      path='/settings/integration',
                                                      body=module_instance)
        except ApiException:
            self.build_context.logging_module.exception('Failed to disable integration instance')
            return

        if res[1] != 200:
            self.build_context.logging_module.error(f'disable instance failed, Error: {pformat(res)}')

    def get_docker_images(self) -> List[str]:
        """
        Gets the docker image name from the configured integration instance's body if such body exists
        Returns:

        """
        if self.integration_configuration_from_server:
            return Docker.get_integration_image(self.integration_configuration_from_server)
        else:
            raise Exception('Cannot get docker image - integration instance was not created yet')

    def __str__(self):
        return f'"{self.name}"'

    def __repr__(self):
        return str(self)


class TestContext:
    def __init__(self,
                 build_context: BuildContext,
                 playbook: TestPlaybook,
                 client: DefaultApi,
                 server_context: 'ServerContext'):
        """
        Initializes the TestContext class
        Args:
            build_context: The context of the current build
            playbook: The TestPlaybook instance to run in the current test execution
            client: A demisto client instance to use for communication with the server
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in
        """
        self.build_context = build_context
        self.server_context = server_context
        self.playbook = playbook
        self.incident_id: Optional[str] = None
        self.test_docker_images: Set[str] = set()
        self.client: DefaultApi = client
        if IS_XSIAM:
            self.tunnel_command = ''
        else:
            self.tunnel_command = \
                f'ssh -i ~/.ssh/oregon-ci.pem -4 -o StrictHostKeyChecking=no -f -N ' \
                f'"{CONTENT_BUILD_SSH_USER}@{LOAD_BALANCER_DNS}" ' \
                f'-L "{self.server_context.tunnel_port}:{self.server_context.server_ip}:443"'

    def _get_investigation_playbook_state(self) -> str:
        """
        Queried the server for the current status of the test's investigation
        Returns:
            A string representing the status of the playbook
        """
        try:
            investigation_playbook_raw = demisto_client.generic_request_func(
                self=self.client,
                method='GET',
                path=f'/inv-playbook/{self.incident_id}')
            investigation_playbook = ast.literal_eval(investigation_playbook_raw[0])
        except ApiException:
            self.build_context.logging_module.exception(
                'Failed to get investigation playbook state, error trying to communicate with demisto server'
            )
            return PB_Status.FAILED

        try:
            state = investigation_playbook['state']
            return state
        except Exception:  # noqa: E722
            # setting state to `in progress` in XSIAM build,
            # Because `investigation_playbook` returned empty if xsiam investigation is still in progress.
            if IS_XSIAM:
                return PB_Status.IN_PROGRESS
            return PB_Status.NOT_SUPPORTED_VERSION

    def _collect_docker_images(self) -> None:
        """
        Collects docker images of the playbook's integration.
        This method can be called only after the integrations were configured in the server.
        """
        for integration in self.playbook.integrations:
            docker_images = integration.get_docker_images()
            if docker_images:
                self.test_docker_images.update(docker_images)

    def _print_investigation_error(self):
        try:
            res = demisto_client.generic_request_func(
                self=self.client,
                method='POST',
                path='/investigation/' + urllib.parse.quote(self.incident_id),  # type: ignore
                body={"pageSize": 1000})
            if res and int(res[1]) == 200:
                resp_json = ast.literal_eval(res[0])
                entries = resp_json['entries']

                self.build_context.logging_module.error(f'Playbook {self.playbook} has failed:')
                for entry in entries:
                    if entry['type'] == ENTRY_TYPE_ERROR and entry['parentContent']:
                        self.build_context.logging_module.error(f'- Task ID: {entry["taskId"]}')
                        # Checks for passwords and replaces them with "******"
                        parent_content = re.sub(
                            r' (P|p)assword="[^";]*"', ' password=******', entry['parentContent'])
                        self.build_context.logging_module.error(f'  Command: {parent_content}')
                        self.build_context.logging_module.error(f'  Body:\n{entry["contents"]}')
            else:
                self.build_context.logging_module.error(
                    f'Failed getting entries for investigation: {self.incident_id}. Res: {res}')
        except ApiException:
            self.build_context.logging_module.exception(
                'Failed to print investigation error, error trying to communicate with demisto server')

    def _poll_for_playbook_state(self) -> str:
        """
        Polls for the playbook execution in the incident and return it's state.
        Returns:
            A string representing the status of the playbook
        """
        timeout = time.time() + self.playbook.configuration.timeout
        number_of_attempts = 1
        # wait for playbook to finish run
        while True:
            # give playbook time to run
            time.sleep(5)
            try:
                # fetch status
                playbook_state = self._get_investigation_playbook_state()
            except demisto_client.demisto_api.rest.ApiException:
                playbook_state = 'Pending'
                self.build_context.logging_module.exception('Error when trying to get investigation playbook state')

            if playbook_state in (PB_Status.COMPLETED, PB_Status.NOT_SUPPORTED_VERSION):
                break
            if playbook_state == PB_Status.FAILED:
                self.build_context.logging_module.error(f'{self.playbook} failed with error/s')
                self._print_investigation_error()
                break
            if time.time() > timeout:
                self.build_context.logging_module.error(f'{self.playbook} failed on timeout')
                break

            if number_of_attempts % DEFAULT_INTERVAL == 0:
                self.build_context.logging_module.info(
                    f'{self.playbook} loop no. {number_of_attempts / DEFAULT_INTERVAL}, {playbook_state=}')
            number_of_attempts = number_of_attempts + 1
        return playbook_state

    def _run_incident_test(self) -> str:
        """
        Creates an incident in demisto server and return its status
        Returns:
            Empty string or
        """
        try:
            if not self.build_context.is_xsiam:
                self.build_context.logging_module.info(f'ssh tunnel command:\n{self.tunnel_command}')
            instance_configuration = self.playbook.configuration.instance_configuration

            if not self.playbook.configure_integrations(self.client, self.server_context, instance_configuration):
                return PB_Status.CONFIGURATION_FAILED

            test_module_result = self.playbook.run_test_module_on_integrations(self.client)
            if not test_module_result:
                self.playbook.disable_integrations(self.client, self.server_context)
                return PB_Status.FAILED

            external_playbook_configuration = self.playbook.configuration.external_playbook_config

            # Change Configuration for external configuration if needed
            restore_needed, default_vals, restore_path = replace_external_playbook_configuration(
                self.client, external_playbook_configuration)

            incident = self.playbook.create_incident(self.client)
            if not incident:
                return ''

            self.incident_id = incident.id if IS_XSIAM else incident.investigation_id
            investigation_id = self.incident_id
            if investigation_id is None:
                self.build_context.logging_module.error(f'Failed to get investigation id of incident: {incident}')
                return ''

            self.build_context.logging_module.info(f'Found incident with incident ID: {investigation_id}.')

            server_url = get_ui_url(self.client.api_client.configuration.host)
            if IS_XSIAM:
                self.build_context.logging_module.info(
                    f'Investigation URL: {self.build_context.xsiam_ui_path}incident-view/alerts_and_insights?caseId='
                    f'{investigation_id}&action:openAlertDetails={investigation_id}-work_plan')
            else:
                self.build_context.logging_module.info(f'Investigation URL: {server_url}/#/WorkPlan/{investigation_id}')
            playbook_state = self._poll_for_playbook_state()
            self.build_context.logging_module.info(f'Got incident: {investigation_id} status: {playbook_state}.')
            if self.playbook.configuration.context_print_dt:
                self.playbook.print_context_to_log(self.client, investigation_id)

            # restore Configuration for external playbook
            if restore_needed:
                restore_external_playbook_configuration(self.client, restore_path=restore_path,
                                                        restore_values=default_vals)

            self.playbook.disable_integrations(self.client, self.server_context)
            self._clean_incident_if_successful(playbook_state)
            return playbook_state
        except Exception:
            self.build_context.logging_module.exception(f'Failed to run incident test for {self.playbook}')
            return PB_Status.FAILED

    def _clean_incident_if_successful(self, playbook_state: str) -> None:
        """
        Deletes the integration instances and the incident if the test was successful or failed on docker rate limit
        Args:
            playbook_state: The state of the playbook with which we can check if the test was successful
        """
        test_passed = playbook_state in (PB_Status.COMPLETED, PB_Status.NOT_SUPPORTED_VERSION)
        # batchDelete is not supported in XSIAM, only close.
        # in XSAIAM we are closing both successful and failed incidents
        if IS_XSIAM and self.incident_id:
            self.playbook.close_incident(self.client, self.incident_id)
            self.playbook.delete_integration_instances(self.client)
        elif self.incident_id and test_passed:
            self.playbook.delete_incident(self.client, self.incident_id)
            self.playbook.delete_integration_instances(self.client)

    def _run_docker_threshold_test(self):
        self._collect_docker_images()
        if self.test_docker_images:
            memory_threshold, pid_threshold = self.get_threshold_values()
            error_message = Docker.check_resource_usage(
                server_url=self.server_context.server_ip,
                docker_images=self.test_docker_images,
                def_memory_threshold=memory_threshold,
                def_pid_threshold=pid_threshold,
                docker_thresholds=self.build_context.conf.docker_thresholds,
                logging_module=self.build_context.logging_module)
            if error_message:
                self.build_context.logging_module.error(error_message)
                return False
        return True

    def get_threshold_values(self) -> Tuple[int, int]:
        """
        Gets the memory and pid threshold values to enforce on the current test.
        If one of the playbook's integrations is a powershell integration - the threshold have to be equals or
        higher than the default powershell threshold value.
        Returns:
            - The memory threshold value
            - The pid threshold value
        """
        memory_threshold = self.playbook.configuration.memory_threshold
        pid_threshold = self.playbook.configuration.pid_threshold
        has_pwsh_integration = any(integration for integration in self.playbook.integrations if
                                   integration.integration_type == Docker.POWERSHELL_INTEGRATION_TYPE)
        if has_pwsh_integration:
            memory_threshold = max(Docker.DEFAULT_PWSH_CONTAINER_MEMORY_USAGE, memory_threshold)
            pid_threshold = max(Docker.DEFAULT_PWSH_CONTAINER_PIDS_USAGE, pid_threshold)
        return memory_threshold, pid_threshold

    def _send_slack_message(self, channel, text, user_name, as_user):
        self.build_context.slack_client.api_call(
            "chat.postMessage",
            json={
                'channel': channel,
                'username': user_name,
                'as_user': as_user,
                'text': text,
                'mrkdwn': 'true'
            }
        )

    def _notify_failed_test(self):
        text = f'{self.build_context.build_name} - {self.playbook} Failed\n' \
               f'for more details run: `{self.tunnel_command}` and browse into the following link\n' \
               f'{get_ui_url(self.client.api_client.configuration.host)}'
        text += f'/#/WorkPlan/{self.incident_id}' if self.incident_id else ''
        if self.build_context.slack_user_id:
            self.build_context.slack_client.api_call(
                "chat.postMessage",
                json={
                    'channel': self.build_context.slack_user_id,
                    'username': 'Content CircleCI',
                    'as_user': 'False',
                    'text': text
                }
            )

    def _add_to_succeeded_playbooks(self) -> None:
        """
        Adds the playbook to the succeeded playbooks list
        """
        self.build_context.tests_data_keeper.succeeded_playbooks.append(self.playbook.configuration.playbook_id)

    def _add_details_to_failed_tests_report(self, playbook_name: str, failed_stage: str) -> None:
        """
        Adds the relevant details to the failed tests report.

        Args:
            playbook_name: The test's name.
            failed_stage: The stage where the test failed.
        """
        self.build_context.tests_data_keeper.playbook_report.setdefault(playbook_name, []).append({
            'number_of_executions': self.playbook.configuration.number_of_executions,
            'number_of_successful_runs': self.playbook.configuration.number_of_successful_runs,
            'failed_stage': failed_stage,
        })

    @staticmethod
    def _get_failed_stage(status: Optional[str], is_second_playback_run: bool = False) -> str:
        """
        Gets the test failed stage.

        Args:
            status: what is the test status.
            is_second_playback_run: Is The playbook run on a second playback after a freshly created record.
        """
        if is_second_playback_run:
            return 'Second playback'
        if status == PB_Status.FAILED_DOCKER_TEST:
            return 'Docker test'
        if status == PB_Status.CONFIGURATION_FAILED:
            return 'Configuration'
        return 'Execution'

    def _add_to_failed_playbooks(self, is_second_playback_run: bool = False, status: Optional[str] = None) -> None:
        """
        Adds the playbook to the failed playbooks list

        Args:
            is_second_playback_run: Is The playbook run on a second playback after a freshly created record
        """
        failed_stage = self._get_failed_stage(status, is_second_playback_run)
        playbook_name_to_add = self.playbook.configuration.playbook_id
        if not self.playbook.is_mockable:
            playbook_name_to_add += " (Mock Disabled)"
        if is_second_playback_run:
            self.build_context.logging_module.error(
                'Playback on newly created record has failed, see the following confluence page for help:\n'
                'https://confluence.paloaltonetworks.com/display/DemistoContent/Debug+Proxy-Related+Test+Failures')
            playbook_name_to_add += ' (Second Playback)'

        self._add_details_to_failed_tests_report(self.playbook.configuration.playbook_id, failed_stage)
        self.build_context.logging_module.error(f'Test failed: {self}')
        self.build_context.tests_data_keeper.failed_playbooks.add(playbook_name_to_add)

    @staticmethod
    def _get_circle_memory_data() -> Tuple[str, str]:
        """
        Checks how many bytes are currently in use in the circle build instance
        Returns:
            The number of bytes in use
        """
        process = subprocess.Popen(['cat', '/sys/fs/cgroup/memory/memory.usage_in_bytes'], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()

    @staticmethod
    def _get_circle_processes_data() -> Tuple[str, str]:
        """
        Returns some data about the processes currently running in the circle build instance
        """
        process = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()

    def _send_circle_memory_and_pid_stats_on_slack(self):
        """
        Sends a slack messages with the number of bytes currently in use and the number of processes currently in use
        """
        if self.build_context.is_nightly and self.build_context.memCheck and not self.build_context.is_local_run:
            stdout, stderr = self._get_circle_memory_data()
            text = 'Memory Usage: {}'.format(stdout) if not stderr else stderr
            self._send_slack_message(SLACK_MEM_CHANNEL_ID, text, 'Content CircleCI', 'False')
            stdout, stderr = self._get_circle_processes_data()
            text = stdout if not stderr else stderr
            self._send_slack_message(SLACK_MEM_CHANNEL_ID, text, 'Content CircleCI', 'False')

    def _incident_and_docker_test(self) -> str:
        """
        Runs incident and docker tests (the docker test is optional)
        Returns:
            The result of the test.
        """
        playbook_state = self._run_incident_test()
        # We don't want to run docker tests on redhat instance because it does not use docker and it does not support
        # the threshold configurations.
        if playbook_state == PB_Status.COMPLETED and self.server_context.is_instance_using_docker:
            #  currently not supported on XSIAM (etc/#47908)
            if not IS_XSIAM:
                docker_test_results = self._run_docker_threshold_test()
                if not docker_test_results:
                    playbook_state = PB_Status.FAILED_DOCKER_TEST
                self._clean_incident_if_successful(playbook_state)
        return playbook_state

    def _execute_unmockable_test(self) -> bool:
        """
        Executes an unmockable test
        In case the test failed to execute because one of the test's integrations were locked will return False
        as indication that the test was not done.
        Returns:
            True if test has finished it's execution else False
        """
        self.build_context.logging_module.info(f'------ Test {self} start ------ (Mock: Disabled)')
        with acquire_test_lock(self.playbook) as lock:
            if lock:
                status = self._incident_and_docker_test()
                self.playbook.configuration.number_of_executions += 1
                self._update_playbook_status(status)
            else:
                return False
        return True

    def _update_complete_status(self, is_first_execution: bool, is_record_run: bool, is_first_playback_run: bool,
                                is_second_playback_run: bool, use_retries_mechanism: bool,
                                number_of_executions: int):
        """
        Updates (if necessary) the playbook status in case the original status is complete.
        Args:
            is_first_execution: whether it is the first execution or not.
            is_record_run: whether it is a record execution or not.
            is_first_playback_run: whether it is the first playback execution or not.
            is_second_playback_run: whether it is the second playback execution or not.
            use_retries_mechanism: whether to use the retries mechanism or not.
            number_of_executions: the number of times the test was executed.
        Returns:
            PB_Status.COMPLETED if the Test-Playbook passed successfully and was added to succeeded playbooks.
            PB_Status.FAILED if the Test-Playbook failed and was added to failed playbooks.
            PB_Status.SECOND_PLAYBACK_REQUIRED if second playback is needed.
            PB_Status.IN_PROGRESS if more executions are needed in order to determine whether the playbook is successful or not.
        """

        self.build_context.logging_module.success(f'PASS: {self} succeed')

        # count successful run only when recording mockable or executing unmockable test.
        if not is_first_playback_run and not is_second_playback_run:
            self.playbook.configuration.number_of_successful_runs += 1

        # mockable test, first record passed, still need to check second playback.
        if is_first_execution and is_record_run:
            return PB_Status.SECOND_PLAYBACK_REQUIRED

        # first/last playback passed (mockable tests) or first execution passed (unmockable tests). adding to succeeded
        # playbooks, no more executions are needed.
        if is_first_execution or is_first_playback_run or is_second_playback_run:
            return PB_Status.COMPLETED

        if use_retries_mechanism:
            return self._update_status_based_on_retries_mechanism(number_of_executions, is_record_run)

        return PB_Status.COMPLETED

    def _update_failed_status(self, is_record_run: bool, is_first_playback_run: bool, is_second_playback_run: bool,
                              use_retries_mechanism: bool, number_of_executions: int):
        """
        Handles the playbook failed status
        - Logs according to the results
        Args:
            is_record_run: whether it is a record execution.
            is_first_playback_run: whether it is the first playback execution.
            is_second_playback_run: whether it is the second playback execution.
            use_retries_mechanism: whether to use the retries mechanism.
            number_of_executions: how many times the test was executed.
        Returns:
            PB_Status.COMPLETED if the Test-Playbook passed successfully and was added to succeeded playbooks.
            PB_Status.FAILED if the Test-Playbook failed and was added to failed playbooks.
            PB_Status.SECOND_PLAYBACK_REQUIRED if second playback is needed.
            PB_Status.IN_PROGRESS if more executions are needed in order to determine whether the playbook is successful or not.
        """
        # in case the first playback run fails, the code should continue to record the playback.
        if is_first_playback_run:
            return PB_Status.IN_PROGRESS

        # in case the second playback run fails, test-playbook is considered a failure.
        if is_second_playback_run:
            return PB_Status.FAILED

        # in case of using the retries mechanism, the function should determine whether the test-playbook is considered
        # a failure or give it another try.
        if use_retries_mechanism:
            return self._update_status_based_on_retries_mechanism(number_of_executions, is_record_run)

        # the test-playbook is considered a failed playbook.
        return PB_Status.FAILED

    def _update_status_based_on_retries_mechanism(self, number_of_executions, is_record_run):
        """
        Updates the status of a test-playbook when using the retries mechanism.
        Args:
            number_of_executions: how many times the test was executed.
            is_record_run: whether it is a record execution.
        Returns:
            PB_Status.COMPLETED if the Test-Playbook passed successfully and was added to succeeded playbooks.
            PB_Status.FAILED if the Test-Playbook failed and was added to failed playbooks.
            PB_Status.SECOND_PLAYBACK_REQUIRED if second playback is needed.
            PB_Status.IN_PROGRESS if more executions are needed in order to determine whether the playbook is successful or not.
        """
        if number_of_executions < MAX_RETRIES:
            self.build_context.logging_module.info(
                f'Using the retries mechanism for test {self}.\n'
                f'Test-Playbook was executed {number_of_executions} times, more executions are needed.')
            self.build_context.test_retries_queue.put(self.playbook)
            return PB_Status.IN_PROGRESS

        else:  # number_of_executions == MAX_RETRIES:
            # check if in most executions, the test passed.
            if self.playbook.configuration.number_of_successful_runs >= RETRIES_THRESHOLD:
                # It's not enough that the record run will pass to declare the test as successful,
                # we need the second playback to pass as well.
                if is_record_run:
                    self.build_context.logging_module.info(
                        f'Test-Playbook recording was executed {MAX_RETRIES} times, and passed {self.playbook.configuration.number_of_successful_runs} times.'
                        f' Running second playback.')
                    return PB_Status.SECOND_PLAYBACK_REQUIRED
                self.build_context.logging_module.info(
                    f'Test-Playbook was executed {MAX_RETRIES} times, and passed {self.playbook.configuration.number_of_successful_runs} times.'
                    f' Adding to succeeded playbooks.')
                return PB_Status.COMPLETED
            else:
                self.build_context.logging_module.info(
                    f'Test-Playbook was executed {MAX_RETRIES} times, and passed only {self.playbook.configuration.number_of_successful_runs} times.'
                    f' Adding to failed playbooks.')
                return PB_Status.FAILED

    def _update_playbook_status(self, status: str,
                                is_first_playback_run: bool = False,
                                is_second_playback_run: bool = False,
                                is_record_run: bool = False) -> str:
        """
        Updates the playbook status if necessary and adds the test to the right set (succeeded/failed) if test is done.
        Args:
            status: The string representation of the playbook execution
            is_first_playback_run: Is the playbook runs in playback mode
            is_second_playback_run: Is The playbook run on a second playback after a freshly created record
        Returns:
            PB_Status.COMPLETED if the Test-Playbook passed successfully and was added to succeeded playbooks.
            PB_Status.FAILED if the Test-Playbook failed and was added to failed playbooks.
            PB_Status.SECOND_PLAYBACK_REQUIRED if second playback is needed.
            PB_Status.IN_PROGRESS if more executions are needed in order to determine whether the playbook is successful or not.
        """
        use_retries_mechanism = self.server_context.use_retries_mechanism
        number_of_executions = self.playbook.configuration.number_of_executions
        is_first_execution = number_of_executions == 1

        if status == PB_Status.COMPLETED:
            updated_status = self._update_complete_status(is_first_execution, is_record_run, is_first_playback_run,
                                                          is_second_playback_run, use_retries_mechanism,
                                                          number_of_executions)

        elif status in (PB_Status.FAILED_DOCKER_TEST, PB_Status.CONFIGURATION_FAILED):
            self._add_to_failed_playbooks(status=status)
            return status

        else:  # test-playbook failed
            updated_status = self._update_failed_status(is_record_run, is_first_playback_run, is_second_playback_run,
                                                        use_retries_mechanism, number_of_executions)

        if updated_status == PB_Status.COMPLETED:
            self._add_to_succeeded_playbooks()
        elif updated_status == PB_Status.FAILED:
            self._notify_failed_test()
            self._add_to_failed_playbooks(is_second_playback_run=is_second_playback_run)
        return updated_status

    def _execute_mockable_test(self, proxy: MITMProxy):
        """
        Executes a mockable test
        In case the test failed to execute because one of the test's integrations were locked will return False
        as indication that the test was not done.
        Returns:
            True if test has finished it's execution else False
        """
        # we want to test first playback only once (we want to skip it when using retries mechanism)
        if not self.playbook.configuration.is_first_playback_failed:
            if proxy.has_mock_file(self.playbook.configuration.playbook_id):
                # Running first playback run on mock file
                self.build_context.logging_module.info(f'------ Test {self} start ------ (Mock: Playback)')
                with run_with_mock(proxy, self.playbook.configuration.playbook_id) as result_holder:
                    status = self._incident_and_docker_test()
                    status = self._update_playbook_status(status, is_first_playback_run=True)
                    result_holder[RESULT] = status == PB_Status.COMPLETED
                if status in (PB_Status.COMPLETED, PB_Status.FAILED_DOCKER_TEST):
                    return True
                self.build_context.logging_module.warning(
                    "Test failed with mock, recording new mock file. (Mock: Recording)")
                self.playbook.configuration.is_first_playback_failed = True

        # Running on record mode since playback has failed or mock file was not found
        self.build_context.logging_module.info(f'------ Test {self} start ------ (Mock: Recording)')
        with acquire_test_lock(self.playbook) as lock:
            if lock:
                with run_with_mock(proxy, self.playbook.configuration.playbook_id, record=True) as result_holder:
                    status = self._incident_and_docker_test()
                    self.playbook.configuration.number_of_executions += 1
                    status = self._update_playbook_status(status, is_record_run=True)
                    result_holder[RESULT] = status == PB_Status.SECOND_PLAYBACK_REQUIRED
            else:
                # If the integrations were not locked - the test has not finished it's execution
                return False

        # Running playback after successful record to verify the record is valid for future runs
        if status == PB_Status.SECOND_PLAYBACK_REQUIRED:
            self.build_context.logging_module.info(
                f'------ Test {self} start ------ (Mock: Second playback)')
            with run_with_mock(proxy, self.playbook.configuration.playbook_id) as result_holder:
                status = self._run_incident_test()
                self._update_playbook_status(status, is_second_playback_run=True)
                result_holder[RESULT] = status == PB_Status.COMPLETED
        return True

    def _is_runnable_on_current_server_instance(self) -> bool:
        """
        Nightly builds can have RHEL instances that uses podman instead of docker as well as the regular LINUX instance.
        In such case - if the test in runnable on docker instances **only** and the current instance uses podman -
        we will not execute the test under this instance and instead will will return it to the queue in order to run
        it under some other instance
        Returns:
            True if this instance can be run on the current instance else False
        """
        if self.playbook.configuration.runnable_on_docker_only and not self.server_context.is_instance_using_docker:
            self.build_context.logging_module.debug(
                f'Skipping test {self.playbook} since it\'s not runnable on podman instances')
            return False
        return True

    def execute_test(self, proxy: Optional[MITMProxy] = None) -> bool:
        """
        Executes the test and return a boolean that indicates whether the test was executed or not.
        In case the test was not executed - it will be returned to the queue and will be collected later in the future
        by some other ServerContext instance.
        Args:
            proxy: The MITMProxy instance to use in the current test

        Returns:
            True if the test was executed by the instance else False
        """
        try:
            if not self._is_runnable_on_current_server_instance():
                return False
            self._send_circle_memory_and_pid_stats_on_slack()
            if self.playbook.is_mockable:
                test_executed = self._execute_mockable_test(proxy)  # type: ignore
            else:
                test_executed = self._execute_unmockable_test()
            return test_executed
        except Exception:
            self.build_context.logging_module.exception(
                f'Unexpected error while running test on playbook {self.playbook}')
            self._add_to_failed_playbooks()
            return True
        finally:
            self.build_context.logging_module.info(f'------ Test {self} end ------ \n')
            self.build_context.logging_module.execute_logs()

    def __str__(self):
        test_message = f'playbook: {self.playbook}'
        if self.playbook.integrations:
            test_message += f' with integration(s): {self.playbook.integrations}'
        else:
            test_message += ' with no integrations'
        if not self.server_context.is_instance_using_docker:
            test_message += ', RedHat instance'
        return test_message

    def __repr__(self):
        return str(self)


class ServerContext:

    def __init__(self, build_context: BuildContext, server_private_ip: str, tunnel_port: int = None,
                 use_retries_mechanism: bool = True):
        self.build_context = build_context
        self.server_ip = server_private_ip
        self.tunnel_port = tunnel_port
        if IS_XSIAM:
            self.server_url = server_private_ip
            # we use client without demisto username
            os.environ.pop('DEMISTO_USERNAME', None)
        else:
            self.server_url = f'https://localhost:{tunnel_port}' if tunnel_port else f'https://{self.server_ip}'
        self.client: Optional[DefaultApi] = None
        self._configure_new_client()
        # currently not supported on XSIAM (etc/#47851)
        if IS_XSIAM:
            self.proxy = None
        else:
            self.proxy = MITMProxy(server_private_ip,
                                   self.build_context.logging_module,
                                   build_number=self.build_context.build_number,
                                   branch_name=self.build_context.build_name)
        self.is_instance_using_docker = not is_redhat_instance(self.server_ip)
        self.executed_tests: Set[str] = set()
        self.executed_in_current_round: Set[str] = set()
        self.prev_system_conf: dict = {}
        self.use_retries_mechanism: bool = use_retries_mechanism
        if IS_XSIAM:
            self.check_if_can_create_manual_alerts()

    def _execute_unmockable_tests(self):
        """
        Iterates the mockable tests queue and executes them as long as there are tests to execute
        """
        self._execute_tests(self.build_context.unmockable_tests_to_run)

    def _execute_tests(self, queue: Queue) -> None:
        """
        Iterates the tests queue and executes them as long as there are tests to execute.
        Before the tests execution starts we will reset the containers to make sure the proxy configuration is correct
        - We need it before the mockable tests because the server starts the python2 default container when it starts
            and it has no proxy configurations.
        - We need it before the unmockable tests because at that point all containers will have the proxy configured
            and we want to clean those configurations when testing unmockable playbooks
        Args:
            queue: The queue to fetch tests to execute from
        """
        self._reset_containers()
        while queue.unfinished_tasks:
            try:
                test_playbook: TestPlaybook = queue.get(block=False)
                self._reset_tests_round_if_necessary(test_playbook, queue)
            except Empty:
                continue
            self._configure_new_client()
            test_executed = TestContext(self.build_context,
                                        test_playbook,
                                        self.client,
                                        self).execute_test(self.proxy)
            if test_executed:
                self.executed_tests.add(test_playbook.configuration.playbook_id)
            else:
                queue.put(test_playbook)
            queue.task_done()

    def _execute_mockable_tests(self):
        """
        Iterates the mockable tests queue and executes them as long as there are tests to execute
        """
        # we running XSIAM without proxy. This code wont be executed on xsiam servers
        if not IS_XSIAM:
            self.proxy.configure_proxy_in_demisto(  # type: ignore[union-attr]
                proxy=self.proxy.ami.internal_ip + ':' + self.proxy.PROXY_PORT,  # type: ignore[union-attr]
                username=self.build_context.secret_conf.server_username,
                password=self.build_context.secret_conf.server_password,
                server=self.server_url)
        self._execute_tests(self.build_context.mockable_tests_to_run)
        if not IS_XSIAM:
            self.proxy.configure_proxy_in_demisto(proxy='',  # type: ignore[union-attr]
                                                  username=self.build_context.secret_conf.server_username,
                                                  password=self.build_context.secret_conf.server_password,
                                                  server=self.server_url)

    def _execute_failed_tests(self):
        self._execute_tests(self.build_context.test_retries_queue)

    def _reset_tests_round_if_necessary(self, test_playbook: TestPlaybook, queue_: Queue) -> None:
        """
        Checks if the string representation of the current test configuration is already in
        the executed_in_current_round set.
        If it is- it means we have already executed this test and the we have reached a round and there are tests that
        were not able to be locked by this execution..
        In that case we want to start a new round monitoring by emptying the 'executed_in_current_round' set and sleep
        in order to let the tests be unlocked
        Since this operation can be performed by multiple threads - this operaion is protected by the queue's lock
        Args:
            test_playbook: Test playbook to check if has been executed in the current round
            queue_: The queue from which the current tests are executed
        """
        queue_.mutex.acquire()
        if str(test_playbook.configuration) in self.executed_in_current_round:
            self.build_context.logging_module.info(
                'all tests in the queue were executed, sleeping for 30 seconds to let locked tests get unlocked.')
            self.executed_in_current_round = {str(test_playbook.configuration)}
            queue_.mutex.release()
            time.sleep(30)
            return
        else:
            self.executed_in_current_round.add(str(test_playbook.configuration))
        queue_.mutex.release()

    def _configure_new_client(self):
        if self.client:
            self.client.api_client.pool.close()
            self.client.api_client.pool.terminate()
            del self.client
        self.client = demisto_client.configure(base_url=self.server_url,
                                               api_key=self.build_context.api_key,
                                               auth_id=self.build_context.auth_id,
                                               verify_ssl=False)

    def _reset_containers(self):
        self.build_context.logging_module.info('Resetting containers\n', real_time=True)

        body, status_code, _ = demisto_client.generic_request_func(self=self.client, method='POST',
                                                                   path='/containers/reset')
        if status_code != 200:
            self.build_context.logging_module.critical(
                f'Request to reset containers failed with status code "{status_code}"\n{body}', real_time=True)
            sys.exit(1)
        time.sleep(10)

    def execute_tests(self):

        try:
            self.build_context.logging_module.info(f'Starts tests with server url - {get_ui_url(self.server_url)}',
                                                   real_time=True)
            self._execute_mockable_tests()
            self.build_context.logging_module.info('Running mock-disabled tests', real_time=True)
            self._execute_unmockable_tests()
            if self.use_retries_mechanism:
                self.build_context.logging_module.info('Running failed tests', real_time=True)
                self._execute_failed_tests()
            self.build_context.logging_module.info(f'Finished tests with server url - '
                                                   f'{get_ui_url(self.server_url)}',
                                                   real_time=True)
            # no need in xsiam, no proxy
            if not IS_XSIAM:
                self.build_context.tests_data_keeper.add_proxy_related_test_data(self.proxy)

            if self.build_context.isAMI and not IS_XSIAM:
                if self.proxy.should_update_mock_repo:  # type: ignore[union-attr]
                    self.proxy.push_mock_files()  # type: ignore[union-attr]
            self.build_context.logging_module.debug(f'Tests executed on server {self.server_ip}:\n'
                                                    f'{pformat(self.executed_tests)}')
        except Exception:
            self.build_context.logging_module.exception('~~ Thread failed ~~')
            raise
        finally:
            self.build_context.logging_module.execute_logs()

    def check_if_can_create_manual_alerts(self):
        """
        In XSIAM we can't create a new incident/alert using API call.
        We need a correlation rule in order to create an alert.
        We want to create an alert manually, when we send an API call to XSIAM server to create a new alert.
        Server check which integration sent a new alert, if the request was sent manually and not from integration it
        sets "sourceBrand" header to be "Manual". XSIAM Server looks for a correlation rule for such sourceBrand,
        and if there is no such correlation rule, no alert will be created.
        If there is a correlation rule for "Manual" integration the alert will be created.

        If this step fails please create an integration with id and name "Manual", set isFetch: true for such
        integration and make sure that the corresponding correlation rule is created.
        """
        body = {
            'query': 'id:"Manual"',
        }
        try:
            res_raw = demisto_client.generic_request_func(
                self=self.client,
                method='POST',
                path='/settings/integration/search',
                body=body,
            )
            res = ast.literal_eval(res_raw[0])
            if int(res_raw[1]) != 200:
                self.build_context.logging_module.error(
                    f'Failed to get integrations configuration with status code: {res_raw[1]}')
                return

            all_configurations = res['configurations']
            for instance in all_configurations:
                if instance.get('id') == "Manual":
                    self.build_context.logging_module.info('Server is able to create manual alerts '
                                                           '("Manual" integration exists).')
                    return
        except ApiException:
            self.build_context.logging_module.exception('Failed to get integrations configuration.')

        self.build_context.logging_module.warning('No "Manual" integration found in XSIAM instance. '
                                                  'Adding it in order to create Manual Correlation Rule.')
        self.create_manual_integration()

    def create_manual_integration(self):
        manual_integration = {
            "name": "Manual",
            "version": 1,
            "display": "Manual",
            "category": "Utilities",
            "description": "This integration creates Manual Correlation Rule.",
            "configuration": [],
            "integrationScript": {
                "script": "",
                "commands": [],
                "type": "python",
                "isFetch": True,
                "subtype": "python3"
            }
        }

        try:
            res_raw_integration = demisto_client.generic_request_func(
                self=self.client,
                method='PUT',
                path='/settings/integration-conf',
                body=manual_integration,
            )
            if int(res_raw_integration[1]) != 200:
                self.build_context.logging_module.error(
                    f'Failed to get integrations configuration with status code: {res_raw_integration[1]}')

        except ApiException:
            self.build_context.logging_module.exception('No "Manual" integration found in XSIAM instance. '
                                                        'Please add it in order to create Manual Correlation Rule.')


def replace_external_playbook_configuration(client: DefaultApi, external_playbook_configuration: dict,
                                            logger_module: logging.Logger = logging.getLogger('demisto-sdk')):
    """ takes external configuration of shape {"playbookID": "Isolate Endpoint - Generic V2",
                                               "input_parameters":{"Endpoint_hostname": {"simple", "test"}}}
        and changes the specified playbook configuration to the mentioned one.
        If playbook's inputs had changed, revert will be needed.
        Returns (Whether the Playbook changed, The values to restore, the path to use when restoring)
        Only to be used with server version 6.2 and above. """

    # Checking configuration
    if not external_playbook_configuration:
        logger_module.info("External Playbook Configuration not provided, skipping re-configuration.")
        return False, {}, ''

    # Checking server version
    server_version = get_demisto_version(client)

    if LooseVersion(server_version.base_version) < LooseVersion('6.2.0'):  # type: ignore
        logger_module.info("External Playbook not supported in versions previous to 6.2.0, skipping re-configuration.")
        return False, {}, ''

    logger_module.info("External Playbook in use, starting re-configuration.")

    # Getting current configuration
    external_playbook_id = external_playbook_configuration['playbookID']
    external_playbook_path = f'/playbook/{external_playbook_id}'
    res, _, _ = demisto_client.generic_request_func(client, method='GET',
                                                    path=external_playbook_path, response_type='object')

    inputs = res.get('inputs', [])
    if not inputs:
        raise Exception("External Playbook was not found or has no inputs.")

    # Save current for default Configuration.
    inputs_default = deepcopy(inputs)
    logger_module.info("Saved current configuration.")

    changed_keys = []
    failed_keys = []

    # Change Configuration for external pb.
    for input_ in external_playbook_configuration["input_parameters"]:
        matching_record = list(filter(lambda x: x.get('key') == input_, inputs))
        if matching_record:
            existing_val = matching_record[0]
            simple = external_playbook_configuration["input_parameters"][input_].get("simple")
            complex = external_playbook_configuration["input_parameters"][input_].get("complex")

            # If no value (simple or complex) was found, It is a typo
            if complex is None and simple is None:
                raise Exception(f'Could not found neither a `simple` nor `complex` value for field: {input_}. '
                                'A valid configuration should be of the followng format: '
                                '{<param name>: {"simple", <required value>}}')

            existing_val['value']["simple"] = simple
            existing_val['value']["complex"] = complex
            changed_keys.append(input_)

        else:
            failed_keys.append(input_)

    if failed_keys:
        raise Exception(f'Some input keys was not found in playbook: {",".join(failed_keys)}.')

    logger_module.info(f"Changing keys: {changed_keys}.")
    saving_inputs_path = f'/playbook/inputs/{external_playbook_id}'

    try:
        if changed_keys:
            demisto_client.generic_request_func(client, method='POST', path=saving_inputs_path, body=inputs)

    except Exception as e:
        raise Exception(f"Could not change inputs in playbook configuration. Error: {e}")

    logger_module.info(f"Re-configured {external_playbook_id} successfully with {len(changed_keys)} new values.")

    return True, inputs_default, saving_inputs_path


def restore_external_playbook_configuration(client: DefaultApi, restore_path: str, restore_values: dict,
                                            logger_module: logging.Logger = logging.getLogger('demisto-sdk')):
    logger_module.info("Restoring External Playbook parameters.")

    res, _, _ = demisto_client.generic_request_func(client, method='POST',
                                                    path=restore_path,
                                                    body=restore_values)

    logger_module.info("Restored External Playbook successfully.")

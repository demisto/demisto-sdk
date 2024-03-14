import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from pprint import pformat
from queue import Empty, Queue
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

import demisto_client
import prettytable
import requests
from demisto_client.demisto_api import DefaultApi, Incident
from demisto_client.demisto_api.rest import ApiException
from junitparser import JUnitXml, TestCase, TestSuite
from junitparser.junitparser import Failure, Result, Skipped
from packaging.version import Version
from slack_sdk import WebClient as SlackClient
from urllib3.exceptions import ReadTimeoutError

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    FILTER_CONF,
    MarketplaceVersions,
    PB_Status,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import get_demisto_version
from demisto_sdk.commands.test_content.Docker import Docker
from demisto_sdk.commands.test_content.IntegrationsLock import acquire_test_lock
from demisto_sdk.commands.test_content.mock_server import (
    RESULT,
    MITMProxy,
    run_with_mock,
)
from demisto_sdk.commands.test_content.ParallelLoggingManager import (
    ParallelLoggingManager,
)
from demisto_sdk.commands.test_content.tools import (
    get_ui_url,
    is_redhat_instance,
    update_server_configuration,
)

ENV_RESULTS_PATH = "./artifacts/env_results.json"
FAILED_MATCH_INSTANCE_MSG = (
    "{} Failed to run.\n There are {} instances of {}, please select one of them by using "
    "the instance_names argument in conf.json. The options are:\n{}"
)
ENTRY_TYPE_ERROR = 4
DEFAULT_INTERVAL = 4
MAX_RETRIES = 3
RETRIES_THRESHOLD = ceil(MAX_RETRIES / 2)

SLACK_MEM_CHANNEL_ID = "CM55V7J8K"
XSOAR_SERVER_TYPE = "XSOAR"
XSIAM_SERVER_TYPE = "XSIAM"
XPANSE_SERVER_TYPE = "XPANSE"
XSOAR_SAAS_SERVER_TYPE = "XSOAR SAAS"

MARKETPLACE_VERSIONS_TO_SERVER_TYPE = {
    MarketplaceVersions.XSOAR: {XSOAR_SERVER_TYPE, XSOAR_SAAS_SERVER_TYPE},
    MarketplaceVersions.MarketplaceV2: {XSIAM_SERVER_TYPE},
    MarketplaceVersions.XPANSE: {XPANSE_SERVER_TYPE},
    MarketplaceVersions.XSOAR_SAAS: {XSOAR_SAAS_SERVER_TYPE},
    MarketplaceVersions.XSOAR_ON_PREM: {XSOAR_SERVER_TYPE},
}

__all__ = [
    "BuildContext",
    "Conf",
    "Integration",
    "IntegrationConfiguration",
    "SecretConf",
    "TestConfiguration",
    "TestContext",
    "TestPlaybook",
    "TestResults",
    "ServerContext",
]


class IntegrationConfiguration:
    def __init__(self, integration_configuration):
        self.raw_dict = integration_configuration
        self.name: str = integration_configuration.get("name", "")
        self.instance_name: str = integration_configuration.get(
            "instance_name", self.name
        )
        self.is_byoi: bool = integration_configuration.get("byoi", True)
        self.should_validate_test_module: bool = integration_configuration.get(
            "validate_test", True
        )
        self.has_integration: bool = integration_configuration.get(
            "has_integration", True
        )
        self.params: dict = integration_configuration.get("params", {})

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
        self.server_username = secret_conf["username"]
        self.server_password = secret_conf["userPassword"]
        self.integrations = [
            IntegrationConfiguration(integration_configuration=configuration)
            for configuration in secret_conf["integrations"]
        ]


class TestConfiguration:
    def __init__(self, test_configuration: dict, default_test_timeout: int):
        """
        Args:
            test_configuration: A record of a test from 'tests' list in conf.json file in content repository.
            default_test_timeout: The default timeout to use in case no timeout is specified in the configuration
        """
        self.raw_dict = test_configuration
        self.playbook_id = test_configuration.get("playbookID", "")
        self.nightly_test = test_configuration.get("nightly", False)
        self.from_version = test_configuration.get(
            "fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION
        )
        self.to_version = test_configuration.get(
            "toversion", DEFAULT_CONTENT_ITEM_TO_VERSION
        )
        self.timeout = test_configuration.get("timeout", default_test_timeout)
        self.memory_threshold = test_configuration.get(
            "memory_threshold", Docker.DEFAULT_CONTAINER_MEMORY_USAGE
        )
        self.pid_threshold = test_configuration.get(
            "pid_threshold", Docker.DEFAULT_CONTAINER_PIDS_USAGE
        )
        self.runnable_on_docker_only: bool = test_configuration.get(
            "runnable_on_docker_only", False
        )
        self.is_mockable = test_configuration.get("is_mockable")
        self.context_print_dt = test_configuration.get("context_print_dt")
        self.test_integrations: List[str] = self._parse_integrations_conf(
            test_configuration
        )
        self.test_instance_names: List[str] = self._parse_instance_names_conf(
            test_configuration
        )
        self.marketplaces: List[MarketplaceVersions] = self._parse_marketplaces_conf(
            test_configuration
        )
        self.instance_configuration: dict = test_configuration.get(
            "instance_configuration", {}
        )
        self.external_playbook_config: dict = test_configuration.get(
            "external_playbook_config", {}
        )
        self.is_first_playback_failed: bool = False
        self.number_of_executions: int = 0
        self.number_of_successful_runs: int = 0

    @staticmethod
    def _parse_integrations_conf(test_configuration):
        integrations_conf = test_configuration.get("integrations", [])
        if not isinstance(integrations_conf, list):
            integrations_conf = [integrations_conf]
        return integrations_conf

    @staticmethod
    def _parse_instance_names_conf(test_configuration):
        instance_names_conf = test_configuration.get("instance_names", [])
        if not isinstance(instance_names_conf, list):
            instance_names_conf = [instance_names_conf]
        return instance_names_conf

    @staticmethod
    def _parse_marketplaces_conf(
        test_configuration,
    ) -> List[MarketplaceVersions]:
        marketplaces_conf = test_configuration.get("marketplaces", [])
        if not isinstance(marketplaces_conf, list):
            marketplaces_conf = [marketplaces_conf]
        marketplaces_conf = [
            MarketplaceVersions(marketplace) for marketplace in marketplaces_conf
        ]

        if MarketplaceVersions.XSOAR in marketplaces_conf:
            marketplaces_conf.append(MarketplaceVersions.XSOAR_SAAS)

        if MarketplaceVersions.XSOAR_ON_PREM in marketplaces_conf:
            marketplaces_conf.append(MarketplaceVersions.XSOAR)

        return marketplaces_conf

    def __str__(self):
        return str(self.raw_dict)


class Conf:
    def __init__(self, conf: dict):
        """
        Args:
            conf: The contents of the content conf.json file.
        """
        self.default_timeout: int = conf.get("testTimeout", 30)
        self.tests: list = [
            TestConfiguration(test_configuration, self.default_timeout)
            for test_configuration in conf.get("tests", [])
        ]
        self.skipped_tests: Dict[str, str] = conf.get("skipped_tests")  # type: ignore
        self.skipped_integrations: Dict[str, str] = conf.get("skipped_integrations")  # type: ignore
        self.skipped_integrations_set = set(self.skipped_integrations.keys())
        self.unmockable_integrations: Dict[str, str] = conf.get("unmockable_integrations")  # type: ignore
        self.parallel_integrations: List[str] = conf["parallel_integrations"]
        self.docker_thresholds = conf.get("docker_thresholds", {}).get("images", {})


class TestPlaybook:
    def __init__(self, build_context, test_configuration: TestConfiguration):
        """
        This class has all the info related to a test playbook during test execution
        Args:
            build_context (BuildContext): The build context to use in the build
            test_configuration: The configuration from content conf.json file
        """
        self.build_context = build_context
        self.configuration: TestConfiguration = test_configuration
        self.is_mockable: bool = (
            self.configuration.playbook_id not in build_context.unmockable_test_ids
        )
        self.test_suite = TestSuite(self.configuration.playbook_id)
        self.start_time = datetime.now(timezone.utc)
        self.test_suite_system_out: List[str] = []
        self.test_suite_system_err: List[str] = []
        self.integrations: List[Integration] = [
            Integration(
                self.build_context,
                integration_name,
                self.configuration.test_instance_names,
                self,
            )
            for integration_name in self.configuration.test_integrations
        ]
        self.integrations_to_lock = [
            integration
            for integration in self.integrations
            if integration.name not in self.build_context.conf.parallel_integrations
        ]
        self.populate_test_suite()

    def log_debug(self, message: str, real_time: bool = False):
        self.build_context.logging_module.debug(message, real_time)
        self.test_suite_system_out.append(message)

    def log_info(self, message: str, real_time: bool = False):
        self.build_context.logging_module.info(message, real_time)
        self.test_suite_system_out.append(message)

    def log_success(self, message: str, real_time: bool = False):
        self.build_context.logging_module.success(message, real_time)
        self.test_suite_system_out.append(message)

    def log_error(self, message: str, real_time: bool = False):
        self.build_context.logging_module.error(message, real_time)
        self.test_suite_system_err.append(message)

    def log_warning(self, message: str, real_time: bool = False):
        self.build_context.logging_module.warning(message, real_time)
        self.test_suite_system_err.append(message)

    def log_exception(self, message: str, real_time: bool = False):
        self.build_context.logging_module.exception(message, real_time)
        self.test_suite_system_err.append(message)

    def populate_test_suite(self):
        self.test_suite.add_property("build_number", self.build_context.build_number)
        self.test_suite.add_property("is_local_run", self.build_context.is_local_run)
        self.test_suite.add_property("is_nightly", self.build_context.is_nightly)
        self.test_suite.add_property(
            "is_saas_server_type", self.build_context.is_saas_server_type
        )
        self.test_suite.add_property("server_type", self.build_context.server_type)
        self.test_suite.add_property("product_type", self.build_context.product_type)
        self.test_suite.add_property("memCheck", self.build_context.memCheck)
        self.test_suite.add_property(
            "server_numeric_version", self.build_context.server_numeric_version
        )
        self.test_suite.add_property(
            "server_version", self.build_context.server_version
        )
        self.test_suite.add_property(
            "xsiam_servers_path", self.build_context.xsiam_servers_path
        )
        self.test_suite.add_property("xsiam_ui_path", self.build_context.xsiam_ui_path)
        self.test_suite.add_property(
            "instances_ips", ",".join(self.build_context.instances_ips)
        )

        self.test_suite.add_property("playbook.is_mockable", self.is_mockable)
        self.test_suite.add_property("is_mockable", self.configuration.is_mockable)
        self.test_suite.add_property("playbook_id", self.configuration.playbook_id)
        self.test_suite.add_property("from_version", self.configuration.from_version)
        self.test_suite.add_property("to_version", self.configuration.to_version)
        self.test_suite.add_property("nightly_test", self.configuration.nightly_test)
        self.test_suite.add_property("pid_threshold", self.configuration.pid_threshold)
        self.test_suite.add_property(
            "memory_threshold",
            self.configuration.memory_threshold,
        )
        self.test_suite.add_property("pid_threshold", self.configuration.pid_threshold)
        self.test_suite.add_property("timeout", self.configuration.timeout)
        self.test_suite.add_property(
            "playbook.test_instance_names",
            ",".join(self.configuration.test_instance_names),
        )
        self.test_suite.add_property(
            "playbook.marketplaces",
            ",".join(self.configuration.marketplaces),
        )
        self.test_suite.add_property(
            "playbook.integrations", ",".join(map(str, self.integrations))
        )
        self.test_suite.add_property(
            "runnable_on_docker_only",
            self.configuration.runnable_on_docker_only,
        )

    def close_test_suite(self, results: Optional[List[Result]] = None):
        results = results or []
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        test_case = TestCase(
            f"Test Playbook {self.configuration.playbook_id} on {self.build_context.server_version}",
            "TestPlaybook",
            duration,
        )
        test_case.system_out = "\n".join(self.test_suite_system_out)
        test_case.system_err = "\n".join(self.test_suite_system_err)
        test_case.result += results
        self.test_suite.add_testcase(test_case)
        self.build_context.tests_data_keeper.test_results_xml_file.add_testsuite(
            self.test_suite
        )

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
            if (
                not self.build_context.filtered_tests
                or self.configuration.playbook_id
                not in self.build_context.filtered_tests
            ):
                msg = f"Skipping {self} because it's not in filtered tests"
                self.log_debug(msg)
                self.close_test_suite([Skipped(msg)])
                skipped_tests_collected[
                    self.configuration.playbook_id
                ] = "not in filtered tests"
                return False
            return True

        def nightly_test_in_non_nightly_build():
            """
            Checks if we are on a build which is not nightly, and the test should run only on nightly builds.
            """
            if self.configuration.nightly_test and not self.build_context.is_nightly:
                log_message = f"Skipping {self} because it's a nightly test in a non nightly build"
                self.close_test_suite([Skipped(log_message)])
                if self.configuration.playbook_id in self.build_context.filtered_tests:
                    self.log_warning(log_message)
                else:
                    self.log_debug(log_message)
                skipped_tests_collected[
                    self.configuration.playbook_id
                ] = "nightly test in a non nightly build"
                return True
            return False

        def skipped_test():
            if (
                self.configuration.playbook_id
                not in self.build_context.conf.skipped_tests
            ):
                return False
            log_message = f"Skipping test {self} because it's in skipped test list"
            if self.configuration.playbook_id in self.build_context.filtered_tests:
                # Add warning log, as the playbook is supposed to run according to the filters, but it's skipped
                self.log_warning(log_message)
            else:
                self.log_debug(log_message)
            reason = self.build_context.conf.skipped_tests[
                self.configuration.playbook_id
            ]
            self.close_test_suite([Skipped(log_message)])
            skipped_tests_collected[self.configuration.playbook_id] = reason
            return True

        def version_mismatch():
            if not (
                Version(self.configuration.from_version)
                <= Version(self.build_context.server_numeric_version)
                <= Version(self.configuration.to_version)
            ):
                log_message = (
                    f"Test {self} ignored due to version mismatch "
                    f"(test versions: {self.configuration.from_version}-{self.configuration.to_version})\n"
                )
                self.log_warning(log_message)
                self.close_test_suite([Skipped(log_message)])
                skipped_tests_collected[
                    self.configuration.playbook_id
                ] = f"(test versions: {self.configuration.from_version}-{self.configuration.to_version})"
                return True
            return False

        def test_has_skipped_integration():
            if skipped_integrations := (
                self.build_context.conf.skipped_integrations_set
                & set(self.configuration.test_integrations)
            ):
                # The playbook should be run but has a skipped integration.
                self.log_debug(
                    f"Skipping {self} because it has skipped integrations:{','.join(skipped_integrations)}"
                )
                results: List[Result] = []
                for integration in skipped_integrations:

                    if (
                        self.build_context.filtered_tests
                        and self.configuration.playbook_id
                        in self.build_context.filtered_tests
                    ):
                        # Adding the playbook ID to playbook_skipped_integration so that we can send a PR comment about it
                        msg = (
                            f"{self.configuration.playbook_id} - reason: "
                            f"{self.build_context.conf.skipped_integrations[integration]}"
                        )
                        self.build_context.tests_data_keeper.playbook_skipped_integration.add(
                            msg
                        )
                        log_message = f"The integration {integration} is skipped and critical for the test {self}."
                        self.test_suite_system_err.append(log_message)
                        self.log_warning(log_message)
                        results.append(Skipped(msg))

                skipped_tests_collected[
                    self.configuration.playbook_id
                ] = f'The integrations:{",".join(skipped_integrations)} are skipped'
                self.test_suite.add_property(
                    "skipped_integrations", ",".join(skipped_integrations)
                )
                self.close_test_suite(results)
                return True

            return False

        def marketplaces_match_server_type() -> bool:
            """
            Checks if the test has a marketplace value, and if so- if it matches the server machine we are on.
            A test playbook might have several entries, each with a different marketplace. This might cause the test playbook to
            be in the filtered tests list, even when the provided entry is not be the one that runs with the current sever
            machine marketplace. This function checks that the entry provided is the exact one that needs to run.
            Entries might differ in any field, the most common one is instance_names.
            """
            test_server_types: Set[str] = set()
            for marketplace in self.configuration.marketplaces or []:
                test_server_types.update(
                    MARKETPLACE_VERSIONS_TO_SERVER_TYPE[marketplace]
                )

            if not test_server_types:
                return True  # test doesn't have a marketplace value so it runs on all machines

            instance_names_log_message = (
                f" for instance names: {', '.join(self.configuration.test_instance_names)}"
                if self.configuration.test_instance_names
                else ""
            )

            if self.build_context.server_type in test_server_types:
                self.log_debug(
                    f"Running {self} with current server marketplace{instance_names_log_message}"
                )
                return True  # test has a marketplace value that matched the build server marketplace

            log_message = (
                f"Skipping {self} because it's marketplace values are: "
                f"{', '.join(self.configuration.marketplaces)}{instance_names_log_message}, "
                f"which is not compatible with the current server marketplace value"
            )
            self.close_test_suite([Skipped(log_message)])
            if self.configuration.playbook_id in self.build_context.filtered_tests:
                self.log_warning(log_message)
            else:
                self.log_debug(log_message)
            skipped_tests_collected[
                self.configuration.playbook_id
            ] = f"test marketplaces are: {', '.join(self.configuration.marketplaces)}{instance_names_log_message}"
            return False  # test has a marketplace value that doesn't matched the build server marketplace

        return (
            in_filtered_tests()
            and not nightly_test_in_non_nightly_build()
            and not skipped_test()
            and not version_mismatch()
            and not test_has_skipped_integration()
            and marketplaces_match_server_type()
        )

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

    def configure_integrations(
        self,
        client: DefaultApi,
        server_context: "ServerContext",
        instance_configuration: dict,
    ) -> bool:
        """
        Configures all integrations that the playbook uses and return a boolean indicating the result
        Args:
            instance_configuration: The instance configuration to use for the integrations
            client: The demisto_client to use
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in

        Returns:
            True if all integrations was configured else False
        """
        configured_integrations: List[Integration] = []
        for integration in self.integrations:
            instance_created = integration.create_integration_instance(
                client,
                self.configuration.playbook_id,
                self.is_mockable,
                server_context,
                instance_configuration,
            )
            if not instance_created:
                self.log_error(
                    f"Cannot run playbook {self}, integration {integration} failed to configure"
                )
                # Deleting all the already configured integrations
                for configured_integration in configured_integrations:
                    configured_integration.delete_integration_instance(client)
                return False
            configured_integrations.append(integration)
        return True

    def disable_integrations(self, client: DefaultApi, server_context: "ServerContext"):
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
        if not self.build_context.is_saas_server_type:
            updated_keys = self._set_prev_server_keys(client, server_context)
        if updated_keys:
            server_context.reset_containers()

    def _set_prev_server_keys(
        self, client: DefaultApi, server_context: "ServerContext"
    ) -> bool:
        """Sets previous stored system (server) config, if existed

        Args:
            client (DefaultApi): The demisto_client to use
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in

        Returns:
             bool: Whether server configurations were updated to indicate if reset containers is required
        """
        updated = False
        for integration in self.integrations:
            if (
                integration.configuration
                and "server_keys" not in integration.configuration.params
            ):
                continue
            if server_context.prev_system_conf:
                update_server_configuration(
                    client=client,
                    server_configuration=server_context.prev_system_conf,
                    error_msg="Failed to set server keys",
                    logging_manager=self.build_context.logging_module,
                )
                server_context.prev_system_conf = {}
                updated = True
            else:
                self.log_error(
                    f"Failed clearing system conf. Found server_keys for integration {integration.name} but could not"
                    "find previous system conf stored"
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

    def create_incident(
        self, client: DefaultApi, timeout: int = 300, sleep_interval: int = 10
    ) -> Optional[Incident]:
        """
        Creates an incident with the current playbook ID
        Args:
            client: The demisto_client to use.
            timeout: The timeout to wait for the incident to be created, in seconds.
            sleep_interval: The interval to sleep between each poll, in seconds.

        Returns:
            - The created incident or None
        """
        # Preparing the incident request

        incident_name = (
            f"inc-{self.configuration.playbook_id}--build_number:"
            f"{self.build_context.build_number}--{uuid.uuid4()}"
        )
        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = True
        create_incident_request.playbook_id = self.configuration.playbook_id
        create_incident_request.name = incident_name

        inc_id = "incCreateErr"
        try:
            response = client.create_incident(
                create_incident_request=create_incident_request
            )
            inc_id = response.id
        except ApiException:
            self.log_exception(
                f"Failed to create incident with name {incident_name} for playbook {self}"
            )

        if inc_id == "incCreateErr":
            self.log_error(
                f"Failed to create incident for playbookID: {self}."
                "Possible reasons are:\nMismatch between playbookID in conf.json and "
                "the id of the real playbook you were trying to use, "
                "or schema problems in the TestPlaybook."
            )
            return None

        # get incident
        search_filter = demisto_client.demisto_api.SearchIncidentsData()
        inc_filter = demisto_client.demisto_api.IncidentFilter()
        if inc_id:
            inc_filter.query = f"id: {inc_id}"
        if self.build_context.is_saas_server_type:
            # In XSIAM or XSOAR SAAS - `create_incident` response don`t return created incident id.
            inc_filter.name = [incident_name]
        # inc_filter.query
        search_filter.filter = inc_filter

        # poll the incidents queue, until the timeout is reached.
        end_time = time.time() + timeout
        while True:
            try:
                incidents = client.search_incidents(filter=search_filter)
                if len(incidents.data):
                    return incidents.data[0]
            except ApiException:
                if self.build_context.is_saas_server_type:
                    self.log_exception(
                        f"Searching incident with name {incident_name} failed"
                    )
                else:
                    self.log_exception(f"Searching incident with id {inc_id} failed")
            if time.time() > end_time:
                if self.build_context.is_saas_server_type:
                    self.log_error(
                        f"Got timeout for searching incident with name "
                        f"{incident_name}"
                    )
                else:
                    self.log_error(f"Got timeout for searching incident id {inc_id}")
                return None

            time.sleep(sleep_interval)

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
            body = {"ids": [incident_id], "filter": {}, "all": False}
            response, status_code, headers = demisto_client.generic_request_func(
                self=client, method="POST", path="/incident/batchDelete", body=body
            )
        except ApiException:
            self.log_exception(
                "Failed to delete incident, error trying to communicate with demisto server"
            )
            return False

        if status_code != requests.codes.ok:
            self.log_error(
                f"delete incident failed - response:{pformat(response)}, status code:{status_code} headers:{headers}"
            )
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
            body = {"id": incident_id, "CustomFields": {}}
            response, status_code, headers = demisto_client.generic_request_func(
                self=client, method="POST", path="/incident/close", body=body
            )
            self.log_info(f"Closed incident: {incident_id}.")
        except ApiException:
            self.log_warning(
                "Failed to close incident, error trying to communicate with demisto server."
            )
            return False

        if status_code != requests.codes.ok:
            self.log_warning(
                f"Close incident failed - response:{pformat(response)}, status code:{status_code} headers:{headers}"
            )
            return False

        return True

    def print_context_to_log(self, client: DefaultApi, incident_id: str):
        try:
            body = {"query": f"${{{self.configuration.context_print_dt}}}"}
            response, status_code, headers = demisto_client.generic_request_func(
                self=client,
                method="POST",
                path=f"/investigation/{incident_id}/context",
                body=body,
                response_type="object",
            )
            if status_code != requests.codes.ok:
                self.log_error(
                    f"incident context fetch failed - response:{pformat(response)}, status code:{status_code} headers:{headers}"
                )
                return
            try:
                msg = json.dumps(response, indent=4)
                self.log_info(msg)
            except (ValueError, TypeError, json.JSONDecodeError):
                self.log_error(
                    f"unable to parse result for result with value: {response}"
                )
        except ApiException:
            self.log_error(
                "Failed to get context, error trying to communicate with demisto server"
            )


class BuildContext:
    def __init__(self, kwargs: dict, logging_module: ParallelLoggingManager):
        self.server_type = kwargs["server_type"]
        self.product_type = kwargs["product_type"]
        self.is_saas_server_type = self.server_type in [
            XSIAM_SERVER_TYPE,
            XSOAR_SAAS_SERVER_TYPE,
        ]
        self.logging_module: ParallelLoggingManager = logging_module
        self.server = kwargs["server"]
        self.xsiam_machine = kwargs.get("xsiam_machine")
        self.xsiam_servers_path = kwargs.get("xsiam_servers_path")
        self.conf, self.secret_conf = self._load_conf_files(
            kwargs["conf"], kwargs["secret"]
        )
        if self.is_saas_server_type:
            with open(kwargs.get("xsiam_servers_api_keys_path")) as json_file:  # type: ignore[arg-type]
                xsiam_servers_api_keys = json.loads(json_file.read())
            self.xsiam_conf = self._load_xsiam_file(self.xsiam_servers_path)
            self.env_json = [self.xsiam_conf.get(self.xsiam_machine, {})]
            self.api_key = xsiam_servers_api_keys.get(self.xsiam_machine)
            self.auth_id = self.env_json[0].get("x-xdr-auth-id")
            self.xsiam_ui_path = self.env_json[0].get("ui_url")
        else:
            self.api_key = kwargs["api_key"]
            self.env_json = self._load_env_results_json()
            self.xsiam_conf = None
            self.auth_id = None
            self.xsiam_ui_path = None
        self.is_nightly = kwargs["nightly"]
        self.slack_client = SlackClient(kwargs["slack"])
        self.circleci_token = kwargs["circleci"]
        self.build_number = kwargs["build_number"]
        self.build_name = kwargs["branch_name"]
        self.isAMI = False if self.is_saas_server_type else kwargs["is_ami"]
        self.memCheck = kwargs["mem_check"]
        self.server_version = kwargs["server_version"]  # AMI Role
        self.is_local_run = self.server is not None
        self.server_numeric_version = self._get_server_numeric_version()
        self.instances_ips = self._get_instances_ips()
        self.filtered_tests = self._extract_filtered_tests()
        self.tests_data_keeper = TestResults(
            self.conf.unmockable_integrations, kwargs["artifacts_path"]
        )
        self.conf_unmockable_tests = self._get_unmockable_tests_from_conf()
        self.unmockable_test_ids: Set[str] = set()
        (
            self.mockable_tests_to_run,
            self.unmockable_tests_to_run,
        ) = self._get_tests_to_run()
        self.test_retries_queue: Queue = Queue()
        self.slack_user_id = self._retrieve_slack_user_id()
        self.all_integrations_configurations = self._get_all_integration_config(
            self.instances_ips
        )

    def _get_all_integration_config(self, instances_ips: list) -> Optional[list]:
        """
        Gets all integration configuration as it exists on the demisto server
        because if all packs are installed the data returned from this request is very heavy, and we want to avoid
        running it in multiple threads.
        Args:
            instances_ips: the instances urls
        Returns:
            A dict containing the configuration for the integration if found, else empty list
        """
        if not self.is_nightly:
            return []
        url = instances_ips[0]
        server_url = url if self.is_saas_server_type else f"https://{url}"
        return self.get_all_installed_integrations_configurations(server_url)

    def get_all_installed_integrations_configurations(
        self, server_url: str, timeout: int = 180, sleep_interval: int = 5
    ) -> list:
        """
        Gets all integration configuration as it exists on the demisto server
        Args:
            server_url: The url of the server to create integration in.
            timeout: The timeout to wait for the incident to be created.
            sleep_interval: The interval to sleep between each poll.

        Returns:
            A dict containing the configuration for the integration if found else empty list
        """
        if self.is_saas_server_type:
            # In XSIAM or XSOAR SAAS - We don't use demisto username
            os.environ.pop("DEMISTO_USERNAME", None)
        tmp_client = demisto_client.configure(
            base_url=server_url,
            auth_id=self.auth_id,
            api_key=self.api_key,
            verify_ssl=False,
        )
        self.logging_module.debug("Getting all integrations instances")

        end_time = time.time() + timeout
        while True:
            try:
                response, _, _ = demisto_client.generic_request_func(
                    self=tmp_client,
                    path="/settings/integration/search",
                    method="POST",
                    body={},
                    response_type="object",
                )
                if "configurations" in response:
                    return response["configurations"]
            except ApiException:
                self.logging_module.exception(
                    "failed to get all integrations configuration"
                )
            if time.time() > end_time:
                self.logging_module.error(
                    "Timeout - failed to get all integration configuration."
                )
                return []

            time.sleep(sleep_interval)

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
        all_tests = self._get_all_tests()
        # In XSIAM or XSOAR SAAS - Set all tests to unmockable.
        unmockable_tests = []
        if self.server or not self.isAMI or self.is_saas_server_type:
            unmockable_tests = all_tests
            self.unmockable_test_ids = {test.playbook_id for test in all_tests}
        elif self.isAMI:
            unmockable_tests = self.conf_unmockable_tests
            self.unmockable_test_ids = {
                test.playbook_id for test in self.conf_unmockable_tests
            }
        self.logging_module.debug(
            f"Unmockable tests selected: {pformat(self.unmockable_test_ids)}"
        )
        mockable_tests = [
            test
            for test in all_tests
            if test.playbook_id not in self.unmockable_test_ids
        ]
        self.logging_module.debug(
            f"Mockable tests selected: {pformat([test.playbook_id for test in mockable_tests])}"
        )
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
        with open(FILTER_CONF) as filter_file:
            filtered_tests = [line.strip("\n") for line in filter_file.readlines()]

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
            unmockable_integrations_used = [
                integration_name
                for integration_name in test_record.test_integrations
                if integration_name in unmockable_integrations
            ]
            if (
                test_name
                and (not test_record.test_integrations or unmockable_integrations_used)
                or not self.isAMI
            ):
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

    def _get_instances_ips(self) -> List[str]:
        """
        Parses the env_results.json and extracts the instance ip from each server configured in it.
        Returns:
            A list contains server internal ips.
        """
        if self.server:
            return [self.server]
        if self.is_saas_server_type:
            return [env.get("base_url") for env in self.env_json]
        return [
            env.get("InstanceDNS")
            for env in self.env_json
            if env.get("Role") == self.server_version
        ]

    @staticmethod
    def _parse_tests_list_arg(tests_list: str):
        """
        Parses the test list arguments if present.

        :param tests_list: CSV string of tests to run.
        :return: List of tests if there are any, otherwise empty list.
        """
        return tests_list.split(",") if tests_list else []

    @staticmethod
    def _load_env_results_json():
        if not Path(ENV_RESULTS_PATH).is_file():
            return {}

        with open(ENV_RESULTS_PATH) as json_file:
            return json.load(json_file)

    def _get_server_numeric_version(self) -> str:
        """
        Gets the current server version

        Returns:
            Server numeric version
        """
        default_version = "99.99.98"
        if self.is_local_run:
            self.logging_module.info(
                f"Local run, assuming server version is {default_version}",
                real_time=True,
            )
            return default_version

        if not self.env_json:
            self.logging_module.warning(
                f"Did not find {ENV_RESULTS_PATH} file, assuming server version is {default_version}.",
                real_time=True,
            )
            return default_version

        server_version_mapping = {
            "Server 5.0": "5.0.0",
            "Server 5.5": "5.5.0",
            "Server 6.0": "6.0.0",
            "Server 6.1": "6.1.0",
            "Server 6.2": "6.2.0",
            "Server 6.5": "6.5.0",
            "Server 6.6": "6.6.0",
            "Server 6.8": "6.8.0",
            "Server 6.9": "6.9.0",
            "Server 6.10": "6.10.0",
            "Server 6.11": "6.11.0",
            "Server 6.12": "6.12.0",
            "Server Master": default_version,
            "XSIAM 1.2": "6.9.0",
            "XSIAM Master": default_version,
        }
        server_numeric_version = server_version_mapping.get(
            self.server_version, default_version
        )
        self.logging_module.info(
            f"Server version: {server_numeric_version}", real_time=True
        )
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
        url = f"https://circleci.com/api/v1.1/project/github/demisto/content/{self.build_number}"
        res = self._http_request(url, params_dict={"circle-token": self.circleci_token})

        user_details = res.get("user", {})
        return user_details.get("name", "")

    @staticmethod
    def _http_request(url, params_dict=None):
        res = requests.request(
            "GET",
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
        user_id = ""
        try:
            user_name = (
                os.getenv("GITLAB_USER_LOGIN") or self._get_user_name_from_circle()
            )
            res = self.slack_client.api_call("users.list")

            user_list = res.get("members", [])  # type: ignore
            for user in user_list:
                profile = user.get("profile", {})
                name = profile.get("real_name_normalized", "")
                if name == user_name:
                    user_id = user.get("id", "")
        except Exception as exc:
            logging.debug(f"failed to retrieve the slack user ID.\nError: {exc}")

        return user_id


class TestResults:
    def __init__(self, unmockable_integrations, artifacts_path: str):
        self.succeeded_playbooks: List[str] = []
        self.failed_playbooks: Set[str] = set()
        self.playbook_report: Dict[str, List[Dict[Any, Any]]] = {}
        self.skipped_tests: Dict[str, str] = {}
        self.skipped_integrations: Dict[str, str] = {}
        self.rerecorded_tests: List[str] = []
        self.empty_files: List[str] = []
        self.test_results_xml_file = JUnitXml()
        self.unmockable_integrations = unmockable_integrations
        self.playbook_skipped_integration: Set[str] = set()
        self.artifacts_path = Path(artifacts_path)

    def add_proxy_related_test_data(self, proxy):
        # Using multiple appends and not extend since append is guaranteed to be thread safe
        for playbook_id in proxy.rerecorded_tests:
            self.rerecorded_tests.append(playbook_id)
        for playbook_id in proxy.empty_files:
            self.empty_files.append(playbook_id)

    def write_artifacts_file(self, file_name: str, content: Iterable[str]):
        with open(self.artifacts_path / file_name, "w") as file:
            file.write("\n".join(content))

    def create_result_files(self):
        self.write_artifacts_file("succeeded_tests.txt", self.succeeded_playbooks)
        self.write_artifacts_file("failed_tests.txt", self.failed_playbooks)
        self.write_artifacts_file("skipped_tests.txt", self.skipped_tests)
        self.write_artifacts_file("skipped_integrations.txt", self.skipped_integrations)
        with open(
            self.artifacts_path / "test_playbooks_report.json", "w"
        ) as test_playbooks_report_file:
            json.dump(self.playbook_report, test_playbooks_report_file, indent=4)

        self.test_results_xml_file.write(
            (self.artifacts_path / "test_playbooks_report.xml").as_posix(), pretty=True
        )

    def print_test_summary(
        self,
        is_ami: bool = True,
        logging_module: Union[Any, ParallelLoggingManager] = logging,
    ):
        """
        Takes the information stored in the tests_data_keeper and prints it in a human-readable way.
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
        logging_module.info("TEST RESULTS:")
        logging_module.info(
            f"Number of playbooks tested - {succeed_count + failed_count}"
        )
        if succeed_count:
            logging_module.success(f"Number of succeeded tests - {succeed_count}")
            logging_module.success(
                "Successful Tests: {}".format(
                    "".join(
                        [
                            f"\n\t\t\t\t\t\t\t - {playbook_id}"
                            for playbook_id in succeed_playbooks
                        ]
                    )
                )
            )
        if rerecorded_count > 0:
            logging_module.debug(
                f"Number of tests with failed playback and successful re-recording - {rerecorded_count}"
            )
            logging_module.debug(
                "Tests with failed playback and successful re-recording: {}".format(
                    "".join(
                        [
                            f"\n\t\t\t\t\t\t\t - {playbook_id}"
                            for playbook_id in rerecorded_tests
                        ]
                    )
                )
            )

        if empty_mocks_count > 0:
            logging_module.debug(
                f"Successful tests with empty mock files count- {empty_mocks_count}:\n"
            )
            proxy_explanation = (
                "\t\t\t\t\t\t\t (either there were no http requests or no traffic is passed through the proxy.\n"
                "\t\t\t\t\t\t\t Investigate the playbook and the integrations.\n"
                "\t\t\t\t\t\t\t If the integration has no http traffic, add to unmockable_integrations in conf.json)"
            )
            logging_module.debug(proxy_explanation)
            logging_module.debug(
                "Successful tests with empty mock files: {}".format(
                    "".join(
                        [
                            f"\n\t\t\t\t\t\t\t - {playbook_id}"
                            for playbook_id in empty_files
                        ]
                    )
                )
            )

        if skipped_integration:
            self.print_table(
                "Skipped Integrations", skipped_integration, logging_module.debug
            )

        if skipped_tests:
            self.print_table("Skipped Tests", skipped_tests, logging_module.debug)

        if unmocklable_integrations:
            self.print_table(
                "Unmockable Integrations",
                unmocklable_integrations,
                logging_module.debug,
            )

        if failed_count:
            logging_module.error(f"Number of failed tests - {failed_count}:")
            logging_module.error(
                "Failed Tests: {}".format(
                    "".join(
                        [
                            f"\n\t\t\t\t\t\t\t - {playbook_id}"
                            for playbook_id in failed_playbooks
                        ]
                    )
                )
            )

    @staticmethod
    def print_table(table_name: str, table_data: dict, logging_method: Callable):
        table = prettytable.PrettyTable()
        table.field_names = ["Index", "Name", "Reason"]
        for index, record in enumerate(table_data, start=1):
            row = [index, record, table_data[record]]
            table.add_row(row)
        logging_method(f"{table_name}:\n{table}", real_time=True)


class Integration:
    def __init__(
        self,
        build_context: BuildContext,
        integration_name: str,
        potential_integration_instance_names: list,
        playbook: TestPlaybook,
    ):
        """
        An integration class that should represent the integrations during the build
        Args:
            build_context: The context of the build
            integration_name: The name of the integration
            potential_integration_instance_names: A list of instance names, one of those names should be the actual reason,
            but we won't know for sure until we will try to filter it with conf.json.
            playbook: The playbook that triggered the integration configuration.
        """
        self.playbook = playbook
        self.build_context = build_context
        self.name = integration_name
        self.instance_names = potential_integration_instance_names
        self.instance_name = ""
        self.configuration: Optional[
            IntegrationConfiguration
        ] = IntegrationConfiguration({"name": self.name, "params": {}})
        self.docker_image: list = []
        self.integration_configuration_from_server: dict = {}
        self.integration_type: str = ""
        self.module_instance: dict = {}

    @staticmethod
    def _change_placeholders_to_values(
        server_url: str, config_item: IntegrationConfiguration
    ) -> IntegrationConfiguration:
        """Some integration should be configured on the current server as host and has the string '%%SERVER_HOST%%'
        in the content-test-conf conf.json configuration.
        This method replaces these placeholders in the configuration to their real values

        Args:
            server_url: The server url that should be inserted instead of the placeholder in the configuration params
            config_item: Integration configuration object.

        Returns:
            IntegrationConfiguration class with the modified params
        """
        placeholders_map = {"%%SERVER_HOST%%": server_url}
        item_as_string = json.dumps(config_item.params)
        for key, value in placeholders_map.items():
            item_as_string = item_as_string.replace(key, value)
        config_item.params = json.loads(item_as_string)
        return config_item

    def _set_integration_params(
        self, server_url: str, playbook_id: str, is_mockable: bool
    ) -> bool:
        """
        Finds the matching configuration for the integration in content-test-data conf.json file
        in accordance with the configured instance name if exist and configures the proxy parameter if needed
        Args:
            server_url: The url of the demisto server to configure the integration in
            playbook_id: The ID of the playbook for which the integration should be configured
            is_mockable: Should the proxy parameter be set to True or not

        Returns:
            True if found a matching configuration else False if found more than one configuration candidate returns False
        """
        self.playbook.log_debug(f"Searching integration configuration for {self}")

        # Finding possible configuration matches
        integration_params: List[IntegrationConfiguration] = [
            deepcopy(conf)
            for conf in self.build_context.secret_conf.integrations
            if conf.name == self.name
        ]
        # Modifying placeholders if exists
        integration_params: List[IntegrationConfiguration] = [
            self._change_placeholders_to_values(server_url, conf)
            for conf in integration_params
        ]
        if self.name == "Core REST API":
            self.configuration.params = {  # type: ignore
                "url": server_url
                if self.build_context.is_saas_server_type
                else "https://localhost",
                "creds_apikey": {
                    "identifier": str(self.build_context.auth_id)
                    if self.build_context.is_saas_server_type
                    else "",
                    "password": self.build_context.api_key,
                },
                "auth_method": "Standard",
                "insecure": True,
            }
        elif integration_params:
            # If we have more than one configuration for this integration - we will try to filter by instance name
            if len(integration_params) != 1:
                found_matching_instance = False
                for item in integration_params:
                    if item.instance_name in self.instance_names:
                        self.configuration = item
                        found_matching_instance = True
                        break

                if not found_matching_instance:
                    optional_instance_names = [
                        optional_integration.instance_name
                        for optional_integration in integration_params
                    ]
                    error_msg = FAILED_MATCH_INSTANCE_MSG.format(
                        playbook_id,
                        len(integration_params),
                        self.name,
                        "\n".join(optional_instance_names),
                    )
                    self.playbook.log_error(error_msg)
                    return False
            else:
                self.configuration = integration_params[0]

        if is_mockable:
            self.playbook.log_debug(f"Configuring {self} with proxy params")
            for param in ("proxy", "useProxy", "useproxy", "insecure", "unsecure"):
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
            match_configurations = [
                x
                for x in self.build_context.all_integrations_configurations
                if x["name"] == self.name
            ]
        else:
            all_configurations = (
                self.build_context.get_all_installed_integrations_configurations(
                    server_url
                )
            )
            match_configurations = [
                x for x in all_configurations if x["name"] == self.name
            ]

        if not match_configurations:
            self.playbook.log_error("Integration was not found")
            return None

        return deepcopy(match_configurations[0])

    def _delete_integration_instance_if_determined_by_name(
        self, client: DefaultApi, instance_name: str
    ):
        """Deletes integration instance by its name.

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
            response, status_code, headers = demisto_client.generic_request_func(
                self=client,
                method="POST",
                path="/settings/integration/search",
                body={"size": 1000},
                response_type="object",
            )
        except ApiException:
            self.playbook.log_exception(
                f"Failed to delete integration {self} instance, error trying to communicate with demisto server"
            )
            return
        if status_code != requests.codes.ok:
            self.playbook.log_error(
                f"Get integration {self} instance failed - response:{pformat(response)}, "
                f"status code:{status_code} headers:{headers}"
            )
            return
        if "instances" not in response:
            self.playbook.log_info(
                f"No integrations instances found to delete for {self}"
            )
            return

        for instance in response["instances"]:
            if instance.get("name") == instance_name:
                self.playbook.log_info(
                    f"Deleting integration instance {instance_name} since it is defined by name"
                )
                self.delete_integration_instance(client, instance.get("id"))

    def _set_server_keys(self, client: DefaultApi, server_context: "ServerContext"):
        """In case the params of the test has 'server_keys' key:
            Resets containers
            Adds server configuration keys using the demisto_client.

        Args:
            client (demisto_client): The configured client to use.
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in
        """
        if "server_keys" not in self.configuration.params:  # type: ignore
            return

        server_context.reset_containers()

        self.playbook.log_debug(f"Setting server keys for integration: {self}")

        data = {"data": {}, "version": -1}

        for key, value in self.configuration.params.get("server_keys").items():  # type: ignore
            data["data"][key] = value  # type: ignore

        _, _, prev_system_conf = update_server_configuration(
            client=client,
            server_configuration=self.configuration.params.get("server_keys"),  # type: ignore
            error_msg="Failed to set server keys",
            logging_manager=self.build_context.logging_module,
        )
        server_context.prev_system_conf = prev_system_conf

    def create_module(
        self,
        instance_name: str,
        configuration: dict,
        incident_configuration: dict = None,
    ) -> Dict[str, Any]:
        module_configuration = configuration["configuration"]

        # If incident_type is given in Test Playbook configuration on test-conf, we change the default configuration.
        if incident_configuration and incident_configuration.get("incident_type"):
            incident_type_configuration = list(
                filter(
                    lambda config: config.get("name") == "incidentType",
                    module_configuration,
                )
            )

            incident_type_configuration[0]["value"] = incident_configuration.get(
                "incident_type"
            )

        module_instance = {
            "brand": configuration["name"],
            "category": configuration["category"],
            "configuration": configuration,
            "data": [],
            "enabled": "true",
            "engine": "",
            "id": "",
            "isIntegrationScript": self.configuration.is_byoi,  # type: ignore
            "name": instance_name,
            "passwordProtected": False,
            "version": 0,
            "incomingMapperId": configuration.get("defaultMapperIn", ""),
            "mappingId": configuration.get("defaultClassifier", ""),
            "outgoingMapperId": configuration.get("defaultMapperOut", ""),
        }

        # If default mapper or classifier are given in test-conf we ignore defaultMapperIn or defaultClassifier from yml.
        if incident_configuration and incident_configuration.get("classifier_id"):
            module_instance["mappingId"] = incident_configuration.get("classifier_id")
        if incident_configuration and incident_configuration.get("incoming_mapper_id"):
            module_instance["incomingMapperId"] = incident_configuration.get(
                "incoming_mapper_id"
            )

        return module_instance

    def create_integration_instance(
        self,
        client: DefaultApi,
        playbook_id: str,
        is_mockable: bool,
        server_context: "ServerContext",
        instance_configuration: dict,
    ) -> bool:
        """
        Create an instance of the integration in the server specified in the demisto client instance.
        Args:
            instance_configuration: The configuration of the instance to create.
            client: The demisto_client instance to use.
            playbook_id: The playbook id for which the instance should be created.
            is_mockable: Indicates whether the integration should be configured with proxy=True or not.
            server_context (ServerContext): The ServerContext instance in which the TestContext instance is created in.

        Returns:
            The integration configuration as it exists on the server after it was configured
        """
        server_url = client.api_client.configuration.host
        self._set_integration_params(server_url, playbook_id, is_mockable)
        configuration = self._get_integration_config(
            client.api_client.configuration.host
        )
        if not configuration:
            self.playbook.log_error(
                f"Could not find configuration for integration {self}"
            )
            return False

        module_configuration = configuration["configuration"] or []

        if "integrationInstanceName" in self.configuration.params:  # type: ignore
            instance_name = self.configuration.params["integrationInstanceName"]  # type: ignore
            self._delete_integration_instance_if_determined_by_name(
                client, instance_name
            )
        else:
            instance_name = f'{self.configuration.instance_name.replace(" ", "_")}_test_{uuid.uuid4()}'  # type: ignore

        self.playbook.log_info(
            f"Configuring instance for {self} (instance name: {instance_name}, "  # type: ignore
            f'validate "test-module": {self.configuration.should_validate_test_module})'
        )

        # define module instance:
        params = self.configuration.params  # type: ignore

        module_instance = self.create_module(
            instance_name, configuration, instance_configuration
        )

        # set server keys
        if not self.build_context.is_saas_server_type:
            self._set_server_keys(client, server_context)

        # set module params
        for param_conf in module_configuration:
            if param_conf["display"] in params or param_conf["name"] in params:
                # param defined in conf
                key = (
                    param_conf["display"]
                    if param_conf["display"] in params
                    else param_conf["name"]
                )
                if key in {"credentials", "creds_apikey"}:
                    credentials = params[key]
                    param_value = {
                        "credential": "",
                        "identifier": credentials.get("identifier", ""),
                        "password": credentials["password"],
                        "passwordChanged": False,
                    }
                else:
                    param_value = params[key]

                param_conf["value"] = param_value
                param_conf["hasvalue"] = True
            elif param_conf["defaultValue"]:
                # param is required - take default value
                param_conf["value"] = param_conf["defaultValue"]
            module_instance["data"].append(param_conf)
        try:
            response, status_code, headers = demisto_client.generic_request_func(
                self=client,
                method="PUT",
                path="/settings/integration",
                body=module_instance,
                response_type="object",
            )
        except ApiException:
            self.playbook.log_exception(
                f"Error trying to create instance for integration: {self}"
            )
            return False

        if status_code not in {requests.codes.ok, requests.codes.no_content}:
            self.playbook.log_error(
                f"create instance failed - response:{pformat(response)}, status code:{status_code} headers:{headers}"
            )
            return False

        self.integration_configuration_from_server = response
        self.module_instance = module_instance
        integration_script = (
            response.get("configuration", {}).get("integrationScript", {}) or {}
        )
        self.integration_type = integration_script.get("type", "")
        return True

    def delete_integration_instance(
        self, client, instance_id: Optional[str] = None
    ) -> bool:
        """
        Deletes an integration with the given ID
        Args:
            client: Demisto client instance
            instance_id: The instance ID to Delete

        Returns:
            True if integration was deleted else False
        """
        self.playbook.log_debug(f"Deleting {self} instance")
        instance_id = instance_id or self.integration_configuration_from_server.get(
            "id"
        )
        if not instance_id:
            self.playbook.log_info(
                f"No instance ID for integration {self} was supplied, not deleting any instances."
            )
            return True
        try:
            res = demisto_client.generic_request_func(
                self=client,
                method="DELETE",
                path=f"/settings/integration/{urllib.parse.quote(instance_id)}",
            )
        except ApiException:
            self.playbook.log_exception(
                "Failed to delete integration instance, error trying to communicate with the server."
            )
            return False
        if int(res[1]) != requests.codes.ok:
            self.playbook.log_error(
                f"delete integration instance failed\nStatus code {res[1]}"
            )
            self.playbook.log_error(pformat(res))
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
            self.playbook.log_debug(
                f'Skipping test-module on {self} because the "validate_test" flag is set to False'
            )
            return True

        connection_retries = 3
        status_code = 0
        response = None
        integration_of_instance = self.integration_configuration_from_server.get(
            "brand", ""
        )
        instance_name = self.integration_configuration_from_server.get("name", "")
        self.playbook.log_info(
            f'Running "test-module" for instance "{instance_name}" of integration "{integration_of_instance}".'
        )
        for i in range(connection_retries):
            try:
                response, status_code, headers = demisto_client.generic_request_func(
                    self=client,
                    method="POST",
                    path="/settings/integration/test",
                    body=self.module_instance,
                    _request_timeout=120,
                    response_type="object",
                )
                break
            except ApiException:
                self.playbook.log_exception(
                    f"Failed to test integration {self} instance, error trying to communicate with demisto server: "
                    f"{get_ui_url(client.api_client.configuration.host)}"
                )
                return False
            except ReadTimeoutError:
                self.playbook.log_warning(
                    f"Could not connect. Trying to connect for the {i + 1} time"
                )

        if status_code != requests.codes.ok:
            self.playbook.log_error(
                f"Integration-instance test-module failed. Bad status code: {status_code}.\n"
                f"Sever URL: {get_ui_url(client.api_client.configuration.host)}"
            )
            return False

        if not (success := bool(response.get("success"))):  # type: ignore[union-attr]
            failure_message = response.get("message")  # type: ignore[union-attr]
            server_url = get_ui_url(client.api_client.configuration.host)
            test_failed_msg = (
                f"Test integration failed - server: {server_url}.\n"
                f"Failure message: {failure_message}"
                if failure_message
                else " No failure message."
            )
            self.playbook.log_error(test_failed_msg)
        return success

    def disable_integration_instance(self, client):
        """Disables the integration
        Args:
            client: The demisto_client instance to use

        Returns:
            The integration configuration as it exists on the server after it was configured
        """
        # tested with POSTMAN, this is the minimum required fields for the request.
        module_instance = {
            key: self.integration_configuration_from_server[key]
            for key in [
                "id",
                "brand",
                "name",
                "data",
                "isIntegrationScript",
            ]
        }
        module_instance["enable"] = "false"
        module_instance["version"] = -1
        self.playbook.log_debug(
            f'Disabling integration instance "{module_instance.get("name")}"'
        )
        try:
            response, status_code, headers = demisto_client.generic_request_func(
                self=client,
                method="PUT",
                path="/settings/integration",
                body=module_instance,
            )
        except ApiException:
            self.playbook.log_exception("Failed to disable integration instance")
            return

        if status_code not in {requests.codes.ok, requests.codes.no_content}:
            self.playbook.log_error(
                f"disable instance failed - response:{pformat(response)}, status code:{status_code} headers:{headers}"
            )

    def get_docker_images(self) -> List[str]:
        """
        Gets the docker image name from the configured integration instance's body if such body exists
        Returns:

        """
        if self.integration_configuration_from_server:
            return Docker.get_integration_image(
                self.integration_configuration_from_server
            )
        else:
            raise Exception(
                "Cannot get docker image - integration instance was not created yet"
            )

    def __str__(self):
        return f'"{self.name}"'

    def __repr__(self):
        return str(self)


class TestContext:
    def __init__(
        self,
        build_context: BuildContext,
        playbook: TestPlaybook,
        client: DefaultApi,
        server_context: "ServerContext",
    ):
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

    def _get_investigation_playbook_state(self) -> str:
        """
        Queried the server for the current status of the test's investigation
        Returns:
            A string representing the status of the playbook
        """
        try:
            response, _, _ = demisto_client.generic_request_func(
                self=self.client,
                method="GET",
                path=f"/inv-playbook/{self.incident_id}",
                response_type="object",
            )
        except ApiException as err:

            self.playbook.log_debug(f"{err=}", real_time=True)
            self.playbook.log_debug(f"{err.status=}", real_time=True)
            if err.status == 401:
                # resetting client due to possible session timeouts
                self.server_context.configure_new_client()
                self.playbook.log_debug(
                    f"new demisto_client created because of err: {err}", real_time=True
                )
                # after resetting client, playbook's state should still be in progress
                return PB_Status.IN_PROGRESS
            # if a different error other than 401 was returned, we log the exception and fail the test playbook.
            else:
                self.playbook.log_exception(
                    f"Failed to get investigation playbook state, "
                    f"error trying to communicate with demisto server: {err}",
                    real_time=True,
                )
                return PB_Status.FAILED

        try:
            return response["state"]
        except Exception:
            # setting state to `in progress` in XSIAM build,
            # Because `investigation_playbook` returned empty if xsiam investigation is still in progress.
            return (
                PB_Status.IN_PROGRESS
                if self.build_context.is_saas_server_type
                else PB_Status.NOT_SUPPORTED_VERSION
            )

    def _collect_docker_images(self):
        """
        Collects docker images of the playbook's integration.
        This method can be called only after the integrations were configured in the server.
        """
        for integration in self.playbook.integrations:
            if docker_images := integration.get_docker_images():
                self.test_docker_images.update(docker_images)
        self.playbook.test_suite.add_property(
            "test_docker_images", ",".join(self.test_docker_images)
        )

    def _print_investigation_error(self):
        try:
            response, status_code, headers = demisto_client.generic_request_func(
                self=self.client,
                method="POST",
                path=f"/investigation/{urllib.parse.quote(self.incident_id)}",  # type: ignore[arg-type]
                body={"pageSize": 1000},
                response_type="object",
            )
            if response and status_code == requests.codes.ok:
                entries = response["entries"]

                self.playbook.log_error(f"Playbook {self.playbook} has failed:")
                for entry in entries:
                    if entry["type"] == ENTRY_TYPE_ERROR and entry["parentContent"]:
                        self.playbook.log_error(f'- Task ID: {entry["taskId"]}')
                        # Checks for passwords and replaces them with "******"
                        parent_content = re.sub(
                            r' ([Pp])assword="[^";]*"',
                            " password=******",
                            entry["parentContent"],
                        )
                        self.playbook.log_error(f"  Command: {parent_content}")
                        self.playbook.log_error(f'  Body:\n{entry["contents"]}')
            else:
                self.playbook.log_error(
                    f"Failed getting entries for investigation: {self.incident_id} - response:{pformat(response)}, "
                    f"status code:{status_code} headers:{headers}"
                )
        except ApiException:
            self.playbook.log_exception(
                "Failed to print investigation error, error trying to communicate with demisto server"
            )

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
                playbook_state = "Pending"
                self.playbook.log_exception(
                    "Error when trying to get investigation playbook state"
                )

            if playbook_state in (PB_Status.COMPLETED, PB_Status.NOT_SUPPORTED_VERSION):
                break
            if playbook_state == PB_Status.FAILED:
                self.playbook.log_error(f"{self.playbook} failed with error/s")
                self._print_investigation_error()
                break
            if time.time() > timeout:
                self.playbook.log_error(f"{self.playbook} failed on timeout")
                break

            if number_of_attempts % DEFAULT_INTERVAL == 0:
                msg = f"{self.playbook} loop no. {number_of_attempts // DEFAULT_INTERVAL}, {playbook_state=}"
                self.playbook.log_info(msg)

            number_of_attempts = number_of_attempts + 1
        return playbook_state

    def replace_external_playbook_configuration(
        self,
        external_playbook_configuration: dict,
        server_version: Version,
    ):
        """takes external configuration of shape {"playbookID": "Isolate Endpoint - Generic V2",
                                               "input_parameters":{"Endpoint_hostname": {"simple", "test"}}}
        and changes the specified playbook configuration to the mentioned one.
        If playbook's inputs had changed, revert will be needed.
        Returns (Whether the Playbook changed, The values to restore, the path to use when restoring)
        Only to be used with server version 6.2 and above."""

        # Checking configuration
        if not external_playbook_configuration:
            self.playbook.log_info(
                "External Playbook Configuration not provided, skipping re-configuration."
            )
            return False, {}, ""

        if Version(server_version.base_version) < Version("6.2.0"):  # type: ignore
            self.playbook.log_info(
                "External Playbook not supported in versions previous to 6.2.0, skipping re-configuration."
            )
            return False, {}, ""

        self.playbook.log_info("External Playbook in use, starting re-configuration.")

        # Getting current configuration
        external_playbook_id = external_playbook_configuration["playbookID"]
        external_playbook_path = f"/playbook/{external_playbook_id}"
        response, _, _ = demisto_client.generic_request_func(
            self.client,
            method="GET",
            path=external_playbook_path,
            response_type="object",
        )

        inputs = response.get("inputs", [])
        if not inputs:
            raise Exception(
                f"External Playbook {external_playbook_id} was not found or has no inputs."
            )

        # Save current for default Configuration.
        inputs_default = deepcopy(inputs)
        self.playbook.log_info("Saved current configuration.")

        changed_keys = []
        failed_keys = []

        # Change Configuration for external pb.
        for input_ in external_playbook_configuration["input_parameters"]:
            if matching_record := list(
                filter(lambda x: x.get("key") == input_, inputs)
            ):
                existing_val = matching_record[0]
                simple = external_playbook_configuration["input_parameters"][
                    input_
                ].get("simple")
                complex_parameter = external_playbook_configuration["input_parameters"][
                    input_
                ].get("complex")

                # If no value (simple or complex) was found, It is a typo
                if complex_parameter is None and simple is None:
                    raise Exception(
                        f"Could not find neither a `simple` nor `complex` value for {external_playbook_id}, field: {input_}. "
                        "A valid configuration should be of the following format: "
                        '{<param name>: {"simple", <required value>}}'
                    )

                existing_val["value"]["simple"] = simple
                existing_val["value"]["complex"] = complex_parameter
                changed_keys.append(input_)

            else:
                failed_keys.append(input_)

        if failed_keys:
            raise Exception(
                f'Some input keys was not found in playbook {external_playbook_id}: {",".join(failed_keys)}.'
            )

        self.playbook.log_info(
            f"Changing keys in {external_playbook_id}: {changed_keys}."
        )
        saving_inputs_path = f"/playbook/inputs/{external_playbook_id}"

        try:
            if changed_keys:
                if Version(server_version.base_version) >= Version("8.5.0"):
                    self.playbook.log_info(
                        "Sending request replace playbook configuration to server with version >= 8.5.0"
                    )
                    demisto_client.generic_request_func(
                        self.client,
                        method="POST",
                        path=saving_inputs_path,
                        body={"inputs": inputs},
                    )
                else:
                    self.playbook.log_info(
                        "Sending request replace playbook configuration to server with version < 8.5.0"
                    )
                    demisto_client.generic_request_func(
                        self.client, method="POST", path=saving_inputs_path, body=inputs
                    )

        except Exception as e:
            raise Exception(
                f"Could not change inputs in playbook {external_playbook_id} configuration. Error: {e}"
            ) from e

        self.playbook.log_info(
            f"Re-configured {external_playbook_id} successfully with {len(changed_keys)} new values."
        )

        return True, inputs_default, saving_inputs_path

    def restore_external_playbook_configuration(
        self, restore_path: str, restore_values: dict, server_version: Version
    ):
        self.playbook.log_info("Restoring External Playbook parameters.")

        if Version(server_version.base_version) >= Version("8.5.0"):
            self.playbook.log_info(
                "Sending request restore playbook configuration to server with version >= 8.5.0"
            )
            demisto_client.generic_request_func(
                self.client,
                method="POST",
                path=restore_path,
                body={"inputs": restore_values},
            )
        else:
            self.playbook.log_info(
                "Sending request restore playbook configuration to server with version < 8.5.0"
            )
            demisto_client.generic_request_func(
                self.client, method="POST", path=restore_path, body=restore_values
            )

        self.playbook.log_info("Restored External Playbook successfully.")

    def _run_incident_test(self) -> str:
        """
        Creates an incident in demisto server and return its status
        Returns:
            Empty string or
        """

        # Checking server version
        server_version = get_demisto_version(self.client)

        try:
            instance_configuration = self.playbook.configuration.instance_configuration

            if not self.playbook.configure_integrations(
                self.client, self.server_context, instance_configuration
            ):
                return PB_Status.CONFIGURATION_FAILED

            test_module_result = self.playbook.run_test_module_on_integrations(
                self.client
            )
            if not test_module_result:
                self.playbook.disable_integrations(self.client, self.server_context)
                return PB_Status.FAILED

            external_playbook_configuration = (
                self.playbook.configuration.external_playbook_config
            )

            # Change Configuration for external configuration if needed
            (
                restore_needed,
                default_vals,
                restore_path,
            ) = self.replace_external_playbook_configuration(
                external_playbook_configuration, server_version
            )

            incident = self.playbook.create_incident(self.client)
            if not incident:
                return ""

            self.incident_id = (
                incident.id
                if self.build_context.is_saas_server_type
                else incident.investigation_id
            )
            investigation_id = self.incident_id
            if investigation_id is None:
                self.playbook.log_error(
                    f"Failed to get investigation id of incident: {incident}"
                )
                return ""
            self.playbook.test_suite.add_property("investigation_id", investigation_id)

            self.playbook.log_info(
                f"Found incident with incident ID: {investigation_id}."
            )

            server_url = get_ui_url(self.client.api_client.configuration.host)
            if self.build_context.is_saas_server_type:
                self.playbook.log_info(
                    f"Investigation URL: {self.build_context.xsiam_ui_path}incident-view/alerts_and_insights?caseId="
                    f"{investigation_id}&action:openAlertDetails={investigation_id}-work_plan"
                )
            else:
                self.playbook.log_info(
                    f"Investigation URL: {server_url}/#/WorkPlan/{investigation_id}"
                )
            playbook_state = self._poll_for_playbook_state()
            self.playbook.log_info(
                f"Got incident: {investigation_id} status: {playbook_state}."
            )
            if self.playbook.configuration.context_print_dt:
                self.playbook.print_context_to_log(self.client, investigation_id)

            # restore Configuration for external playbook
            if restore_needed:
                self.restore_external_playbook_configuration(
                    restore_path=restore_path,
                    restore_values=default_vals,
                    server_version=server_version,
                )

            self.playbook.disable_integrations(self.client, self.server_context)
            self._clean_incident_if_successful(playbook_state)
            return playbook_state
        except Exception:
            self.playbook.log_exception(
                f"Failed to run incident test for {self.playbook}"
            )
            return PB_Status.FAILED

    def _clean_incident_if_successful(self, playbook_state: str):
        """
        Deletes the integration instances and the incident if the test was successful or failed on docker rate limit
        Args:
            playbook_state: The state of the playbook with which we can check if the test was successful
        """
        test_passed = playbook_state in (
            PB_Status.COMPLETED,
            PB_Status.NOT_SUPPORTED_VERSION,
        )
        # batchDelete is not supported in XSIAM, only close.
        # in XSIAM we are closing both successful and failed incidents
        if self.build_context.server_type == XSIAM_SERVER_TYPE and self.incident_id:
            self.playbook.close_incident(self.client, self.incident_id)
            self.playbook.delete_integration_instances(self.client)
        elif self.incident_id and test_passed:
            self.playbook.delete_incident(self.client, self.incident_id)
            self.playbook.delete_integration_instances(self.client)

    def _run_docker_threshold_test(self):
        self._collect_docker_images()
        if self.test_docker_images:
            memory_threshold, pid_threshold = self.get_threshold_values()
            if error_message := Docker.check_resource_usage(
                server_url=self.server_context.server_ip,
                docker_images=self.test_docker_images,
                def_memory_threshold=memory_threshold,
                def_pid_threshold=pid_threshold,
                docker_thresholds=self.build_context.conf.docker_thresholds,
                logging_module=self.build_context.logging_module,
            ):
                self.playbook.log_error(error_message)
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
        has_pwsh_integration = any(
            integration
            for integration in self.playbook.integrations
            if integration.integration_type == Docker.POWERSHELL_INTEGRATION_TYPE
        )
        if has_pwsh_integration:
            memory_threshold = max(
                Docker.DEFAULT_PWSH_CONTAINER_MEMORY_USAGE, memory_threshold
            )
            pid_threshold = max(Docker.DEFAULT_PWSH_CONTAINER_PIDS_USAGE, pid_threshold)
        return memory_threshold, pid_threshold

    def _send_slack_message(self, channel, text, user_name, as_user):
        self.build_context.slack_client.api_call(
            "chat.postMessage",
            json={
                "channel": channel,
                "username": user_name,
                "as_user": as_user,
                "text": text,
                "mrkdwn": "true",
            },
        )

    def _notify_failed_test(self):
        text = (
            f"{self.build_context.build_name} - {self.playbook} Failed\n"
            f"for more details browse into the following link\n"
            f"{get_ui_url(self.client.api_client.configuration.host)}"
        )
        text += f"/#/WorkPlan/{self.incident_id}" if self.incident_id else ""
        if self.build_context.slack_user_id:
            self.build_context.slack_client.api_call(
                "chat.postMessage",
                json={
                    "channel": self.build_context.slack_user_id,
                    "username": "Content CircleCI",
                    "as_user": "False",
                    "text": text,
                },
            )

    def _add_to_succeeded_playbooks(self):
        """
        Adds the playbook to the succeeded playbooks list
        """

        self.build_context.tests_data_keeper.succeeded_playbooks.append(
            self.playbook.configuration.playbook_id
        )
        self.playbook.close_test_suite()

    def _add_details_to_failed_tests_report(
        self, playbook_name: str, failed_stage: str
    ):
        """
        Adds the relevant details to the failed tests report.

        Args:
            playbook_name: The test's name.
            failed_stage: The stage where the test failed.
        """
        self.build_context.tests_data_keeper.playbook_report.setdefault(
            playbook_name, []
        ).append(
            {
                "number_of_executions": self.playbook.configuration.number_of_executions,
                "number_of_successful_runs": self.playbook.configuration.number_of_successful_runs,
                "failed_stage": failed_stage,
            }
        )

    @staticmethod
    def _get_failed_stage(
        status: Optional[str], is_second_playback_run: bool = False
    ) -> str:
        """
        Gets the test failed stage.

        Args:
            status: what is the test status.
            is_second_playback_run: Is The playbook run on a second playback after a freshly created record.
        """
        if is_second_playback_run:
            return "Second playback"
        if status == PB_Status.FAILED_DOCKER_TEST:
            return "Docker test"
        if status == PB_Status.CONFIGURATION_FAILED:
            return "Configuration"
        return "Execution"

    def _add_to_failed_playbooks(
        self, is_second_playback_run: bool = False, status: Optional[str] = None
    ):
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
            self.playbook.log_error(
                "Playback on newly created record has failed, see the following confluence page for help:\n"
                "https://confluence.paloaltonetworks.com/display/DemistoContent/Debug+Proxy-Related+Test+Failures"
            )
            playbook_name_to_add += " (Second Playback)"

        self._add_details_to_failed_tests_report(
            self.playbook.configuration.playbook_id, failed_stage
        )
        err = f"Test failed: {self}"
        self.playbook.log_error(err)
        self.build_context.tests_data_keeper.failed_playbooks.add(playbook_name_to_add)
        self.playbook.test_suite.add_property(
            "playbook_name_to_add", playbook_name_to_add
        )
        self.playbook.close_test_suite([Failure(err)])

    @staticmethod
    def _get_circle_memory_data() -> Tuple[str, str]:
        """
        Checks how many bytes are currently in use in the circle build instance
        Returns:
            The number of bytes in use
        """
        process = subprocess.Popen(
            ["cat", "/sys/fs/cgroup/memory/memory.usage_in_bytes"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()

    @staticmethod
    def _get_circle_processes_data() -> Tuple[str, str]:
        """
        Returns some data about the processes currently running in the circle build instance
        """
        process = subprocess.Popen(
            ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()

    def _send_circle_memory_and_pid_stats_on_slack(self):
        """
        Sends a Slack messages with the number of bytes currently in use and the number of processes currently in use
        """
        if (
            self.build_context.is_nightly
            and self.build_context.memCheck
            and not self.build_context.is_local_run
        ):
            stdout, stderr = self._get_circle_memory_data()
            text = stderr or f"Memory Usage: {stdout}"
            self._send_slack_message(
                SLACK_MEM_CHANNEL_ID, text, "Content CircleCI", "False"
            )
            stdout, stderr = self._get_circle_processes_data()
            text = stderr or stdout
            self._send_slack_message(
                SLACK_MEM_CHANNEL_ID, text, "Content CircleCI", "False"
            )

    def _incident_and_docker_test(self) -> str:
        """
        Runs incident and docker tests (the docker test is optional)
        Returns:
            The result of the test.
        """
        playbook_state = self._run_incident_test()
        # We don't want to run docker tests on redhat instance because it does not use docker, and it does not support
        # the threshold configurations.
        if (
            playbook_state == PB_Status.COMPLETED
            and self.server_context.is_instance_using_docker
        ) and not self.build_context.is_saas_server_type:
            #  currently not supported on XSIAM (CIAC-508)
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
            True if test has finished its execution else False
        """
        self.playbook.log_info(f"------ Test {self} start ------ (Mock: Disabled)")
        with acquire_test_lock(self.playbook) as lock:
            if lock:
                status = self._incident_and_docker_test()
                self.playbook.configuration.number_of_executions += 1
                self._update_playbook_status(status)
            else:
                return False
        return True

    def _update_complete_status(
        self,
        is_first_execution: bool,
        is_record_run: bool,
        is_first_playback_run: bool,
        is_second_playback_run: bool,
        use_retries_mechanism: bool,
        number_of_executions: int,
    ):
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

        self.playbook.log_success(f"PASS: {self} succeed")

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
            return self._update_status_based_on_retries_mechanism(
                number_of_executions, is_record_run
            )

        return PB_Status.COMPLETED

    def _update_failed_status(
        self,
        is_record_run: bool,
        is_first_playback_run: bool,
        is_second_playback_run: bool,
        use_retries_mechanism: bool,
        number_of_executions: int,
    ):
        """
        Handles the playbook failed status
        - Logs according to the results
        Args:
            is_record_run: whether it is a record execution.
            is_first_playback_run: whether it is the first playback execution.
            is_second_playback_run: whether it is the second playback execution.
            use_retries_mechanism: whether to use the retries' mechanism.
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
            return self._update_status_based_on_retries_mechanism(
                number_of_executions, is_record_run
            )

        # the test-playbook is considered a failed playbook.
        return PB_Status.FAILED

    def _update_status_based_on_retries_mechanism(
        self, number_of_executions, is_record_run
    ):
        """
        Updates the status of a test-playbook when using the retries' mechanism.
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
            self.playbook.log_info(
                f"Using the retries mechanism for test {self}.\n"
                f"Test-Playbook was executed {number_of_executions} times, more executions are needed."
            )
            self.build_context.test_retries_queue.put(self.playbook)
            return PB_Status.IN_PROGRESS

        else:  # number_of_executions == MAX_RETRIES:
            # check if in most executions, the test passed.
            if (
                self.playbook.configuration.number_of_successful_runs
                >= RETRIES_THRESHOLD
            ):
                # It's not enough that the record run will pass to declare the test as successful,
                # we need the second playback to pass as well.
                if is_record_run:
                    self.playbook.log_info(
                        f"Test-Playbook recording was executed {MAX_RETRIES} times, and passed {self.playbook.configuration.number_of_successful_runs} times."
                        f" Running second playback."
                    )
                    return PB_Status.SECOND_PLAYBACK_REQUIRED
                self.playbook.log_info(
                    f"Test-Playbook was executed {MAX_RETRIES} times, and passed {self.playbook.configuration.number_of_successful_runs} times."
                    f" Adding to succeeded playbooks."
                )
                return PB_Status.COMPLETED
            else:
                self.playbook.log_info(
                    f"Test-Playbook was executed {MAX_RETRIES} times, and passed only {self.playbook.configuration.number_of_successful_runs} times."
                    f" Adding to failed playbooks."
                )
                return PB_Status.FAILED

    def _update_playbook_status(
        self,
        status: str,
        is_first_playback_run: bool = False,
        is_second_playback_run: bool = False,
        is_record_run: bool = False,
    ) -> str:
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
        if status == PB_Status.COMPLETED:
            is_first_execution = number_of_executions == 1

            updated_status = self._update_complete_status(
                is_first_execution,
                is_record_run,
                is_first_playback_run,
                is_second_playback_run,
                use_retries_mechanism,
                number_of_executions,
            )

        elif status in (PB_Status.FAILED_DOCKER_TEST, PB_Status.CONFIGURATION_FAILED):
            self._add_to_failed_playbooks(status=status)
            return status

        else:  # test-playbook failed
            updated_status = self._update_failed_status(
                is_record_run,
                is_first_playback_run,
                is_second_playback_run,
                use_retries_mechanism,
                number_of_executions,
            )

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
            True if test has finished its execution else False
        """
        # we want to test first playback only once (we want to skip it when using retries mechanism)
        if (
            not self.playbook.configuration.is_first_playback_failed
            and proxy.has_mock_file(self.playbook.configuration.playbook_id)
        ):
            self.playbook.log_info(f"------ Test {self} start ------ (Mock: Playback)")
            with run_with_mock(
                proxy, self.playbook.configuration.playbook_id
            ) as result_holder:
                status = self._incident_and_docker_test()
                status = self._update_playbook_status(
                    status, is_first_playback_run=True
                )
                result_holder[RESULT] = status == PB_Status.COMPLETED
            if status in (PB_Status.COMPLETED, PB_Status.FAILED_DOCKER_TEST):
                return True
            self.playbook.log_warning(
                "Test failed with mock, recording new mock file. (Mock: Recording)"
            )
            self.playbook.configuration.is_first_playback_failed = True

        # Running on record mode since playback has failed or mock file was not found
        self.playbook.log_info(f"------ Test {self} start ------ (Mock: Recording)")
        with acquire_test_lock(self.playbook) as lock:
            if not lock:
                # If the integrations were not locked - the test has not finished its execution
                return False

            with run_with_mock(
                proxy, self.playbook.configuration.playbook_id, record=True
            ) as result_holder:
                status = self._incident_and_docker_test()
                self.playbook.configuration.number_of_executions += 1
                status = self._update_playbook_status(status, is_record_run=True)
                result_holder[RESULT] = status == PB_Status.SECOND_PLAYBACK_REQUIRED
        # Running playback after successful record to verify the record is valid for future runs
        if status == PB_Status.SECOND_PLAYBACK_REQUIRED:
            self.playbook.log_info(
                f"------ Test {self} start ------ (Mock: Second playback)"
            )
            with run_with_mock(
                proxy, self.playbook.configuration.playbook_id
            ) as result_holder:
                status = self._run_incident_test()
                self._update_playbook_status(status, is_second_playback_run=True)
                result_holder[RESULT] = status == PB_Status.COMPLETED
        return True

    def _is_runnable_on_current_server_instance(self) -> bool:
        """
        Nightly builds can have RHEL instances that uses podman instead of docker as well as the regular LINUX instance.
        In such case - if the test in runnable on docker instances **only** and the current instance uses podman -
        we will not execute the test under this instance and instead will return it to the queue in order to run
        it under some other instance
        Returns:
            True if this instance can be run on the current instance else False
        """
        if (
            self.playbook.configuration.runnable_on_docker_only
            and not self.server_context.is_instance_using_docker
        ):
            log_message = f"Skipping test {self.playbook} since it's not runnable on podman instances"
            self.playbook.log_debug(log_message)
            self.playbook.close_test_suite([Skipped(log_message)])

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
            return (
                self._execute_mockable_test(proxy)  # type: ignore[arg-type]
                if self.playbook.is_mockable
                else self._execute_unmockable_test()
            )
        except Exception:
            self.playbook.log_exception(
                f"Unexpected error while running test on playbook {self.playbook}"
            )
            self._add_to_failed_playbooks()
            return True
        finally:
            self.playbook.log_info(f"------ Test {self} end ------ \n")
            self.playbook.build_context.logging_module.execute_logs()

    def __str__(self):
        test_message = f"playbook: {self.playbook}"
        if self.playbook.integrations:
            test_message += f" with integration(s): {self.playbook.integrations}"
        else:
            test_message += " with no integrations"
        if not self.server_context.is_instance_using_docker:
            test_message += ", RedHat instance"
        return test_message

    def __repr__(self):
        return str(self)


class ServerContext:
    def __init__(
        self,
        build_context: BuildContext,
        server_private_ip: str,
        use_retries_mechanism: bool = True,
    ):
        self.build_context = build_context
        self.server_ip = server_private_ip
        if self.build_context.is_saas_server_type:
            self.server_url = server_private_ip
            # we use client without demisto username
            os.environ.pop("DEMISTO_USERNAME", None)
        else:
            self.server_url = f"https://{self.server_ip}"
        self.client: Optional[DefaultApi] = None
        self.configure_new_client()
        # currently not supported on XSIAM (CIAC-514)
        if self.build_context.is_saas_server_type:
            # In XSIAM or XSOAR SAAS - We're running without proxy. This code won't be executed on SaaS servers.
            self.proxy = None
        else:
            self.proxy = MITMProxy(
                server_private_ip,
                self.build_context.logging_module,
                build_number=self.build_context.build_number,
                branch_name=self.build_context.build_name,
            )
        self.is_instance_using_docker = not is_redhat_instance(self.server_ip)
        self.executed_tests: Set[str] = set()
        self.executed_in_current_round: Set[str] = set()
        self.prev_system_conf: dict = {}
        self.use_retries_mechanism: bool = use_retries_mechanism
        if self.build_context.is_saas_server_type:
            self.check_if_can_create_manual_alerts()

    def _execute_unmockable_tests(self):
        """
        Iterates the mockable tests queue and executes them as long as there are tests to execute
        """
        self._execute_tests(self.build_context.unmockable_tests_to_run)

    def _execute_tests(self, queue: Queue):
        """
        Iterates the tests queue and executes them as long as there are tests to execute.
        Before the tests execution starts we will reset the containers to make sure the proxy configuration is correct
        - We need it before the mockable tests because the server starts the python2 default container when it starts,
            and it has no proxy configurations.
        - We need it before the unmockable tests because at that point all containers will have the proxy configured,
            and we want to clean those configurations when testing unmockable playbooks
        Args:
            queue: The queue to fetch tests to execute from
        """
        self.reset_containers()
        while queue.unfinished_tasks:
            try:
                test_playbook: TestPlaybook = queue.get(block=False)
                self._reset_tests_round_if_necessary(test_playbook, queue)
            except Empty:
                continue
            self.configure_new_client()
            if TestContext(
                self.build_context, test_playbook, self.client, self
            ).execute_test(self.proxy):
                self.executed_tests.add(test_playbook.configuration.playbook_id)
            else:
                queue.put(test_playbook)
            queue.task_done()

    def _execute_mockable_tests(self):
        """
        Iterates the mockable tests queue and executes them as long as there are tests to execute
        """
        if self.proxy:
            self.proxy.configure_proxy_in_demisto(
                proxy=f"{self.proxy.ami.internal_ip}:{self.proxy.PROXY_PORT}",
                username=self.build_context.secret_conf.server_username,
                password=self.build_context.secret_conf.server_password,
                server=self.server_url,
            )
        self._execute_tests(self.build_context.mockable_tests_to_run)
        if self.proxy:
            self.proxy.configure_proxy_in_demisto(
                proxy="",
                username=self.build_context.secret_conf.server_username,
                password=self.build_context.secret_conf.server_password,
                server=self.server_url,
            )

    def _execute_failed_tests(self):
        self._execute_tests(self.build_context.test_retries_queue)

    def _reset_tests_round_if_necessary(
        self, test_playbook: TestPlaybook, queue_: Queue
    ):
        """
        Checks if the string representation of the current test configuration is already in
        the executed_in_current_round set.
        If it is- it means we have already executed this test, and we have reached a round and there are tests that
        were not able to be locked by this execution.
        In that case we want to start a new round monitoring by emptying the 'executed_in_current_round' set and sleep
        in order to let the tests be unlocked
        Since this operation can be performed by multiple threads - this operation is protected by the queue's lock
        Args:
            test_playbook: Test playbook to check if has been executed in the current round
            queue_: The queue from which the current tests are executed
        """
        queue_.mutex.acquire()
        if str(test_playbook.configuration) in self.executed_in_current_round:
            self.build_context.logging_module.info(
                "all tests in the queue were executed, sleeping for 30 seconds to let locked tests get unlocked."
            )
            self.executed_in_current_round = {str(test_playbook.configuration)}
            queue_.mutex.release()
            time.sleep(30)
            return
        else:
            self.executed_in_current_round.add(str(test_playbook.configuration))
        queue_.mutex.release()

    def configure_new_client(self):
        if self.client:
            self.client.api_client.pool.close()
            self.client.api_client.pool.terminate()
            del self.client
        self.client = demisto_client.configure(
            base_url=self.server_url,
            api_key=self.build_context.api_key,
            auth_id=self.build_context.auth_id,
            verify_ssl=False,
        )

    def reset_containers(self):
        if self.build_context.is_saas_server_type:
            self.build_context.logging_module.info(
                "Skip reset containers - this API is not supported.", real_time=True
            )
            return

        self.build_context.logging_module.info("Resetting containers\n", real_time=True)

        response, status_code, headers = demisto_client.generic_request_func(
            self=self.client, method="POST", path="/containers/reset"
        )
        if status_code != requests.codes.ok:
            self.build_context.logging_module.critical(
                f"Request to reset containers failed - response:{pformat(response)}, "
                f"status code:{status_code} headers:{headers}",
                real_time=True,
            )
            sys.exit(1)
        time.sleep(10)

    def execute_tests(self):
        try:
            self.build_context.logging_module.info(
                f"Starts tests with server url - {get_ui_url(self.server_url)}",
                real_time=True,
            )
            self._execute_mockable_tests()
            self.build_context.logging_module.info(
                "Running mock-disabled tests", real_time=True
            )
            self.configure_new_client()
            self._execute_unmockable_tests()
            if self.use_retries_mechanism:
                self.build_context.logging_module.info(
                    "Running failed tests", real_time=True
                )
                self._execute_failed_tests()
            self.build_context.logging_module.info(
                f"Finished tests with server url - " f"{get_ui_url(self.server_url)}",
                real_time=True,
            )
            # no need in SaaS server type, no proxy.
            if not self.build_context.is_saas_server_type:
                self.build_context.tests_data_keeper.add_proxy_related_test_data(
                    self.proxy
                )

            if (
                self.build_context.isAMI
                and self.proxy
                and self.proxy.should_update_mock_repo
            ):
                self.proxy.push_mock_files()
            self.build_context.logging_module.debug(
                f"Tests executed on server {self.server_ip}:\n"
                f"{pformat(self.executed_tests)}"
            )
        except Exception:
            self.build_context.logging_module.exception("~~ Thread failed ~~")
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
            "query": 'id:"Manual"',
        }
        try:
            response, status_code, headers = demisto_client.generic_request_func(
                self=self.client,
                method="POST",
                path="/settings/integration/search",
                body=body,
                response_type="object",
            )
            if status_code != requests.codes.ok:
                self.build_context.logging_module.error(
                    f"Failed to get integrations configuration response:{pformat(response)}, "
                    f"status code:{status_code} headers:{headers}"
                )
                return

            all_configurations = response["configurations"]
            for instance in all_configurations:
                if instance.get("id") == "Manual":
                    self.build_context.logging_module.info(
                        "Server is able to create manual alerts "
                        '("Manual" integration exists).'
                    )
                    return
        except ApiException:
            self.build_context.logging_module.exception(
                "Failed to get integrations configuration."
            )

        self.build_context.logging_module.warning(
            'No "Manual" integration found in XSIAM instance. '
            "Adding it in order to create Manual Correlation Rule."
        )
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
                "subtype": "python3",
            },
        }

        try:
            response, status_code, headers = demisto_client.generic_request_func(
                self=self.client,
                method="PUT",
                path="/settings/integration-conf",
                body=manual_integration,
                response_type="object",
            )
            if status_code not in {requests.codes.ok, requests.codes.no_content}:
                self.build_context.logging_module.error(
                    f"Failed to get integrations configuration - response:{pformat(response)}, "
                    f"status code:{status_code} headers:{headers}"
                )

        except ApiException:
            self.build_context.logging_module.exception(
                'No "Manual" integration found in XSIAM instance. '
                "Please add it in order to create Manual Correlation Rule."
            )

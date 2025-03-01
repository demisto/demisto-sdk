import contextlib
import re
import socket
import time
import urllib.parse
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import dateparser
import demisto_client
import requests
from demisto_client.demisto_api.api.default_api import DefaultApi
from demisto_client.demisto_api.models.entry import Entry
from demisto_client.demisto_api.rest import ApiException, RESTResponse
from packaging.version import Version
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from urllib3 import HTTPResponse

from demisto_sdk.commands.common.clients.configs import XsoarClientConfig
from demisto_sdk.commands.common.clients.errors import (
    InvalidServerType,
    PollTimeout,
    UnAuthorized,
    UnHealthyServer,
)
from demisto_sdk.commands.common.constants import (
    MINIMUM_XSOAR_SAAS_VERSION,
    IncidentState,
    InvestigationPlaybookState,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.common.tools import retry


class ServerType(StrEnum):
    XSOAR = "xsoar-on-prem"
    XSOAR_SAAS = "xsoar-saas"
    XSIAM = "xsiam"


class ServerAbout(BaseModel):
    product_mode: str = Field("", alias="productMode")
    deployment_mode: str = Field("", alias="deploymentMode")
    version: str = Field("", alias="demistoVersion")


class XsoarClient:
    """
    api client for xsoar-on-prem
    """

    _ENTRY_TYPE_ERROR: int = 4
    PLAYBOOK_TASKS_STATES = [
        "New",
        "InProgress",
        "Completed",
        "Waiting",
        "Error",
        "Skipped",
        "Blocked",
    ]
    PLAYBOOK_TASKS_TYPES = ["regular", "condition", "collection"]

    def __init__(
        self,
        config: XsoarClientConfig,
        client: Optional[DefaultApi] = None,
        raise_if_server_not_healthy: bool = True,
        should_validate_server_type: bool = False,
    ):
        self.server_config = config
        self._xsoar_client = client or demisto_client.configure(
            config.base_api_url,
            api_key=self.server_config.api_key.get_secret_value(),
            auth_id=self.server_config.auth_id,
            username=self.server_config.user,
            password=self.server_config.password.get_secret_value(),
            verify_ssl=self.server_config.verify_ssl,
        )
        if raise_if_server_not_healthy and not self.is_healthy:
            raise UnHealthyServer(str(self))
        if should_validate_server_type and not self.is_server_type:
            raise InvalidServerType(str(self), server_type=self.server_type)

    @property
    def xsoar_client(self) -> DefaultApi:
        return self._xsoar_client

    def __str__(self) -> str:
        try:
            about: Union[ServerAbout, None] = self.about
        except Exception as error:
            logger.warning(
                f"Could not get server /about of {self.server_config.base_api_url}, error={error}"
            )
            about = None

        summary = f"api-url={self.server_config.base_api_url}"
        if about:
            if version := about.version:
                summary = f"{summary}, version={version}"
            if deployment_mode := about.deployment_mode:
                summary = f"{summary}, deployment-mode={deployment_mode}"
            if product_mode := about.product_mode:
                summary = f"{summary}, product-mode={product_mode}"

        return f"{self.__class__.__name__}({summary})"

    @property
    def is_server_type(self) -> bool:
        """
        Validates whether the configured server actually matches to the class initialized
        """
        about = self.about
        is_xsoar_on_prem = (
            about.product_mode == "xsoar" and about.deployment_mode == "opp"
        ) or bool((self.version and self.version < Version(MINIMUM_XSOAR_SAAS_VERSION)))
        if not is_xsoar_on_prem:
            logger.debug(f"{self} is not {self.server_type} server")
            return False
        return True

    @property
    def server_type(self) -> ServerType:
        return ServerType.XSOAR

    @property
    def marketplace(self) -> MarketplaceVersions:
        return MarketplaceVersions.XSOAR

    @property
    @retry(exceptions=ApiException)
    def is_healthy(self) -> bool:
        """
        Validates that xsoar server is healthy

        Returns:
            bool: True if xsoar server is healthy, False if not.
        """
        try:
            status_code = self._xsoar_client.generic_request(
                method="GET", path="/health/server"
            )[1]
            if not status_code == requests.codes.ok:
                logger.error(
                    f"The XSOAR server part of {self.server_config.base_api_url} is not healthy"
                )
                return False
            return True
        except ApiException as err:
            if err.status == requests.codes.unauthorized:
                raise UnAuthorized(
                    message=f"Could not connect to {self.server_config.base_api_url}, credentials are invalid",
                    status_code=err.status,
                )
            raise

    @cached_property
    @retry(exceptions=ApiException)
    def about(self) -> ServerAbout:
        raw_response, _, response_headers = self._xsoar_client.generic_request(
            "/about", "GET", response_type="object"
        )
        if "text/html" in response_headers.get("Content-Type"):
            raise ValueError(
                f"The {self.server_config.base_api_url} URL is not the api-url",
            )
        logger.debug(f"about={raw_response}")
        return ServerAbout(**raw_response)

    @property
    def containers_health(self) -> Dict[str, int]:
        raw_response, _, _ = self._xsoar_client.generic_request(
            "/health/containers", "GET", response_type="object"
        )
        return raw_response

    @property
    def version(self) -> Version:
        """
        Returns XSOAR version
        """
        return Version(self.about.version)

    @property
    def xsoar_host_url(self) -> str:
        """
        Returns the base api url used for api requests to xsoar endpoints
        """
        return self._xsoar_client.api_client.configuration.host

    @property
    def base_url(self) -> str:
        """
        Returns the base URL of the xsoar/xsiam instance (not the api URL!)
        """
        return re.sub(r"api-|/xsoar", "", self.xsoar_host_url)

    @property
    def fqdn(self) -> str:
        return urlparse(self.base_url).netloc

    @property
    def ip(self) -> str:
        return socket.gethostbyname(self.fqdn)

    @property
    def external_base_url(self) -> str:
        # url that its purpose is to expose apis of integrations outside from xsoar/xsiam
        return self.server_config.config.base_api_url

    """
    #############################
    Helper methods
    #############################
    """

    def _process_response(self, response, status_code, expected_status=200):
        """Process the HTTP response coming from the XSOAR client."""
        if status_code == expected_status:
            if response:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    error = response.text
                    err_msg = f"Failed to parse json response - with status code {response.status_code}"
                    err_msg += f"\n{error}" if error else ""
                    logger.error(err_msg)
                    response.raise_for_status()
        else:
            error_message = f"Expected status {expected_status}, but got {status_code}. Response: {response}"
            raise Exception(error_message)

    """
    #############################
    marketplace related methods
    #############################
    """

    @property
    @retry(exceptions=ApiException)
    def installed_packs(self):
        """
        Returns all the installed packs in xsoar/xsiam
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="GET",
            path="/contentpacks/metadata/installed",
            response_type="object",
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_installed_pack(self, pack_id: str) -> dict:
        """
        Returns the installed pack by pack_id
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="GET",
            path="/contentpacks/metadata/installed",
            response_type="object",
        )
        for pack in raw_response or []:
            if pack.get("id") == pack_id:
                return pack

        raise ValueError(f"'{pack_id}' is not installed in {self.base_url}")

    @retry(exceptions=ApiException)
    def search_marketplace_packs(self, filters: Optional[Dict] = None):
        """
        Searches for packs in a marketplace

        Args:
            filters: whether there are any filters to apply

        Returns:
            raw response of the found packs
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/contentpacks/marketplace/search",
            response_type="object",
            body=filters or {},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_marketplace_pack(self, pack_id: str):
        """
        Retrives a marketplace pack metadata

        Args:
            pack_id: the pack ID to retrieve.

        Returns:
            raw response of the found pack request
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="GET",
            path=f"/contentpacks/marketplace/{pack_id}",
            response_type="object",
        )
        return raw_response

    @retry(exceptions=ApiException)
    def uninstall_marketplace_packs(self, pack_ids: List[str]):
        """
        Deletes installed packs from the marketplace.

        Args:
            pack_ids: list of pack IDs to delete

        Returns:
            raw response of the deleted packs request
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/contentpacks/installed/delete",
            response_type="object",
            body={"IDs": pack_ids},
        )
        logger.debug(f"Successfully removed packs {pack_ids} from {self.base_url}")
        return raw_response

    @retry(exceptions=ApiException)
    def upload_marketplace_packs(
        self, zipped_packs_path: Union[Path, str], skip_validation: bool = True
    ):
        """
        Uploads packs to the marketplace.

        Args:
            zipped_packs_path: zipped packs path
            skip_validation: whether to skip packs validations, True if yes, False if not.

        Returns:
            raw response of the upload packs request
        """
        params = {}
        if skip_validation:
            params["skip_validation"] = "true"

        return self._xsoar_client.upload_content_packs(str(zipped_packs_path), **params)

    @retry(exceptions=ApiException)
    def install_marketplace_packs(
        self, packs: List[Dict[str, Any]], ignore_warnings: bool = True
    ):
        """
        Installs packs from the marketplace.

        Args:
            packs: the packs metadata to install
            ignore_warnings: whether to ignore warnings when installing, True if yes, False if not.

        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/contentpacks/marketplace/install",
            response_type="object",
            body={"packs": packs, "ignoreWarnings": ignore_warnings},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def sync_marketplace(self):
        """
        Syncs up the marketplace.
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/contentpacks/marketplace/sync",
            response_type="object",
        )
        return raw_response

    """
    #############################
    integrations related methods
    #############################
    """

    @retry(exceptions=ApiException)
    def create_integration_instance(
        self,
        _id: str,
        instance_name: str,
        integration_instance_config: Dict,
        integration_log_level: Optional[str] = None,
        is_long_running: bool = False,
        should_enable: str = "true",
        response_type: str = "object",
        should_test: bool = False,
    ):
        """
        Creates an integration instance.

        Args:
            _id: integration ID.
            instance_name: the name for the new instance
            integration_instance_config: integration configuration (params)
            integration_log_level: integration log level (Verbose, Debug, None)
            is_long_running: whether the integration is a long-running-integration
            should_enable: should the instance be enabled, True if yes, False if not.
            response_type: the response type to return
            should_test: whether to test the newly created integration (run its test-module),
                         True to run test module, False if not.

        Returns:
            raw response of the newly created integration instance
        """
        logger.info(
            f"Creating integration instance {instance_name} for integration {_id}"
        )
        integrations_metadata: Dict[str, Any] = (
            self.get_integrations_module_configuration(_id)
        )
        with contextlib.suppress(ValueError):
            instance = self.get_integration_instance(instance_name)
            logger.info(
                f"Integration instance {instance_name} already exists, deleting instance"
            )
            self.delete_integration_instance(instance.get("id"))
        integration_instance_body_request = {
            "brand": integrations_metadata["name"],
            "category": integrations_metadata["category"],
            "canSample": True,
            "configuration": integrations_metadata,
            "data": [],
            "enabled": should_enable,
            "engine": "",
            "id": "",
            "isIntegrationScript": True,  # type: ignore
            "name": instance_name,
            "passwordProtected": False,
            "version": 0,
            "incomingMapperId": integrations_metadata.get("defaultMapperIn", ""),
            "mappingId": integrations_metadata.get("defaultClassifier", ""),
            "outgoingMapperId": integrations_metadata.get("defaultMapperOut", ""),
        }
        if integration_log_level:
            if integration_log_level not in {"Debug", "Verbose"}:
                raise ValueError(
                    f"integrationLogLevel must be either Debug/Verbose and not {integration_log_level}"
                )
            integration_instance_body_request["integrationLogLevel"] = (
                integration_log_level
            )

        if is_long_running:
            integration_instance_body_request["isLongRunning"] = is_long_running

        module_configuration: List[Dict[str, Any]] = integrations_metadata[
            "configuration"
        ]

        for param_conf in module_configuration:
            display = param_conf["display"]
            name = param_conf["name"]
            default_value = param_conf["defaultValue"]

            if (
                display in integration_instance_config
                or name in integration_instance_config
            ):
                key = display if display in integration_instance_config else name
                if key in {"credentials", "creds_apikey"}:
                    credentials = integration_instance_config[key]
                    param_value = {
                        "credential": "",
                        "identifier": credentials.get("identifier", ""),
                        "password": credentials["password"],
                        "passwordChanged": True if is_long_running else False,
                    }
                else:
                    param_value = integration_instance_config[key]

                param_conf["value"] = param_value
                param_conf["hasvalue"] = True
            elif default_value:
                param_conf["value"] = default_value

            integration_instance_body_request["data"].append(param_conf)

        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="PUT",
            path="/settings/integration",
            body=integration_instance_body_request,
            response_type=response_type,
        )
        logger.info(
            f"Successfully created integration instance {instance_name} for Integration {_id}"
        )
        if should_test:
            self.test_module(_id, instance_name)
        return raw_response

    @retry(exceptions=ApiException)
    def search_integrations(self, response_type: str = "object"):
        """
        Searches for integrations

        Args:
            response_type: the response type to return
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/settings/integration/search",
            response_type=response_type,
            body={},
        )
        return raw_response

    def test_module(self, _id: str, instance_name: str):
        """
        Runs test module for an integration instance, if an exception isn't raised, the test was successful.

        Raises ApiException in case the test-module was not successful.

        Args:
            _id: the ID of the integration
            instance_name: the instance integration name

        """
        logger.info(f"Running test-module on integration {_id} and {instance_name=}")
        instance = self.get_integration_instance(instance_name)
        raw_response, status_code, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/settings/integration/test",
            body=instance,
            response_type="object",
            _request_timeout=240,
        )
        if status_code >= 300 or not raw_response.get("success"):
            raise ApiException(
                f"Test module failed - {raw_response.get('message')}, status code: {status_code}"
            )
        logger.debug(
            f"The test-module was successful for integration {_id} and {instance_name=}"
        )

    @retry(exceptions=ApiException)
    def delete_integration_instance(
        self, instance_id: str, response_type: str = "object"
    ):
        """
        Deletes integration instance.

        Args:
            instance_id: the ID of the instance to delete
            response_type: the response type to return

        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="DELETE",
            path=f"/settings/integration/{urllib.parse.quote(instance_id)}",
            response_type=response_type,
        )
        logger.debug(
            f"Successfully removed integration instance {instance_id} from {self.base_url}"
        )

    @retry(exceptions=ApiException)
    def get_integrations_module_configuration(
        self,
        _id: Optional[str] = None,
        response_type: str = "object",
    ):
        """
        Get the integration(s) module configuration(s)

        Args:
            _id: the module configuration of a specific integration
            response_type: the response type to return

        Returns:
            if _id is provided, the module config of a specific integration,
            otherwise all module configs of all integrations
        """
        if response_type != "object" and _id:
            raise ValueError(
                'response_type must be equal to "object" when providing _id'
            )

        raw_response = self.search_integrations(response_type=response_type)
        if not _id:
            return raw_response
        for config in raw_response.get("configurations") or []:
            if config.get("id") == _id:
                return config

        raise ValueError(
            f"Could not find module configuration for integration ID '{_id}'"
        )

    @retry(exceptions=ApiException)
    def get_integration_instance(self, instance_name: str):
        """
        Searches for an existing integration instance.

        Args:
            instance_name: the instance name of the integration

        """
        raw_response = self.search_integrations()
        for instance in raw_response.get("instances", []):
            if instance_name == instance.get("name"):
                return instance

        raise ValueError(f"Could not find instance for instance name '{instance_name}'")

    def disable_integration_instance(self, instance_name):
        return self.update_integration_instance_state(False, instance_name)

    def enable_integration_instance(self, instance_name):
        return self.update_integration_instance_state(True, instance_name)

    def update_integration_instance_state(self, enable: bool, instance_name: str):
        # it will throw an error if the instance does not exist
        instance = self.get_integration_instance(instance_name)

        integration_instance_body_request = {
            "id": instance.get("id"),
            "brand": instance.get("brand"),
            "name": instance_name,
            "data": instance.get("data"),
            "isIntegrationScript": instance.get("isIntegrationScript"),
            "enabled": "true" if enable else "false",
            "version": -1,
        }
        logger.info(
            f"{'Enabling' if enable else 'Disabling'} integration instance {instance_name} for integration {instance.get('brand')}"
        )

        raw_response, _, _ = self.xsoar_client.generic_request(
            method="PUT",
            path="/settings/integration",
            body=integration_instance_body_request,
            response_type="object",
        )
        logger.info(
            f"Successfully {'enabled' if enable else 'disabled'} integration instance {instance_name} for Integration {instance.get('brand')}"
        )
        return raw_response

    """
    #############################
    incidents related methods
    #############################
    """

    @retry(exceptions=ApiException)
    def create_incident(
        self,
        name: str,
        should_create_investigation: bool = True,
        attached_playbook_id: Optional[str] = None,
    ):
        """
        Args:
            name: the name of the created incident
            should_create_investigation: whether it is required to start investigating the incident
                                        (start playbook running)
            attached_playbook_id: the playbook to attach to the incident

        Returns:
            raw response of the newly created incident
        """
        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = should_create_investigation
        create_incident_request.playbook_id = attached_playbook_id

        create_incident_request.name = name

        try:
            return self._xsoar_client.create_incident(
                create_incident_request=create_incident_request
            )
        except ApiException as err:
            if err.status == requests.codes.bad_request and attached_playbook_id:
                raise ValueError(f"playbook-id {attached_playbook_id} does not exist.")
            raise

    @retry(exceptions=ApiException)
    def search_incidents(
        self,
        incident_ids: Optional[Union[List, str]] = None,
        from_date: Optional[str] = None,
        incident_types: Optional[Union[List, str]] = None,
        source_instance_name: Optional[str] = None,
        page: int = 0,
        size: int = 50,
        response_type: str = "object",
    ):
        """
        Args:
            incident_ids: retrieves only the incident IDs provided
            from_date: from which date incidents should be retrieved
            incident_types: the incident types to match
            source_instance_name: retrieve only incidents came from this instance name (integration)
            page: the page number
            size: the size number
            response_type: the response type of the raw response

        Returns:
            the raw response of the incidents found
        """
        filters: Dict[str, Any] = {"page": page, "size": size}

        if incident_ids:
            if isinstance(incident_ids, str):
                incident_ids = [incident_ids]
            filters["id"] = incident_ids

        if from_date:
            if parsed_date := dateparser.parse(from_date):
                filters["fromDate"] = parsed_date.strftime(
                    "%Y-%m-%dT%H:%M:%S.000+00:00"
                )
            else:
                raise ValueError(
                    f"Could not parse {from_date}, make sure it is a valid date string"
                )

        if incident_types:
            if isinstance(incident_types, str):
                incident_types = [incident_types]
            filters["type"] = incident_types

        if source_instance_name:
            filters["sourceInstance"] = source_instance_name

        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/incidents/search",
            body={"filter": filters},
            response_type=response_type,
        )
        return raw_response

    def poll_incident_state(
        self,
        incident_id: str,
        expected_states: Tuple[IncidentState, ...] = (IncidentState.CLOSED,),
        timeout: int = 120,
    ):
        """
        Polls for an incident state

        Args:
            incident_id: the incident ID to poll its state
            expected_states: which states are considered to be valid for the incident to reach
            timeout: how long to query until incidents reaches the expected state

        Returns:
            raw response of the incident that reached into the relevant state.
        """
        if timeout <= 0:
            raise ValueError("timeout argument must be larger than 0")

        elapsed_time = 0
        start_time = time.time()
        interval = timeout / 10
        incident_name = None
        incident_status = None

        expected_state_names = {state.name for state in expected_states}

        while elapsed_time < timeout:
            try:
                incident = self.search_incidents(incident_id).get("data", [])[0]
            except Exception as e:
                raise ValueError(
                    f"Could not find incident ID {incident_id}, error:\n{e}"
                )
            logger.debug(f"Incident raw response {incident}")
            incident_status = IncidentState(str(incident.get("status"))).name
            incident_name = incident.get("name")
            logger.debug(f"status of the incident {incident_name} is {incident_status}")
            if incident_status in expected_state_names:
                return incident
            else:
                time.sleep(interval)
                elapsed_time = int(time.time() - start_time)

        raise PollTimeout(
            f"status of incident {incident_name} is {incident_status}",
            expected_states=expected_states,
            timeout=timeout,
        )

    @retry(exceptions=ApiException)
    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
        """
        Args:
            incident_ids: The incident IDs to remove
            filters: any filters if needed
            _all: whether to delete all incidents
            response_type: the response type of the raw response

        Returns:
            the raw response of the incidents deleted
        """
        if isinstance(incident_ids, str):
            incident_ids = [incident_ids]
        body = {"ids": incident_ids, "filter": filters or {}, "all": _all}

        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/incident/batchDelete",
            body=body,
            response_type=response_type,
        )
        return raw_response

    def get_incident_work_plan_url(self, incident_id: str) -> str:
        """
        Returns the URL of the work-plan of the incident ID.

        Args:
            incident_id: incident ID.
        """
        return f"{self.base_url}/#/WorkPlan/{incident_id}"

    """
    #############################
    indicators related methods
    #############################
    """

    @retry(exceptions=ApiException)
    def create_indicator(
        self,
        value: str,
        indicator_type: str,
        score: int = 0,
        response_type: str = "object",
    ):
        """
        Args:
            value: the value of the indicator
            indicator_type: the type of the indicator
            score: the score of the indicator
            response_type: the response type of the raw response

        Returns:
            the raw response of newly created indicator
        """

        whitelisted_indicators_raw_response = self.get_indicators_whitelist()
        for indicator in whitelisted_indicators_raw_response:
            if indicator.get("value") == value:
                raise ApiException(
                    status=400,
                    reason=f"Cannot create the indicator={value} type={indicator_type} "
                    f"because it is in the exclusion list",
                )

        # if raw_response = None and status_code = 200, it means the indicator is in the exclusion list
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/indicator/create",
            body={
                "indicator": {
                    "value": value,
                    "indicator_type": indicator_type,
                    "score": score,
                }
            },
            response_type=response_type,
        )

        return raw_response

    @retry(exceptions=ApiException)
    def delete_indicators(
        self,
        indicator_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        should_exclude: bool = False,
        response_type: str = "object",
    ):
        """
        Deletes indicators from xsoar/xsiam

        Args:
            indicator_ids: the indicator IDs to remove
            filters: any filters if needed
            _all: whether all indicators should be deleted
            should_exclude: whether to put them in exclusion list post deletion, True if yes, False if not
            response_type: the response type of the raw response

        Returns:
            the raw response of the deleted indicators
        """
        if isinstance(indicator_ids, str):
            indicator_ids = [indicator_ids]
        body = {
            "ids": indicator_ids,
            "filter": filters or {},
            "all": _all,
            "DoNotWhitelist": not should_exclude,
        }
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/indicators/batchDelete",
            body=body,
            response_type=response_type,
        )

        successful_removed_ids = set(raw_response.get("updatedIds") or [])
        indicators_ids_to_remove = set(indicator_ids)
        if not indicators_ids_to_remove.issubset(successful_removed_ids):
            logger.warning(
                f"could not delete the following indicator IDs "
                f"{indicators_ids_to_remove.difference(successful_removed_ids)}"
            )
        else:
            logger.debug(f"Successfully deleted indicators {indicator_ids}")

        return raw_response

    @retry(exceptions=ApiException)
    def list_indicators(
        self,
        page: int = 0,
        size: int = 50,
        query: str = "",
        response_type: str = "object",
    ):
        """
        Args:
            page: the page number
            size: the size number
            query: the query to get specific indicators
            response_type: the response type of the raw response

        Returns:
            the raw response of existing indicators
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/indicators/search",
            body={"page": page, "size": size, "query": query},
            response_type=response_type,
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_indicators_whitelist(self, response_type: str = "object"):
        """
        Args:
            response_type: the response type of the raw response

        Returns:
            the indicators that are in the exclusion list
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="GET",
            path="/indicators/whitelisted",
            response_type=response_type,
        )
        return raw_response

    @retry(exceptions=ApiException)
    def delete_indicators_from_whitelist(
        self, indicator_ids: List[str], response_type: str = "object"
    ):
        """
        Args:
            indicator_ids: the indicator IDs to remove from exclusion list
            response_type: the response type of the raw response

        Returns:
            the raw response of deleting indicators from exclusion list
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/indicators/whitelist/remove",
            response_type=response_type,
        )
        indicator_ids = set(indicator_ids)
        raw_response = set(raw_response)

        if not indicator_ids.issubset(raw_response):
            logger.warning(
                f"Could not delete indicators with the following IDs: {indicator_ids.difference(raw_response)}"
            )
        return raw_response

    """
    #############################
    long-running methods
    #############################
    """

    @retry(times=20, exceptions=RequestException)
    def do_long_running_instance_request(
        self,
        instance_name: str,
        url_suffix: str = "",
        headers: Optional[Dict[str, Any]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> requests.Response:
        """

        Args:
            instance_name: the integration instance name
            url_suffix: any url suffix for the api request
            headers: any headers if required
            username: the username of the integration if exist
            password: the password for the integration if exist

        Returns:
            the response of the long-running integration request
        """
        if url_suffix and not url_suffix.startswith("/"):
            url_suffix = f"/{url_suffix}"
        url = f"{self.external_base_url}/instance/execute/{instance_name}{url_suffix}"
        auth = HTTPBasicAuth(username, password) if username and password else None

        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        return response

    """
    #############################
    incident investigations related methods
    #############################
    """

    @retry(exceptions=ApiException)
    def run_cli_command(
        self,
        command: str,
        investigation_id: Optional[str] = None,
        should_delete_context: bool = True,
        response_type: str = "object",
    ) -> Tuple[List[Entry], Dict[str, Any]]:
        """
        Args:
            command: the command to run
            investigation_id: investigation ID of a specific incident / playground
            should_delete_context: whether context should be deleted before executing the command
            response_type: the response type of the raw response

        Returns:
            the context after running the command
        """
        return self._run_command(
            "!", command, investigation_id, should_delete_context, response_type
        )

    @retry(exceptions=ApiException)
    def run_slash_command(
        self,
        command: str,
        investigation_id: Optional[str] = None,
        should_delete_context: bool = True,
        response_type: str = "object",
    ) -> Tuple[List[Entry], Dict[str, Any]]:
        """
        Args:
            command: the command to run
            investigation_id: investigation ID of a specific incident / playground
            should_delete_context: whether context should be deleted before executing the command
            response_type: the response type of the raw response

        Returns:
            the context after running the command
        """
        return self._run_command(
            "/", command, investigation_id, should_delete_context, response_type
        )

    def _run_command(
        self,
        command_type: str,
        command: str,
        investigation_id: Optional[str] = None,
        should_delete_context: bool = True,
        response_type: str = "object",
    ) -> Tuple[List[Entry], Dict[str, Any]]:
        """
        Args:
            command_type: command type, slash or cli command.
            command: the command to run
            investigation_id: investigation ID of a specific incident / playground
            should_delete_context: whether context should be deleted before executing the command
            response_type: the response type of the raw response

        Returns:
            the context after running the command
        """
        if not investigation_id:
            if self.server_config.server_type == ServerType.XSOAR:
                investigation_id = self.get_playground_id()
            else:
                # it is not possible to auto-detect playground-id in xsoar-8, see CIAC-8766,
                # once its resolved this should be implemented
                raise ValueError(
                    "Investigation_id must be provided for xsoar-saas/xsiam"
                )
        if not command.startswith(command_type):
            command = f"{command_type}{command}"

        if should_delete_context:
            update_entry = {
                "investigationId": investigation_id,
                "data": "!DeleteContext all=yes",
            }

            self._xsoar_client.investigation_add_entries_sync(update_entry=update_entry)

        update_entry = {"investigationId": investigation_id, "data": command}
        war_room_entries: List[Entry] = (
            self._xsoar_client.investigation_add_entries_sync(update_entry=update_entry)
        )
        logger.debug(
            f"Successfully run the command {command} in investigation {investigation_id}"
        )

        return war_room_entries, self.get_investigation_context(
            investigation_id, response_type
        )

    def get_formatted_error_entries(self, entries: List[Entry]) -> Set[str]:
        """
        Get formatted error entries from an executed command / playbook tasks

        Args:
            entries: a list of entries

        Returns:
            Formatted error entries
        """
        error_entries: Set[str] = set()

        for entry in entries:
            if entry.type == self._ENTRY_TYPE_ERROR and entry.parent_content:
                # Checks for passwords and replaces them with "******"
                parent_content = re.sub(
                    r' ([Pp])assword="[^";]*"',
                    " password=******",
                    entry.parent_content,
                )
                formatted_error = ""
                if entry_task := entry.entry_task:
                    formatted_error = f"Playbook {entry_task.playbook_name} task({entry_task.task_id}) named '{entry_task.task_name}' using "
                formatted_error += (
                    f"Command {parent_content} finished with error:\n{entry.contents}"
                )

                error_entries.add(formatted_error)

        return error_entries

    def get_playground_id(self) -> str:
        """
        Returns a playground ID based on the user.
        """
        answer = self._xsoar_client.search_investigations(
            filter={"filter": {"type": [9], "page": 0}}
        )
        if answer.total == 0:
            raise RuntimeError(f"No playgrounds were detected in {self.base_url}")
        elif answer.total == 1:
            playground_id = answer.data[0].id
        else:
            # if found more than one playground, try to filter to results against the current user
            user_data, status_code, _ = self._xsoar_client.generic_request(
                path="/user",
                method="GET",
                content_type="application/json",
                response_type="object",
            )
            if status_code != 200:
                raise RuntimeError("Cannot find username")

            username = user_data.get("username") or ""

            def filter_by_creating_user_id(playground):
                return playground.creating_user_id == username

            playgrounds = list(filter(filter_by_creating_user_id, answer.data))
            if playgrounds:
                playground_id = playgrounds[0].id
            else:
                for page in range(int((answer.total - 1) / len(answer.data))):
                    playgrounds.extend(
                        filter(
                            filter_by_creating_user_id,
                            self._xsoar_client.search_investigations(
                                filter={"filter": {"type": [9], "page": page + 1}}
                            ).data,
                        )
                    )
                if not playgrounds:
                    raise RuntimeError(f"Could not find playground for {self.base_url}")
                playground_id = playgrounds[0].id

        logger.debug(f"Found playground ID {playground_id} for {self.base_url}")
        return playground_id

    @retry(exceptions=ApiException)
    def get_investigation_context(
        self, investigation_id: str, response_type: str = "object"
    ):
        """
        Args:
            investigation_id: the ID of the investigation
            response_type: the response type of the raw response

        Returns:
            the context of the investigation / incident
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path=f"/investigation/{investigation_id}/context",
            response_type=response_type,
            body={"query": "${.}"},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_investigation_status(self, incident_id: str):
        """
        Args:
            incident_id: the incident ID

        Returns:
            the raw response of the status of the investigation
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path=f"/investigation/{urllib.parse.quote(incident_id)}",
            body={"pageSize": 1000},
            response_type="object",
        )
        return raw_response

    @retry(exceptions=ApiException)
    def start_incident_investigation(
        self, incident_id: str, response_type: str = "object"
    ):
        """
        Args:
            incident_id: the incident ID
            response_type: the response type of the raw response

        Returns:
            the raw response of investigation of the incident
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/incident/investigate",
            body={"id": incident_id},
            response_type=response_type,
        )
        return raw_response

    """
    #############################
    playbooks related methods
    #############################
    """

    @retry(exceptions=ApiException)
    def delete_playbook(self, name: str, _id: str, response_type: str = "object"):
        """
        Args:
            name: the name of the playbook to delete
            _id: the ID of the playbook to delete
            response_type: the response type of the raw response

        Returns:
            the raw response of deleting the playbook
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="POST",
            path="/playbook/delete",
            response_type=response_type,
            body={"id": _id, "name": name},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_incident_playbook_failure(self, incident_id: str) -> Set[str]:
        """
        Returns the failure reason for a playbook within an incident

        Args:
            incident_id: the incident ID.

        Returns:
            Formatted set of error messages for each error entry
        """
        investigation_status = self.get_investigation_status(incident_id)

        # parses the playbook entries into the Entry model from demisto-py
        playbook_entries = self._xsoar_client.api_client.deserialize(
            RESTResponse(
                HTTPResponse(body=json.dumps(investigation_status.get("entries") or []))
            ),
            response_type="list[Entry]",
        )
        return self.get_formatted_error_entries(playbook_entries)

    @retry(exceptions=ApiException)
    def get_playbook_state(self, incident_id: str, response_type: str = "object"):
        """
        Returns the playbook state within an incident

        Args:
            incident_id: the incident ID
            response_type: the response type of the raw response

        Returns:
            the raw response of the state of the playbook
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self._xsoar_client,
            method="GET",
            path=f"/inv-playbook/{incident_id}",
            response_type=response_type,
        )
        return raw_response

    def poll_playbook_state(
        self,
        incident_id: str,
        expected_states: Tuple[InvestigationPlaybookState, ...] = (
            InvestigationPlaybookState.COMPLETED,
        ),
        timeout: int = 120,
    ):
        """
        Polls for a playbook state until it reaches into an expected state.

        Args:
            incident_id: incident ID that the playbook is running on
            expected_states: which states are considered to be valid for the playbook to reach
            timeout: how long to query until the playbook reaches the expected state

        Returns:
            the raw response of the state of the playbook
        """
        if timeout <= 0:
            raise ValueError("timeout argument must be larger than 0")

        elapsed_time = 0
        start_time = time.time()
        interval = timeout / 10
        playbook_id = None
        playbook_state = None

        while elapsed_time < timeout:
            playbook_state_raw_response = self.get_playbook_state(incident_id)
            logger.debug(f"playbook state raw-response: {playbook_state_raw_response}")
            playbook_state = playbook_state_raw_response.get("state")
            playbook_id = playbook_state_raw_response.get("playbookId")
            logger.debug(
                f"status of the playbook {playbook_id} running in incident {incident_id} is {playbook_state}"
            )
            if playbook_state in expected_states:
                return playbook_state_raw_response
            else:
                time.sleep(interval)
                elapsed_time = int(time.time() - start_time)

        raise PollTimeout(
            f"status of the playbook {playbook_id} running in incident {incident_id} "
            f"is {playbook_state}",
            expected_states=expected_states,
            timeout=timeout,
            reason=(
                f"{self.get_incident_playbook_failure(incident_id)}"
                if playbook_state == InvestigationPlaybookState.FAILED
                else None
            ),
        )

    def get_playbook_data(self, playbook_id: int) -> dict:
        playbook_endpoint = f"/playbook/{playbook_id}"

        response, status_code, _ = self._xsoar_client.generic_request(
            playbook_endpoint, method="GET", accept="application/json"
        )
        return self._process_response(response, status_code, 200)

    def update_playbook_input(self, playbook_id: str, new_inputs: dict):
        saving_inputs_path = f"/playbook/inputs/{playbook_id}"
        response, status_code, _ = self._xsoar_client.generic_request(
            saving_inputs_path, method="POST", body={"inputs": new_inputs}
        )
        return self._process_response(response, status_code, 200)

    def get_playbook_task_in_investigation(self, task_name, investigation_id):
        """
        Get playbook task in an incident.

        Args:
            investigation_id: incident ID that the playbook is running on
            task_name: The name of the task to retrieve data on it.
        Returns:
            a dict of the task details.
        """
        tasks, status_code, _ = self._xsoar_client.generic_request(
            f"/investigation/{investigation_id}/workplan/tasks",
            method="POST",
            body={
                "states": self.PLAYBOOK_TASKS_STATES,
                "types": self.PLAYBOOK_TASKS_TYPES,
            },
            response_type="object",
        )

        for task in tasks:
            if task_name == task.get("task").get("name"):
                return task
        raise ValueError(
            f"{task_name} task was not found in {investigation_id} investigation."
        )

    def pull_playbook_tasks_by_state(
        self,
        incident_id: str,
        task_input: str = None,
        task_states: list = None,
        task_name: str = None,
        max_timeout: int = 60,
        interval_between_tries: str = "3",
        complete_task: bool = False,
    ):
        """
        Wait and complete playbook tasks by given status. Same implementation as WaitAndCompleteTask script in content.

        Args:
            incident_id: incident ID that the playbook is running on
            task_input: Outcome for a conditional task. For example, "Yes"
            task_states: list of states. Possible values: New, InProgress, Completed, Waiting, Error, Skipped, Blocked (leave empty to get all tasks)
            task_name: The name of the task that should be completed. If no task name is provided, will complete all tasks with the state `task_state`
            max_timeout: Timeout in seconds for the script to complete tasks.
            interval_between_tries: Time (seconds) to wait between each check iteration.
            complete_task: Whether to complete the task in addition to checking if it is completed.


        Returns:
            a list of completed task if completed, and found tasks if not completed.
        """
        if not all(state in self.PLAYBOOK_TASKS_STATES for state in task_states):  # type: ignore
            raise ValueError(
                f"task_states are bad. Possible values: {self.PLAYBOOK_TASKS_STATES}"
            )
        if not task_states:
            task_states = self.PLAYBOOK_TASKS_STATES
        if complete_task and not task_input:
            raise RuntimeError("Task input argument is missing to complete tasks.")
        completed_tasks = []
        found_tasks = []
        start_time = time.time()

        while time.time() - start_time > max_timeout:  # type: ignore[operator]
            # Get all tasks with one state of the states in task_states list
            tasks_by_states, status_code, _ = self._xsoar_client.generic_request(
                f"/investigation/{incident_id}/workplan/tasks",
                method="POST",
                body={"states": task_states, "types": self.PLAYBOOK_TASKS_TYPES},
                response_type="object",
            )
            requested_task = None

            # find task to complete if was given task name
            if task_name:
                for task in tasks_by_states:
                    if task.get("task").get("name") == task_name:
                        requested_task = task
                        break

            if requested_task and complete_task:
                # complete the requested task
                self.complete_playbook_task(
                    investigation_id=incident_id,
                    task_id=requested_task.get("id"),
                    task_input=task_input,  # type: ignore
                )

                completed_tasks.append(requested_task.get("task").get("name"))
                break

            # Do not complete the task
            elif requested_task:
                # just validate that task was found and not complete it
                found_tasks.append(
                    {
                        "task name": requested_task.get("task").get("name"),
                        "task state": requested_task.get("state"),
                    }
                )
                break

            elif not task_name and tasks_by_states and complete_task:
                # complete all tasks, which state is task_states
                for task in tasks_by_states:
                    self.complete_playbook_task(
                        investigation_id=incident_id,
                        task_id=task.get("id"),
                        task_input=task_input,  # type: ignore
                    )
                    completed_tasks.append(task.get("task").get("name"))

                break

            elif not task_name and tasks_by_states:
                # just validate that task was found and not complete it
                found_tasks.extend(
                    {
                        "task name": task.get("task").get("name"),
                        "task state": task.get("state"),
                    }
                    for task in tasks_by_states
                )
                break

            time.sleep(float(interval_between_tries))  # type: ignore[arg-type]

        if not completed_tasks and not found_tasks:
            if task_name and task_states:
                raise RuntimeError(
                    f'The task "{task_name}" was not found by the script or it did not reach the {" or ".join(task_states)} state.'
                )
            elif task_states:
                raise RuntimeError(
                    f'None of the tasks reached the {" or ".join(task_states)} state.'
                )
            else:
                raise RuntimeError("No tasks were found.")

        return {"CompletedTask": completed_tasks, "FoundTask": found_tasks}

    def complete_playbook_task(
        self,
        investigation_id,
        task_input: str,
        task_id: str = None,
        task_name: str = None,
    ):
        """
        Complete a playbook task in an investigation.

        Args:
            investigation_id: Investigation ID that the playbook is running on
            task_input: The input to complete the task with.
            task_id: the task id to complete.
            task_name: the name of the task to complete.
        """
        if not (task_name or task_id):
            return RuntimeError("Task id or task name should be provided.")
        elif not task_id:
            task = self.get_playbook_task_in_investigation(task_name, investigation_id)
            task_id = task.get("id")
        try:
            response, status_code, _ = self._xsoar_client.generic_request(
                "/inv-playbook/task/complete",
                method="POST",
                response_type="object",
                content_type="multipart/form-data",
                form_params=[
                    ("investigationId", investigation_id),
                    ("taskId", task_id),
                    ("taskInput", task_input),
                ],
            )
        except ApiException as e:
            if e.status == 400 and "Task is completed already" in e.body:
                logger.info(
                    f"task with id {task_id} is already completed, or it does not exist."
                )
            elif "Could not find investigations" in e.body:
                raise ValueError(
                    f"Could not find investigation with id: {investigation_id}"
                )
            else:
                raise RuntimeError(f"Failed Completing task {task_id}. Error: {e}")

        logger.info(
            f"The playbook task with id {task_id} was completed with input {task_input}"
        )

    def upload_file_to_war_room(
        self,
        file_path,
        incident_id,
        file_name: str = None,
        file_comment: str = None,
        field: str = None,
        show_media_file: str = None,
        last: str = None,
    ):
        """
        Upload a file attachment to an investigation .

        Args:
            file_path: path of the file to upload to the incident.
            incident_id: incident ID to upload to
            file_name: the name of the file to upload
            file_comment: comment on the file
            file_name: The name of the task to retrieve data on it.
            field: field name to hold the attachment details. If not specified, `attachment` will be used.
            show_media_file: show media file
            last: If set to true will create an investigation. Used for uploading after creating incident.
        """
        form_params = []
        if file_name:
            form_params.append(("fileName", file_name))
        if file_comment:
            form_params.append(("fileComment", file_comment))
        if field:
            form_params.append(("field", field))
        if show_media_file:
            form_params.append(("showMediaFile", show_media_file))
        if last:
            form_params.append(("last", last))

        self._xsoar_client.generic_request(
            f"/entry/upload/{incident_id}",
            method="POST",
            form_params=form_params,
            response_type="object",
            content_type="multipart/form-data",
            files={"file": file_path},
        )

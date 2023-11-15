import contextlib
import re
import urllib.parse
from abc import ABC
from typing import Any, Dict, List, Optional, Union

import dateparser
import demisto_client
import requests
from demisto_client.demisto_api.api.default_api import DefaultApi
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version
from pydantic import BaseModel, Field, validator
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.configs import (
    XsoarClientConfig,
)
from demisto_sdk.commands.common.clients.errors import UnAuthorized
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry


class XsoarClient(BaseModel, ABC):
    """
    api client for xsoar-on-prem
    """

    _ENTRY_TYPE_ERROR: int = 4
    client: DefaultApi = Field(exclude=True)
    config: XsoarClientConfig
    about_xsoar: Dict = Field(None, exclude=True)
    marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    @retry(exceptions=ApiException)
    def get_xsoar_about(cls, client: DefaultApi) -> Dict[str, Any]:
        """
        Get basic information about XSOAR server.
        """
        try:
            raw_response, _, _ = client.generic_request(
                "/about", "GET", response_type="object"
            )
            return raw_response
        except ApiException as err:
            if err.status == requests.codes.unauthorized:
                raise UnAuthorized(
                    message=f"Could not connect to {client.api_client.configuration.host}, check credentials are valid",
                    status_code=err.status,
                )
            raise

    @validator("client", always=True, pre=True)
    def validate_client_configured_correctly(
        cls, v: Optional[DefaultApi]
    ) -> DefaultApi:
        return v or demisto_client.configure()

    @validator("about_xsoar", always=True)
    def get_xsoar_server_about(cls, v: Optional[Dict], values: Dict[str, Any]) -> Dict:
        return v or cls.get_xsoar_about(values["client"])

    @property
    def containers_health(self) -> Dict[str, int]:
        raw_response, _, _ = self.client.generic_request(
            "/health/containers", "GET", response_type="object"
        )
        return raw_response

    @property
    def version(self) -> Version:
        """
        Returns XSOAR version
        """
        if xsoar_version := self.about_xsoar.get("demistoVersion"):
            return Version(xsoar_version)
        raise RuntimeError(f"Could not get version from instance {self.xsoar_host_url}")

    @property
    def build_number(self) -> str:
        if build_number := self.about_xsoar.get("buildNum"):
            return build_number
        raise RuntimeError(
            f"Could not get build number from instance {self.xsoar_host_url}"
        )

    @property
    def xsoar_host_url(self) -> str:
        """
        Returns the base api url used for api requests to xsoar endpoints
        """
        return self.client.api_client.configuration.host

    @property
    def base_url(self) -> str:
        """
        Returns the base URL of the xsoar/xsiam instance (not the api URL!)
        """
        return re.sub(r"api-|/xsoar", "", self.xsoar_host_url)

    @property
    def external_base_url(self) -> str:
        # url that its purpose is to expose apis of integrations outside from xsoar/xsiam
        return self.config.base_api_url

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
            self=self.client,
            method="GET",
            path="/contentpacks/metadata/installed",
            response_type="object",
        )
        return raw_response

    def search_marketplace_packs(self, filters: Dict):
        """
        Searches for packs in a marketplace

        Args:
            filters: whether there are any filters to apply

        Returns:
            raw response
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/contentpacks/marketplace/search",
            response_type="object",
            body=filters,
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
            should_test: whether to test the newly created integration (run its test-module)

        Returns:
            raw response of the newly created integration instance
        """
        logger.info(
            f"Creating integration instance {instance_name} for Integration {_id}"
        )
        integrations_metadata: Dict[
            str, Any
        ] = self.get_integrations_module_configuration(_id)
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
            integration_instance_body_request[
                "integrationLogLevel"
            ] = integration_log_level

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
            self=self.client,
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
            self=self.client,
            method="POST",
            path="/settings/integration/search",
            response_type=response_type,
            body={},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def test_module(self, _id: str, instance_name: str, response_type: str = "object"):
        """
        Runs test module for an integration instance

        Args:
            _id: the ID of the integration
            instance_name: the instance integration name
            response_type: the type of the response to return

        Returns:

        """
        logger.info(f"Running test-module on {_id}")
        instance = self.get_integration_instance(instance_name, response_type)
        response_data, response_code, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/settings/integration/test",
            body=instance,
            response_type=response_type,
            _request_timeout=240,
        )
        if response_code >= 300 or not response_data.get("success"):
            raise ApiException(
                f"Test connection failed - {response_data.get('message')}"
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

        Returns:
            raw response of the deleted integration
        """
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path=f"/settings/integration/{urllib.parse.quote(instance_id)}",
            response_type=response_type,
        )
        return raw_response

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
    def get_integration_instance(
        self,
        instance_name: str,
        response_type: str = "object",
    ):
        """
        Get the integration(s) module configuration(s)

        Args:
            instance_name: the instance name of the integration
            response_type: the response type to return

        Returns:
            if _id is provided, the module config of a specific integration,
            otherwise all module configs of all integrations
        """
        raw_response = self.search_integrations(response_type=response_type)
        for instance in raw_response.get("instances", []):
            if instance_name == instance.get("name"):
                return instance

        raise ValueError(f"Could not find instance for instance name '{instance_name}'")

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

        return self.client.create_incident(
            create_incident_request=create_incident_request
        )

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
            self=self.client,
            method="POST",
            path="/incidents/search",
            body={"filter": filters},
            response_type=response_type,
        )
        return raw_response

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
            self=self.client,
            method="POST",
            path="/incident/batchDelete",
            body=body,
            response_type=response_type,
        )
        return raw_response

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
            self=self.client,
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
            self=self.client,
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
        body = {"page": page, "size": size, "query": query}
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/indicators/search",
            body=body,
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
            self=self.client,
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
            self=self.client,
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
    ):
        """
        Args:
            command: the command to run
            investigation_id: investigation ID of a specific incident / playground
            should_delete_context: whether context should be deleted before executing the command
            response_type: the response type of the raw response

        Returns:
            the context after running the command
        """
        if should_delete_context:
            update_entry = {
                "investigationId": investigation_id,
                "data": "!DeleteContext all=yes",
            }

            self.client.investigation_add_entries_sync(update_entry=update_entry)

        update_entry = {"investigationId": investigation_id, "data": command}
        self.client.investigation_add_entries_sync(update_entry=update_entry)

        return self.get_investigation_context(investigation_id, response_type)

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
            self=self.client,
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
            self=self.client,
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
            self=self.client,
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
            self=self.client,
            method="POST",
            path="/playbook/delete",
            response_type=response_type,
            body={"id": _id, "name": name},
        )
        return raw_response

    @retry(exceptions=ApiException)
    def get_incident_playbook_failure(self, incident_id: str) -> Dict:
        """
        Returns the failure reason for a playbook within an incident

        Args:
            incident_id: the incident ID.

        Returns:
            mapping between the command(s) and its failure
        """
        investigation_status = self.get_investigation_status(incident_id)
        entries = investigation_status["entries"]
        error_entries = {}
        for entry in entries:
            if entry["type"] == self._ENTRY_TYPE_ERROR and entry["parentContent"]:
                # Checks for passwords and replaces them with "******"
                parent_content = re.sub(
                    r' ([Pp])assword="[^";]*"',
                    " password=******",
                    entry["parentContent"],
                )
                error_entries[
                    f"Command: {parent_content}"
                ] = f'Body:\n{entry["contents"]}'
        return error_entries

    @retry(times=20, delay=3, exceptions=ApiException)
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
            self=self.client,
            method="GET",
            path=f"/inv-playbook/{incident_id}",
            response_type=response_type,
        )
        return raw_response

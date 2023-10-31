import os
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import dateparser
import demisto_client
import requests
from demisto_client.demisto_api.models import (
    IncidentWrapper,
)
from demisto_client.demisto_api.rest import ApiException
from pydantic import BaseModel, Field, SecretStr, validator
from pydantic.fields import ModelField
from requests.auth import HTTPBasicAuth

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.utils.utils import retry_http_request


class XsoarApiClientConfig(BaseModel):
    base_url: str = Field(
        default=os.getenv("DEMISTO_BASE_URL"), description="XSOAR Tenant Base API URL"
    )
    api_key: SecretStr = Field(
        default=SecretStr(os.getenv("DEMISTO_API_KEY", "")), description="XSOAR API Key"
    )

    @validator("base_url", "api_key", always=True)
    def validate_client_config(cls, v, field: ModelField):
        if not v:
            raise ValueError(
                f"XSOAR client configuration is not complete: value was not passed for {field.name} and"
                f" the associated environment variable for {field.name} is not set"
            )
        return v


class XsoarNGApiClientConfig(XsoarApiClientConfig):
    auth_id: Optional[str] = Field(
        default=os.getenv("XSIAM_AUTH_ID"), description="XSOAR-NG Auth ID"
    )

    @validator("auth_id", always=True)
    def validate_client_config(cls, v, field: ModelField):
        if not v:
            raise ValueError(
                f"XSOAR NG client configuration is not complete: value was not passed for {field.name} and"
                f" the associated environment variable for {field.name} is not set"
            )
        return v

    @validator("base_url", always=True)
    def get_base_url(cls, v: str) -> str:
        xsoar_suffix = "xsoar"
        if not v.endswith(xsoar_suffix):
            v = f"{v}/{xsoar_suffix}"
        return v


class XsoarApiInterface(ABC):
    def __init__(
        self, xsoar_client_config: XsoarApiClientConfig, verify_ssl: bool = False
    ):
        self.base_api_url = xsoar_client_config.base_url
        self.client = demisto_client.configure(
            base_url=self.base_api_url,
            api_key=xsoar_client_config.api_key.get_secret_value(),
            auth_id=xsoar_client_config.auth_id  # type: ignore[attr-defined]
            if hasattr(xsoar_client_config, "auth_id")
            else None,
            verify_ssl=verify_ssl,
        )

    @abstractmethod
    def create_integration_instance(
        self,
        _id: str,
        name: str,
        integration_instance_config: Dict,
        response_type: str = "object",
        integration_log_level: Optional[str] = None,
        is_long_running: bool = False,
        should_enable: str = "true",
    ):
        pass

    @abstractmethod
    def delete_integration_instance(
        self, instance_id: str, response_type: str = "object"
    ):
        pass

    @abstractmethod
    def create_incident(
        self,
        name: str,
        should_create_investigation: bool = True,
        attached_playbook_id: Optional[str] = None,
    ):
        pass

    @abstractmethod
    def search_incidents(
        self,
        incident_ids: Optional[Union[List, str]] = None,
        from_date: Optional[str] = None,
        incident_types: Optional[Union[List, str]] = None,
        page: int = 0,
        size: int = 50,
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def create_indicator(
        self,
        value: str,
        indicator_type: str,
        score: int = 0,
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def delete_indicators(
        self,
        indicator_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def list_indicators(
        self,
        page: int = 0,
        size: int = 50,
        query: str = "",
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def get_indicators_whitelist(self, response_type: str = "object"):
        pass

    @abstractmethod
    def delete_indicators_from_whitelist(
        self, indicator_ids: List[str], response_type: str = "object"
    ):
        pass

    @abstractmethod
    def get_integrations_module_configuration(
        self, _id: str, response_type: str = "object"
    ):
        pass

    @abstractmethod
    def get_installed_packs(self, response_type: str = "object"):
        pass

    @abstractmethod
    def get_installed_pack(self, pack_id: str):
        pass

    @abstractmethod
    def do_long_running_instance_request(
        self,
        instance_name: str,
        url_suffix: str = "",
        headers: Optional[Dict[str, Any]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        pass

    @abstractmethod
    def run_cli_command(
        self,
        command: str,
        investigation_id: Optional[str] = None,
        response_type: str = "object",
    ):
        pass

    @abstractmethod
    def delete_playbook(self, name: str, _id: str, response_type: str = "object"):
        pass

    @abstractmethod
    def get_investigation_context(
        self, investigation_id: str, response_type: str = "object"
    ):
        pass

    @abstractmethod
    def get_playbook_state(self, incident_id: str, response_type: str = "object"):
        pass

    @abstractmethod
    def get_playground_investigation_id(self):
        pass


class XsoarNGApiClient(XsoarApiInterface):
    @property
    def external_base_url(self) -> str:
        return self.base_api_url.replace(
            "api", "ext"
        )  # url for long-running integrations

    @property
    def base_url(self) -> str:
        return re.sub(r"api-|/xsoar", "", self.base_api_url)

    @retry_http_request()
    def create_integration_instance(
        self,
        _id: str,
        name: str,
        integration_instance_config: Dict,
        response_type: str = "object",
        integration_log_level: Optional[str] = None,
        is_long_running: bool = False,
        should_enable: str = "true",
    ):
        integrations_metadata: Dict[
            str, Any
        ] = self.get_integrations_module_configuration(_id)

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
            "name": name,
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
        return raw_response

    @retry_http_request()
    def delete_integration_instance(
        self, instance_id: str, response_type: str = "object"
    ):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path=f"/settings/integration/{urllib.parse.quote(instance_id)}",
            response_type=response_type,
        )
        return raw_response

    @retry_http_request()
    def create_incident(
        self,
        name: str,
        should_create_investigation: bool = True,
        attached_playbook_id: Optional[str] = None,
    ) -> IncidentWrapper:
        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = should_create_investigation
        create_incident_request.playbook_id = attached_playbook_id

        create_incident_request.name = name

        return self.client.create_incident(
            create_incident_request=create_incident_request
        )

    @retry_http_request()
    def search_incidents(
        self,
        incident_ids: Optional[Union[List, str]] = None,
        from_date: Optional[str] = None,
        incident_types: Optional[Union[List, str]] = None,
        page: int = 0,
        size: int = 50,
        response_type: str = "object",
    ):

        filters = {"page": page, "size": size}

        if incident_ids:
            if isinstance(incident_ids, str):
                incident_ids = [incident_ids]
            filters["id"] = incident_ids

        if from_date:
            filters["fromDate"] = dateparser.parse(from_date).strftime(
                "%Y-%m-%dT%H:%M:%S.000+00:00"
            )

        if incident_types:
            if isinstance(incident_types, str):
                incident_types = [incident_types]
            filters["type"] = incident_types

        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/incidents/search",
            body={"filter": filters},
            response_type=response_type,
        )
        return raw_response

    @retry_http_request()
    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
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

    @retry_http_request()
    def create_indicator(
        self,
        value: str,
        indicator_type: str,
        score: int = 0,
        response_type: str = "object",
    ):

        whitelisted_indicators_raw_response = self.get_indicators_whitelist()
        for indicator in whitelisted_indicators_raw_response:
            if indicator.get("value") == value:
                raise ApiException(
                    status=400,
                    reason=f"Cannot create the indicator={value} type={indicator_type} because it is in the exclusion list",
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

    @retry_http_request()
    def delete_indicators(
        self,
        indicator_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        should_exclude: bool = False,
        response_type: str = "object",
    ):
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
        return raw_response

    @retry_http_request()
    def list_indicators(
        self,
        page: int = 0,
        size: int = 50,
        query: str = "",
        response_type: str = "object",
    ):
        body = {"page": page, "size": size, "query": query}
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/indicators/search",
            body=body,
            response_type=response_type,
        )
        return raw_response

    @retry_http_request()
    def get_indicators_whitelist(self, response_type: str = "object"):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="GET",
            path="/indicators/whitelisted",
            response_type=response_type,
        )
        return raw_response

    @retry_http_request()
    def delete_indicators_from_whitelist(
        self, indicator_ids: List[str], response_type: str = "object"
    ):
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

    @retry_http_request()
    def get_integrations_module_configuration(
        self, _id: Optional[str] = None, response_type: str = "object"
    ):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/settings/integration/search",
            response_type=response_type,
        )
        if not _id:
            return raw_response
        for config in raw_response.get("configurations") or []:
            if config.get("id") == _id:
                return config

        raise ValueError(
            f"Could not find module configuration for integration ID '{_id}'"
        )

    @retry_http_request()
    def get_installed_packs(self, response_type: str = "object"):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="GET",
            path="/contentpacks/metadata/installed",
            response_type=response_type,
        )
        return raw_response

    def get_installed_pack(self, pack_id: str) -> Dict[str, Any]:
        for pack_info in self.get_installed_packs():
            if pack_info.get("id") == pack_id:
                return pack_info
        raise ValueError(f"pack ID {pack_id} does not exist in {self.base_url}")

    @retry_http_request(times=20)
    def do_long_running_instance_request(
        self,
        instance_name: str,
        url_suffix: str = "",
        headers: Optional[Dict[str, Any]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> requests.Response:
        if url_suffix and not url_suffix.startswith("/"):
            url_suffix = f"/{url_suffix}"
        url = f"{self.external_base_url}/instance/execute/{instance_name}{url_suffix}"
        auth = HTTPBasicAuth(username, password) if username and password else None
        return requests.get(url, auth=auth, headers=headers)

    @retry_http_request()
    def run_cli_command(
        self,
        command: str,
        investigation_id: Optional[str] = None,
        response_type: str = "object",
    ):

        if not investigation_id:
            investigation_id = self.get_playground_investigation_id()

        update_entry = {
            "investigationId": investigation_id,
            "data": "!DeleteContext all=yes",
        }

        self.client.investigation_add_entries_sync(update_entry=update_entry)

        update_entry = {"investigationId": investigation_id, "data": command}
        response = self.client.investigation_add_entries_sync(update_entry=update_entry)

        context = self.get_investigation_context(investigation_id)
        return response, context

    @retry_http_request()
    def get_investigation_context(
        self, investigation_id: str, response_type: str = "object"
    ):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path=f"/investigation/{investigation_id}/context",
            response_type=response_type,
            body={"query": "${.}"},
        )
        return raw_response

    @retry_http_request()
    def delete_playbook(self, name: str, _id: str, response_type: str = "object"):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/playbook/delete",
            response_type=response_type,
            body={"id": _id, "name": name},
        )
        return raw_response

    @retry_http_request(times=20, delay=3)
    def get_playbook_state(self, incident_id: str, response_type: str = "object"):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="GET",
            path=f"/inv-playbook/{incident_id}",
            response_type=response_type,
        )
        return raw_response

    @retry_http_request()
    def get_playground_investigation_id(self):

        response = self.client.search_investigations(filter={"filter": {"type": [9], "page": page}})
        for entry in response.data:
            if entry.name == "Playground":
                return entry.id

        raise ValueError("Could not find any playground.")

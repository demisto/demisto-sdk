import os
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from pydantic import BaseModel, Field, SecretStr, validator
from pydantic.fields import ModelField

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
    ):
        pass

    @abstractmethod
    def delete_integration_instance(
        self, instance_id: str, response_type: str = "object"
    ):
        pass

    @abstractmethod
    def get_incident(self, incident_id: str, response_type: str = "object"):
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
    def get_integrations_module_configuration(
        self, _id: str, response_type: str = "object"
    ):
        pass


class XsoarNGApiClient(XsoarApiInterface):
    @property
    def external_base_url(self):
        return self.base_api_url.replace(
            "api", "ext"
        )  # url for long-running integrations

    @retry_http_request()
    def create_integration_instance(
        self,
        _id: str,
        name: str,
        integration_instance_config: Dict,
        response_type: str = "object",
    ):
        integrations_metadata: Dict[
            str, Any
        ] = self.get_integrations_module_configuration(_id)

        integration_instance_body_request = {
            "brand": integrations_metadata["name"],
            "category": integrations_metadata["category"],
            "configuration": integrations_metadata,
            "data": [],
            "enabled": "true",
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

        module_configuration: List[Dict[str, Any]] = integrations_metadata[
            "configuration"
        ]

        # update the integration configuration according to the module configuration in xsoar DB
        for param_conf in module_configuration:
            display = param_conf["display"]
            name = param_conf["name"]
            default_value = param_conf["defaultValue"]

            if (key := integration_instance_config.get(display)) or (
                key := integration_instance_config.get(name)
            ):
                if key in {"credentials", "creds_apikey"}:
                    credentials = integration_instance_config[key]
                    param_value = {
                        "credential": "",
                        "identifier": credentials.get("identifier", ""),
                        "password": credentials["password"],
                        "passwordChanged": False,
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
    def get_incident(self, incident_id: str, response_type: str = "object"):
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/public/v1/incidents/search",
            body={"filters": {"id": incident_id}},
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
            path="/incidents/batchDelete",
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
        raw_response, status_code, _ = demisto_client.generic_request_func(
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
    def get_integrations_module_configuration(
        self, _id: Optional[str] = None, response_type: str = "object"
    ) -> Union[List, Dict[str, Any]]:
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

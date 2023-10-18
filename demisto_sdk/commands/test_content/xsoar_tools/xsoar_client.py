import ast
import os
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from pydantic import BaseModel, Field, HttpUrl, SecretStr


class XsoarApiClientConfig(BaseModel):
    base_url: HttpUrl = Field(
        default=os.getenv("DEMISTO_BASE_URL"), description="XSIAM Tenant Base URL"
    )
    api_key: SecretStr = Field(
        default=SecretStr(os.getenv("DEMISTO_API_KEY", "")), description="XSIAM API Key"
    )
    auth_id: Optional[str] = Field(
        default=os.getenv("XSIAM_AUTH_ID"), description="XSIAM Auth ID"
    )


class XsoarApiInterface(ABC):
    def __init__(self, xsoar_client_config: XsoarApiClientConfig):
        self.base_url = xsoar_client_config.base_url
        self.client = demisto_client.configure(
            base_url=self.base_url,
            api_key=xsoar_client_config.api_key.get_secret_value(),
            auth_id=xsoar_client_config.auth_id,
            verify_ssl=False,
        )

    @abstractmethod
    def create_integration_instance(
        self, _id: str, name: str, integration_instance_config: Dict
    ):
        pass

    @abstractmethod
    def delete_integration_instance(self, instance_id: str):
        pass

    @abstractmethod
    def get_incident(self, incident_id: str):
        pass

    @abstractmethod
    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
    ):
        pass

    @abstractmethod
    def create_indicator(self, value: str, indicator_type: str, score: int = 0):
        pass

    @abstractmethod
    def delete_indicators(
        self,
        indicator_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
    ):
        pass

    @abstractmethod
    def get_integrations_module_configuration(self, _id: str):
        pass


class XsoarNGApiClient(XsoarApiInterface):

    @property
    def external_base_url(self):
        return self.base_url.replace("api", "ext")  # url for long-running integrations

    def create_integration_instance(
        self, _id: str, name: str, integration_instance_config: Dict
    ):
        integrations_metadata: Dict[str, Any] = self.get_integrations_module_configuration(_id)

        module_instance = {
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

        module_configuration: List[Dict[str, Any]] = integrations_metadata["configuration"]

        for param_conf in module_configuration:
            if param_conf["display"] in integration_instance_config or param_conf["name"] in integration_instance_config:
                # param defined in conf
                key = (
                    param_conf["display"]
                    if param_conf["display"] in integration_instance_config
                    else param_conf["name"]
                )
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
            elif param_conf["defaultValue"]:
                # param is required - take default value
                param_conf["value"] = param_conf["defaultValue"]
            module_instance["data"].append(param_conf)

        return demisto_client.generic_request_func(
            self=self.client,
            method="PUT",
            path="/xsoar/settings/integration",
            body=module_instance,
        )

    def delete_integration_instance(self, instance_id: str):
        return demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path=f"/xsoar/settings/integration/{urllib.parse.quote(instance_id)}",
        )

    def get_incident(self, incident_id: str):
        return demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/xsoar/public/v1/incidents/search",
            body={"filters": {"id": incident_id}},
        )

    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
    ):
        if isinstance(incident_ids, str):
            incident_ids = [incident_ids]
        body = {"ids": incident_ids, "filter": filters or {}, "all": _all}
        return demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path="/xsoar/incident/batchDelete",
            body=body,
        )

    def create_indicator(self, value: str, indicator_type: str, score: int = 0):
        return demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/xsoar/indicator/create",
            body={
                "indicator": {
                    "value": value,
                    "indicator_type": indicator_type,
                    "score": score,
                }
            },
        )

    def delete_indicators(
        self,
        indicator_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        should_exclude: bool = False
    ):
        if isinstance(indicator_ids, str):
            indicator_ids = [indicator_ids]
        body = {"ids": indicator_ids, "filter": filters or {}, "all": _all, "DoNotWhitelist": not should_exclude}
        return demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path="/xsoar/indicator/batchDelete",
            body=body,
        )

    def get_integrations_module_configuration(self, _id: Optional[str] = None) -> Union[List, Dict[str, Any]]:
        raw_response, _, _ = demisto_client.generic_request_func(
            self=self.client,
            method="POST",
            path="/xsoar/settings/integration/search",
        )
        response = ast.literal_eval(raw_response)
        if not _id:
            return response
        for config in response.get("configurations") or []:
            if config.get("id") == _id:
                return config

        raise ValueError(f'Could not find module configuration for integration ID {_id}')



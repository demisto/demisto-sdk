import os
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import demisto_client
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
        self.client = demisto_client.configure(
            base_url=xsoar_client_config.base_url,
            api_key=xsoar_client_config.api_key.get_secret_value(),
            auth_id=xsoar_client_config.auth_id,
            verify_ssl=False,
        )

    @abstractmethod
    def create_integration_instance(
        self, instance_name: str, instance_configuration: Dict[str, Any]
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


class XsoarNGApiClient(XsoarApiInterface):
    def create_integration_instance(
        self, instance_name: str, instance_configuration: Dict[str, Any]
    ):
        return demisto_client.generic_request_func(
            self=self.client,
            method="PUT",
            path="/xsoar/settings/integration",
            body=instance_configuration,
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
    ):
        if isinstance(indicator_ids, str):
            indicator_ids = [indicator_ids]
        body = {"ids": indicator_ids, "filter": filters or {}, "all": _all}
        return demisto_client.generic_request_func(
            self=self.client,
            method="DELETE",
            path="/xsoar/indicator/batchDelete",
            body=body,
        )

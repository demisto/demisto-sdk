import gzip
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from pprint import pformat
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from packaging.version import Version
from pydantic import BaseModel, Field, HttpUrl, SecretStr, validator
from pydantic.fields import ModelField
from requests.exceptions import ConnectionError, Timeout

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry

json = JSON_Handler()


class XsiamApiClientConfig(BaseModel):
    base_url: HttpUrl = Field(
        default=os.getenv("DEMISTO_BASE_URL"), description="XSIAM Tenant Base URL"
    )
    api_key: SecretStr = Field(
        default=SecretStr(os.getenv("DEMISTO_API_KEY", "")), description="XSIAM API Key"
    )
    auth_id: str = Field(
        default=os.getenv("XSIAM_AUTH_ID"), description="XSIAM Auth ID"
    )
    token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv("XSIAM_TOKEN", "")), description="XSIAM Token"
    )
    collector_token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv("XSIAM_COLLECTOR_TOKEN", "")),
        description="XSIAM HTTP Collector Token",
    )

    @validator("base_url", "api_key", "auth_id", always=True)
    def validate_client_config(cls, v, field: ModelField):
        if not v:
            raise ValueError(
                f"XSIAM client configuration is not complete: value was not passed for {field.name} and"
                f" the associated environment variable for {field.name} is not set"
            )
        return v

    @validator("collector_token", always=True)
    def validate_client_config_token(cls, v, values, field: ModelField):
        if not v:
            other_token_name = "token"
            if not values.get(other_token_name):
                raise ValueError(
                    f'XSIAM client configuration is not complete: you must set one of "{field.name}" or '
                    f'"{other_token_name}" either explicitly on the command line or via their associated '
                    "environment variables"
                )
        return v


class XsiamApiInterface(ABC):
    @abstractmethod
    def uninstall_packs(self, pack_ids: List[str]):
        pass

    @abstractmethod
    def upload_packs(self, zip_path: Path):
        pass

    @abstractmethod
    def install_packs(self, packs: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def push_to_dataset(
        self,
        data: List[Dict[str, Any]],
        vendor: str,
        product: str,
        data_format: str = "json",
    ):
        pass

    @abstractmethod
    def start_xql_query(self, query: str):
        pass

    @abstractmethod
    def get_xql_query_result(self, execution_id: str):
        pass


class XsiamApiClient(XsiamApiInterface):
    def __init__(self, config: XsiamApiClientConfig):
        self.base_url = config.base_url
        self.api_key = (
            config.api_key.get_secret_value()
            if isinstance(config.api_key, SecretStr)
            else config.api_key
        )
        self.auth_id = config.auth_id
        self.token = (
            config.token.get_secret_value()
            if isinstance(config.token, SecretStr)
            else config.token
        )
        self.collector_token = (
            config.collector_token.get_secret_value()
            if isinstance(config.collector_token, SecretStr)
            else config.collector_token
        )
        self.__session: requests.Session = None  # type: ignore

    @property
    def _session(self) -> requests.Session:
        if not self.__session:
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "x-xdr-auth-id": self.auth_id,
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                }
            )
        return self.__session

    @_session.setter
    def _session(self, value: requests.Session):
        self.__session = value

    @lru_cache
    @retry(times=5, exceptions=(RuntimeError, ConnectionError, Timeout))
    def get_demisto_version(self) -> Version:
        endpoint = urljoin(self.base_url, "xsoar/about")
        response = self._session.get(endpoint)
        response.raise_for_status()
        data = response.json()
        demisto_version = data.get("demistoVersion")
        if not demisto_version:
            raise RuntimeError("Could not get the tenant's demisto version")
        logger.info(
            f"[green]Demisto version of XSIAM tenant is {demisto_version}[/green]",
            extra={"markup": True},
        )
        return Version(demisto_version)

    @property
    def installed_packs(self) -> List[Dict[str, Any]]:
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/metadata/installed")
        response = self._session.get(endpoint)
        response.raise_for_status()
        return response.json()

    def search_marketplace(self, filter_json: dict):
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/marketplace/search")
        response = self._session.post(endpoint, json=filter_json)
        response.raise_for_status()
        return response.json()

    def search_data_sources(self, filter_json: dict):
        endpoint = urljoin(self.base_url, "xsoar/settings/datasourcepack/search")
        response = self._session.post(endpoint, json=filter_json)
        response.raise_for_status()
        return response.json()

    def search_pack(self, pack_id):
        endpoint = urljoin(self.base_url, f"xsoar/contentpacks/marketplace/{pack_id}")
        response = self._session.get(endpoint)
        response.raise_for_status()
        logger.debug(f'Found pack "{pack_id}" in bucket!')
        data = response.json()
        pack_data = {"id": data.get("id"), "version": data.get("currentVersion")}
        return pack_data

    def uninstall_packs(self, pack_ids: List[str]):
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/installed/delete")
        body = {"IDs": pack_ids}
        response = self._session.post(endpoint, json=body)
        response.raise_for_status()

    def upload_packs(self, zip_path: Path):
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/installed/upload")
        header_params = {"Content-Type": "multipart/form-data"}
        file_path = os.path.abspath(zip_path)
        files = {"file": file_path}
        response = self._session.post(endpoint, files=files, headers=header_params)
        response.raise_for_status()
        logger.info(
            f"All packs from file {zip_path} were successfully installed on server {self.base_url}"
        )

    def install_packs(self, packs: List[Dict[str, Any]]):
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/marketplace/install")
        response = self._session.post(
            url=endpoint, json={"packs": packs, "ignoreWarnings": True}
        )
        response.raise_for_status()
        if response.status_code in range(200, 300) and response.status_code != 204:
            response_data = response.json()
            packs_data = [
                {"ID": pack.get("id"), "CurrentVersion": pack.get("currentVersion")}
                for pack in response_data
            ]
            logger.info(f"Packs were successfully installed on server {self.base_url}")
            logger.debug(
                f"The packs that were successfully installed on server {self.base_url}:\n{packs_data}"
            )
        elif response.status_code == 204:
            logger.info(
                f"All packs were successfully installed on server {self.base_url}"
            )

    def sync_marketplace(self):
        endpoint = urljoin(self.base_url, "xsoar/contentpacks/marketplace/sync")
        response = self._session.post(endpoint)
        response.raise_for_status()
        logger.info(f"Marketplace was successfully synced on server {self.base_url}")

    def push_to_dataset(
        self,
        data: List[Dict[str, Any]],
        vendor: str,
        product: str,
        data_format: str = "json",
    ):
        if self.token:
            endpoint = urljoin(self.base_url, "logs/v1/xsiam")
            additional_headers = {
                "authorization": self.token,
                "format": data_format,
                "product": product,
                "vendor": vendor,
                "content-encoding": "gzip",
            }
            token_type = "xsiam_token"
        elif self.collector_token:
            endpoint = urljoin(self.base_url, "logs/v1/event")
            additional_headers = {
                "authorization": self.collector_token,
                "content-type": "application/json"
                if data_format.casefold == "json"
                else "text/plain",
                "content-encoding": "gzip",
            }
            token_type = "collector_token"

        formatted_data = "\n".join([json.dumps(d) for d in data])
        compressed_data = gzip.compress(formatted_data.encode("utf-8"))
        response = self._session.post(
            endpoint, data=compressed_data, headers=additional_headers
        )
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:  # type: ignore[attr-defined]
            error = response.text
            err_msg = f"Failed to push using {token_type} - with status code {response.status_code}"
            err_msg += f"\n{error}" if error else ""
            logger.error(err_msg)
            response.raise_for_status()
        if response.status_code in range(200, 300):
            return data
        else:
            logger.error(
                f"Failed to push using {token_type} - with status code {response.status_code}\n{pformat(data)}"
            )
            response.raise_for_status()

    def start_xql_query(self, query: str):
        body = {"request_data": {"query": query}}
        endpoint = urljoin(self.base_url, "public_api/v1/xql/start_xql_query/")
        logger.info(f"Starting xql query:\nendpoint={endpoint}\n{query=}")
        response = self._session.post(endpoint, json=body)
        logger.debug("Request completed to start xql query")
        data = response.json()

        if response.status_code in range(200, 300):
            execution_id: str = data.get("reply", "")
            return execution_id
        response.raise_for_status()

    def get_xql_query_result(self, execution_id: str, timeout: int = 300):
        payload = json.dumps(
            {
                "request_data": {
                    "query_id": execution_id,
                    "pending_flag": False,
                    "limit": 1000,
                    "format": "json",
                }
            }
        )
        endpoint = urljoin(self.base_url, "public_api/v1/xql/get_query_results/")
        logger.info(f"Getting xql query results: endpoint={endpoint}")
        response = self._session.post(endpoint, data=payload, timeout=timeout)
        logger.debug("Request completed to get xql query results")
        data = response.json()
        logger.debug(pformat(data))

        if (
            response.status_code in range(200, 300)
            and data.get("reply", {}).get("status", "") == "SUCCESS"
        ):
            return data.get("reply", {}).get("results", {}).get("data", [])
        response.raise_for_status()

    def delete_dataset(self, dataset_id: str):
        endpoint = urljoin(self.base_url, "public_api/v1/xql/delete_dataset")
        body = {"dataset_name": dataset_id}
        response = self._session.post(endpoint, json=body)
        response.raise_for_status()

import gzip
from pprint import pformat
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests
from demisto_client.demisto_api.api.default_api import DefaultApi
from demisto_client.demisto_api.rest import ApiException
from pydantic import validator
from requests import Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.configs import (
    XsiamClientConfig,
)
from demisto_sdk.commands.common.clients.xsoar_saas.xsoar_saas_api_client import (
    XsoarSaasClient,
)
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER
from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry

json = DEFAULT_JSON_HANDLER


class XsiamClient(XsoarSaasClient):
    """
    api client for xsiam
    """

    marketplace = MarketplaceVersions.MarketplaceV2

    @classmethod
    def is_xsiam(cls, _client: DefaultApi, product_mode: Optional[str] = None):
        """
        Returns whether the configured client is xsiam.
        """
        if product_mode == "xsiam":
            return True

        # for old environments that do not have product-mode / deployment-mode
        try:
            # /ioc-rules is only an endpoint in XSIAM.
            response, status_code, response_headers = _client.generic_request(
                "/ioc-rules", "GET"
            )
        except ApiException:
            return False

        if (
            "text/html" in response_headers.get("Content-Type")
            or status_code != requests.codes.ok
        ):
            return False

        return True

    @classmethod
    @retry(exceptions=RequestException)
    def is_xsiam_server_healthy(
        cls, session: Session, config: XsiamClientConfig
    ) -> bool:
        """
        Validates that XSIAM instance is healthy.

        Returns:
            bool: True if XSIAM server is healthy, False if not.
        """
        url = urljoin(config.base_api_url, "public_api/v1/healthcheck")
        response = session.get(url)
        response.raise_for_status()
        try:
            xsiam_health_status = (response.json().get("status") or "").lower()
            logger.debug(f"The status of XSIAM health is {xsiam_health_status}")
            return (
                response.status_code == requests.codes.ok
                and xsiam_health_status == "available"
            )
        except JSONDecodeError as e:
            logger.debug(
                f"Could not validate if XSIAM {config.base_api_url} is healthy, error:\n{e}"
            )
            return False

    @validator("session", always=True)
    def get_xdr_session(cls, v: Optional[Session], values: Dict[str, Any]) -> Session:
        session = v or super().get_xdr_session(v, values)
        config = values["config"]
        if cls.is_xsiam_server_healthy(session, config):
            return session
        raise RuntimeError(
            f"Could not connect to XSIAM server {config.base_api_url}, check your configurations are valid"
        )

    """
    #############################
    xsoar related methods
    #############################
    """

    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
        # if in the future it will be possible to delete incidents in XSIAM, implement this method
        raise NotImplementedError("it is not possible to delete incidents in XSIAM")

    """
    #############################
    datasets related methods
    #############################
    """

    def push_to_dataset(
        self,
        data: List[Dict[str, Any]],
        vendor: str,
        product: str,
        data_format: str = "json",
    ):
        if self.config.token:
            endpoint = urljoin(self.config.base_api_url, "logs/v1/xsiam")
            additional_headers = {
                "authorization": self.config.token,
                "format": data_format,
                "product": product,
                "vendor": vendor,
                "content-encoding": "gzip",
            }
            token_type = "xsiam_token"
        elif self.config.collector_token:
            endpoint = urljoin(self.config.base_api_url, "logs/v1/event")
            additional_headers = {
                "authorization": self.config.collector_token,
                "content-type": "application/json"
                if data_format.casefold == "json"
                else "text/plain",
                "content-encoding": "gzip",
            }
            token_type = "collector_token"
        else:
            raise ValueError(
                "XSIAM_TOKEN or XSIAM_COLLECTOR_TOKEN is missing for pushing logs"
            )

        formatted_data = "\n".join([json.dumps(d) for d in data])
        compressed_data = gzip.compress(formatted_data.encode("utf-8"))
        response = self.session.post(
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

    def delete_dataset(self, dataset_id: str):
        endpoint = urljoin(self.config.base_api_url, "public_api/v1/xql/delete_dataset")
        body = {"dataset_name": dataset_id}
        response = self.session.post(endpoint, json=body)
        response.raise_for_status()

    """
    #############################
    XQL related methods
    #############################
    """

    def start_xql_query(self, query: str):
        body = {"request_data": {"query": query}}
        endpoint = urljoin(
            self.config.base_api_url, "public_api/v1/xql/start_xql_query/"
        )
        logger.info(f"Starting xql query:\nendpoint={endpoint}\n{query=}")
        response = self.session.post(endpoint, json=body)
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
        endpoint = urljoin(
            self.config.base_api_url, "public_api/v1/xql/get_query_results/"
        )
        logger.info(f"Getting xql query results: endpoint={endpoint}")
        response = self.session.post(endpoint, data=payload, timeout=timeout)
        logger.debug("Request completed to get xql query results")
        data = response.json()
        logger.debug(pformat(data))

        if (
            response.status_code in range(200, 300)
            and data.get("reply", {}).get("status", "") == "SUCCESS"
        ):
            return data.get("reply", {}).get("results", {}).get("data", [])
        response.raise_for_status()

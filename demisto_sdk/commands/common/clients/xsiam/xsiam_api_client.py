import gzip
from pprint import pformat
from typing import Any, Dict, List, Union
from urllib.parse import urljoin

import requests
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import ServerType
from demisto_sdk.commands.common.clients.xsoar_saas.xsoar_saas_api_client import (
    XsoarSaasClient,
)
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER
from demisto_sdk.commands.common.logger import logger

json = DEFAULT_JSON_HANDLER


class XsiamClient(XsoarSaasClient):
    """
    api client for xsiam
    """

    @property
    def is_server_type(self) -> bool:
        about = self.about
        if about.product_mode == "xsiam":
            return True

        try:
            self.get_ioc_rules()
            return True
        except ApiException as error:
            logger.debug(f"{self} is not {self.server_type} server, error: {error}")
            return False

    @property
    def server_type(self) -> ServerType:
        return ServerType.XSIAM

    @property
    def marketplace(self) -> MarketplaceVersions:
        return MarketplaceVersions.MarketplaceV2

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
        if self.server_config.token:
            endpoint = urljoin(self.server_config.base_api_url, "logs/v1/xsiam")
            additional_headers = {
                "authorization": self.server_config.token,
                "format": data_format,
                "product": product,
                "vendor": vendor,
                "content-encoding": "gzip",
            }
            token_type = "xsiam_token"
        elif self.server_config.collector_token:
            endpoint = urljoin(self.server_config.base_api_url, "logs/v1/event")
            additional_headers = {
                "authorization": self.server_config.collector_token,
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
        response = self._xdr_client.post(
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
        endpoint = urljoin(
            self.server_config.base_api_url, "public_api/v1/xql/delete_dataset"
        )
        body = {"dataset_name": dataset_id}
        response = self._xdr_client.post(endpoint, json=body)
        response.raise_for_status()

    """
    #############################
    XQL related methods
    #############################
    """

    def start_xql_query(self, query: str):
        body = {"request_data": {"query": query}}
        endpoint = urljoin(
            self.server_config.base_api_url, "public_api/v1/xql/start_xql_query/"
        )
        logger.info(f"Starting xql query:\nendpoint={endpoint}\n{query=}")
        response = self._xdr_client.post(endpoint, json=body)
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
            self.server_config.base_api_url, "public_api/v1/xql/get_query_results/"
        )
        logger.info(f"Getting xql query results: endpoint={endpoint}")
        response = self._xdr_client.post(endpoint, data=payload, timeout=timeout)
        logger.debug("Request completed to get xql query results")
        data = response.json()
        logger.debug(pformat(data))

        if (
            response.status_code in range(200, 300)
            and data.get("reply", {}).get("status", "") == "SUCCESS"
        ):
            return data.get("reply", {}).get("results", {}).get("data", [])
        response.raise_for_status()

    """
    #############################
    IOC related methods
    #############################
    """

    def get_ioc_rules(self):
        # /ioc-rules is only an endpoint in XSIAM.
        response, status_code, response_headers = self._xsoar_client.generic_request(
            "/ioc-rules", "GET", response_type="object"
        )
        if (
            "text/html" in response_headers.get("Content-Type")
            or status_code != requests.codes.ok
        ):
            raise ApiException(
                status=404, reason=f'{self} does not have "/ioc-rules" endpoint'
            )

        return response

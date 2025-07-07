import gzip
from pprint import pformat
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import requests
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import ServerType
from demisto_sdk.commands.common.clients.xsoar_saas.xsoar_saas_api_client import (
    XsoarSaasClient,
)
from demisto_sdk.commands.common.constants import MarketplaceVersions, XsiamAlertState
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER
from demisto_sdk.commands.common.logger import logger

json = DEFAULT_JSON_HANDLER
GET_ALERTS_BATCH_SIZE = 100


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
            logger.debug(  # noqa: PLE1205
                "{}",
                f"<cyan>{self} is not {self.server_type} server, error: {error}</cyan>",
            )
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

    """
    #############################
    Alerts related methods
    #############################
    """

    def create_alert_from_json(self, json_content: dict) -> str:
        """Creates a custom XSIAM alert.

        Args:
            json_content (dict): A dictionary containing mandatory fields (vendor, product, severity, category)
                                 and other fields that appears in the alert table.

        Returns:
            str: The alert *external* ID.
                 Use `XsiamClient.get_internal_alert_id()` to get the alert *internal* ID for other actions (e.g. polling alert state).

        Example:
        >>> create_alert_from_json({"description": "My alert desc", "severity": "Low", "vendor": "Example", "product": "Example", "category": "Other"})
        "31c7c088-126b-4e0e-9523-85080c03753e"
        """
        # https://docs-cortex.paloaltonetworks.com/r/Cortex-XSIAM-REST-API/Create-a-Custom-Alert
        alert_payload = {"request_data": {"alert": json_content}}
        endpoint = urljoin(
            self.server_config.base_api_url, "/public_api/v1/alerts/create_alert"
        )
        res = self._xdr_client.post(endpoint, json=alert_payload)
        alert_data = self._process_response(res, res.status_code, 200)
        return alert_data["reply"]

    def get_internal_alert_id(self, alert_external_id: str) -> int:
        data = self.search_alerts(
            filters=[
                {
                    "field": "external_id_list",
                    "operator": "in",
                    "value": [alert_external_id],
                }
            ]
        )
        return data["alerts"][0]["alert_id"]

    def poll_alert_state(
        self,
        alert_id: str,
        expected_states: Tuple[XsiamAlertState, ...] = (XsiamAlertState.RESOLVED,),
        timeout: int = 120,
    ) -> dict:
        """
        Polls for the state of an XSIAM alert until it matches any of the expected states or times out.

        Args:
            alert_id (str): The XSIAM alert ID to poll its state.
            expected_states (Tuple[XsiamAlertState, ...]): The states the XSIAM alert is expected to reach.
            timeout (int): The time limit in seconds to wait for the expected states, defaults to 120.

        Returns:
            dict: Raw response of the XSIAM alert that reached the relevant state.

        Raises:
            PollTimeout: If the alert did not reach any of the expected states in time.

        Example:
            >>> client.poll_alert_state("123", expected_states=(XsiamAlertState.RESOLVED,))
            {"id": "123", "name": "My name", "details": "My description", "labels": [], ... }
        """
        return super().poll_incident_state(alert_id, expected_states, timeout)

    def poll_incident_state(self, *args, **kwargs):
        """Overrides method from `XsoarClient`. Raises `NotImplementedError` to prevent usage in `XsiamClient`.

        Raises:
            NotImplementedError: When connected to an XSIAM tenant.
        """
        raise NotImplementedError(
            "This method is not implemented in XsiamClient. Use poll_alert_state instead."
        )

    def update_alert(self, alert_id: Union[str, list[str]], updated_data: dict) -> dict:
        """
        Args:
            alert_id (str | list[str]): alert ids to edit.
            updated_data (dict): The data to update the alerts with. https://cortex-panw.stoplight.io/docs/cortex-xsiam-1/rpt3p1ne2bwfe-update-alerts
        """
        alert_payload = {
            "request_data": {"update_data": updated_data, "alert_id_list": alert_id}
        }
        endpoint = urljoin(
            self.server_config.base_api_url, "/public_api/v1/alerts/update_alerts"
        )
        res = self._xdr_client.post(endpoint, json=alert_payload)
        alert_data = self._process_response(res, res.status_code, 200)
        return alert_data

    def search_alerts(
        self,
        filters: list = None,
        search_from: int = None,
        search_to: int = None,
        sort: dict = None,
    ) -> dict:
        """
        filters should be a list of dicts contains field, operator, value.
        For example:
        [{field: alert_id_list, operator: in, value: [1,2,3,4]}]
        Allowed values for fields - alert_id_list, alert_source, severity, creation_time
        """
        logger.debug(
            f"Searching alerts by filters: {filters}. "
            f"Start offset: {search_from}, end offset: {search_to}."
        )
        body = {
            "request_data": {
                "filters": filters,
                "search_from": search_from,
                "search_to": search_to,
                "sort": sort,
            }
        }
        endpoint = urljoin(
            self.server_config.base_api_url, "/public_api/v1/alerts/get_alerts/"
        )
        res = self._xdr_client.post(endpoint, json=body)
        return self._process_response(res, res.status_code, 200)["reply"]

    def _search_alerts_by_values(
        self,
        filters: Optional[list],
        match_values: Optional[list],
        match_function: Callable[[dict, tuple], bool],
    ) -> list[str]:
        """
        Applies a custom matching function to determine if each alert should be included based
        on given values.

        Args:
            filters (Optional[list]): A list of field filters to apply during the alert search.
            match_values (Optional[list]): A list of values to check using the `match_function`.
            match_function (Callable[[dict, tuple], bool]): A function that takes an alert dictionary
                                                            and a `match_values` tuple. Returns True
                                                            if matches, False otherwise.

        Returns:
            list[str]: A list of alert IDs that match the specified criteria.
        """
        match_values: tuple[str, ...] = tuple(match_values or [])
        alert_ids: list[str] = []

        # If not specified, API uses search_from = 0 and search_to = 100 by default
        res = self.search_alerts(filters=filters)
        alerts: list[dict] = res.get("alerts", [])
        cumulative_count: int = res.get("result_count", 0)  # Count of results so far

        while len(alerts) > 0 and len(match_values) > len(alert_ids):
            for alert in alerts:
                if match_function(alert, match_values):
                    alert_ids.append(alert.get("alert_id", ""))

            search_from = cumulative_count  # Start offset
            search_to = cumulative_count + GET_ALERTS_BATCH_SIZE  # End offset
            # Advance start and end alert offsets for the next search batch
            res = self.search_alerts(
                filters=filters,
                search_from=search_from,
                search_to=search_to,
            )
            alerts = res.get("alerts", [])
            cumulative_count += res.get("result_count", 0)

        return alert_ids

    def search_alerts_by_uuid(
        self,
        alert_uuids: Optional[list] = None,
        filters: Optional[list] = None,
    ) -> list[str]:
        """
        Finds alerts where the description ends with any given UUIDs.

        Args:
            alert_uuids (Optional[list]): A list of UUIDs to check against the alert descriptions.
                                          If None, no UUID-specific search is conducted.
            filters (Optional[list]): A list of field filters to apply during the alert search.

        Returns:
            list[str]: A list of alert IDs where the descriptions end with any of the UUIDs.

        Example:
            >>> client.search_alerts_by_uuid(["550e8400-e29b-41d4-a716-446655440000"], [{"field": "creation_time", "operator": "gte", "value": 1745309363}])
            ["54"]
        """
        return self._search_alerts_by_values(
            filters,
            alert_uuids,
            lambda alert, uuids: alert.get("description", "").endswith(uuids),
        )

    def search_alerts_by_name(
        self,
        alert_names: Optional[list] = None,
        filters: Optional[list] = None,
    ) -> list[str]:
        """
        Finds alerts where the name exactly matches any of the given names.

        Args:
            alert_names (Optional[list]): A list of names to check against the alert names.
                                          If None, no name-specific search is conducted.
            filters (Optional[list]): A list of field filters to apply during the alert search.

        Returns:
            list[str]: A list of alert IDs that exactly match any of the names.

        Example:
            >>> client.search_alerts_by_name(["My Alert"], [{"field": "alert_id_list", "operator": "in", "value": [1, 2, 3]}])
            ["1"]
        """
        return self._search_alerts_by_values(
            filters,
            alert_names,
            lambda alert, names: alert.get("name", "") in names,
        )

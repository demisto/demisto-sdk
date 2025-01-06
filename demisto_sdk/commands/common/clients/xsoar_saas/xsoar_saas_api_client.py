from typing import Optional
from urllib.parse import urljoin

import requests
from demisto_client.demisto_api.api.default_api import DefaultApi
from packaging.version import Version
from requests import Response, Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.configs import XsoarClientConfig
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import (
    ServerType,
    XsoarClient,
)
from demisto_sdk.commands.common.constants import (
    MINIMUM_XSOAR_SAAS_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry


class XsoarSaasClient(XsoarClient):
    """
    api client for xsoar-saas
    """

    def __init__(
        self,
        config: XsoarClientConfig,
        client: Optional[DefaultApi] = None,
        raise_if_server_not_healthy: bool = True,
        should_validate_server_type: bool = False,
    ):
        self._xdr_client = Session()
        self._xdr_client.verify = config.verify_ssl
        self._xdr_client.headers.update(
            {
                "x-xdr-auth-id": config.auth_id,
                "Authorization": config.api_key.get_secret_value(),
                "Content-Type": "application/json",
            }
        )
        self.project_id = config.project_id
        super().__init__(
            config,
            client=client,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
            should_validate_server_type=should_validate_server_type,
        )

    @property
    def is_server_type(self) -> bool:
        about = self.about
        is_xsoar_saas = (
            about.product_mode == "xsoar" and about.deployment_mode == "saas"
        ) or bool(
            (self.version and self.version >= Version(MINIMUM_XSOAR_SAAS_VERSION))
        )
        if not is_xsoar_saas:
            logger.debug(f"{self} is not {self.server_type} server")
            return False
        return True

    @property
    def server_type(self) -> ServerType:
        return ServerType.XSOAR_SAAS

    @property
    def is_healthy(self) -> bool:
        """
        Validates that xdr server part is healthy

        Returns:
            bool: True if xdr server part is healthy, False if not.
        """
        if not super().is_healthy:
            return False
        url = urljoin(self.server_config.base_api_url, "public_api/v1/healthcheck")
        response = self._xdr_client.get(url)
        response.raise_for_status()
        try:
            server_health_status = (response.json().get("status") or "").lower()
            logger.debug(
                f"The status of {self.server_config} health is {server_health_status}"
            )
            is_xdr_healthy = (
                response.status_code == requests.codes.ok
                and server_health_status == "available"
            )
            if not is_xdr_healthy:
                logger.error(
                    f"The XDR server part of {self.server_config} is not healthy"
                )
                return False
            return True

        except JSONDecodeError as e:
            logger.debug(
                f"Could not validate if {self.server_config} is healthy, error:\n{e}"
            )
            return False

    @property
    def marketplace(self) -> MarketplaceVersions:
        return MarketplaceVersions.XSOAR_SAAS

    @property
    def external_base_url(self) -> str:
        return self.xsoar_host_url.replace("api", "ext")

    @retry(exceptions=RequestException)
    def get_xdr_tenant_info(self) -> Response:
        """
        Returns tenant info on SaaS based xsoar/xsiam.
        """
        url = urljoin(
            self.server_config.base_api_url, "public_api/v1/system/get_tenant_info"
        )
        response = self._xdr_client.post(url)
        response.raise_for_status()
        return response

    def get_incident_work_plan_url(self, incident_id: str) -> str:
        """
        Returns the URL link to the work-plan of an incident

        Args:
            incident_id: incident ID
        """
        return f"{self.base_url}/WorkPlan/{incident_id}"

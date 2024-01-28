from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from packaging.version import Version
from pydantic import Field, validator
from requests import Response, Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.configs import XsoarSaasClientConfig
from demisto_sdk.commands.common.clients.errors import UnHealthyServer
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
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

    session: Session = Field(None, exclude=True)
    marketplace = MarketplaceVersions.XSOAR_SAAS

    @classmethod
    def is_xsoar_saas(
        cls,
        server_version: str,
        product_mode: Optional[str] = None,
        deployment_mode: Optional[str] = None,
    ):
        return (product_mode == "xsoar" and deployment_mode == "saas") or (
            server_version
            and Version(server_version) >= Version(MINIMUM_XSOAR_SAAS_VERSION)
        )

    @classmethod
    @retry(exceptions=RequestException)
    def is_xdr_healthy(
        cls, session: Session, server_config: XsoarSaasClientConfig
    ) -> bool:
        """
        Validates that XDR is healthy.

        Returns:
            bool: True if SaaS server is healthy, False if not.
        """
        url = urljoin(server_config.base_api_url, "public_api/v1/healthcheck")
        response = session.get(url)
        response.raise_for_status()
        try:
            server_health_status = (response.json().get("status") or "").lower()
            logger.debug(
                f"The status of {server_config} health is {server_health_status}"
            )
            return (
                response.status_code == requests.codes.ok
                and server_health_status == "available"
            )
        except JSONDecodeError as e:
            logger.debug(
                f"Could not validate if {server_config} is healthy, error:\n{e}"
            )
            return False

    @validator("session", always=True)
    def get_xdr_session(cls, v: Optional[Session], values: Dict[str, Any]) -> Session:
        if v:
            return v
        config = values["config"]
        session = Session()
        session.verify = config.verify_ssl
        session.headers.update(
            {
                "x-xdr-auth-id": config.auth_id,
                "Authorization": config.api_key.get_secret_value(),
                "Content-Type": "application/json",
            }
        )
        if cls.is_xdr_healthy(session, server_config=config):
            return session
        raise UnHealthyServer(str(config), server_part="xdr")

    @property
    def external_base_url(self) -> str:
        return self.xsoar_host_url.replace("api", "ext")

    @retry(exceptions=RequestException)
    def get_tenant_info(self) -> Response:
        """
        Returns tenant info on SaaS based xsoar/xsiam.
        """
        url = urljoin(self.config.base_api_url, "public_api/v1/system/get_tenant_info")
        response = self.session.post(url)
        response.raise_for_status()
        return response

    def get_incident_work_plan_url(self, incident_id: str) -> str:
        """
        Returns the URL link to the work-plan of an incident

        Args:
            incident_id: incident ID
        """
        return f"{self.base_url}/WorkPlan/{incident_id}"

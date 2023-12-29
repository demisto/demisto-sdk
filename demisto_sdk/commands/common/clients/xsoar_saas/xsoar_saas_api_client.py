from typing import Any, Dict, Optional
from urllib.parse import urljoin

from packaging.version import Version
from pydantic import Field, validator
from requests import Response, Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.configs import (
    XsoarClientConfig,
    XsoarSaasClientConfig,
)
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
from demisto_sdk.commands.common.constants import (
    MINIMUM_XSOAR_SAAS_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import retry


class XsoarSaasClient(XsoarClient):
    session: Session = Field(None, exclude=True)
    marketplace = MarketplaceVersions.XSOAR_SAAS

    @classmethod
    def from_server_type(
        cls, client_config: Optional[XsoarClientConfig] = None
    ) -> "XsoarClient":
        """
        Returns whether the configured client is xsoar-saas.
        """
        return super().from_server_type(client_config or XsoarSaasClientConfig())

    @classmethod
    def is_server_type(cls, xsoar_info: Dict):
        product_mode = xsoar_info.get("productMode")
        deployment_mode = xsoar_info.get("deploymentMode")
        server_version = xsoar_info.get("serverVersion")
        return (product_mode == "xsoar" and deployment_mode == "saas") or (
            server_version
            and Version(server_version) >= Version(MINIMUM_XSOAR_SAAS_VERSION)
        )

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
        return session

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

from typing import Any, Dict, Optional
from urllib.parse import urljoin

from pydantic import Field, validator
from requests import Response, Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import retry


class XsoarSaasClient(XsoarClient):
    session: Session = Field(None, exclude=True)
    marketplace = MarketplaceVersions.XSOAR_SAAS

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
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

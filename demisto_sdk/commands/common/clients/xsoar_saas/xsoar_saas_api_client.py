from typing import Any, Dict, Optional
from urllib.parse import urljoin

from demisto_client.demisto_api import DefaultApi
from pydantic import Field, validator
from requests import Response, Session
from requests.exceptions import RequestException

from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import retry


class XsoarSaasClient(XsoarClient):
    session: Session = Field(None, exclude=True)
    marketplace = MarketplaceVersions.XSOAR_SAAS

    @validator("session", always=True)
    def get_xdr_session(cls, v: Optional[Session], values: Dict[str, Any]) -> Session:
        if v:
            return v
        config = values["config"]
        client: DefaultApi = values["client"]
        session = Session()
        session.verify = client.api_client.configuration.verify_ssl
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
        url = urljoin(self.config.base_api_url, "public_api/v1/system/get_tenant_info")
        response = self.session.post(url)
        response.raise_for_status()
        return response

from typing import Any, Dict, List, Union

from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients.xsiam.xsiam_api_client import XsiamClient
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import ServerType
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger


class PlatformClient(XsiamClient):
    """
    api client for platform — covers both XSIAM and XSOAR SaaS tenants.

    PlatformClient extends XsiamClient and relaxes the server-type check so that
    it accepts *any* SaaS-based tenant (xsiam **or** xsoar-saas product mode).
    Use this client when you need to interact with a tenant that may be running
    either product mode and you do not want to hard-code a specific flavour.

    Methods that are XSIAM-only in XsiamClient (poll_incident_state,
    delete_incidents) are restored here so that XSOAR SaaS tenants can use them.
    """

    @property
    def is_server_type(self) -> bool:
        """
        Returns True for any SaaS-based tenant (xsiam or xsoar-saas deployment).

        Falls back to the IOC-rules probe (same as XsiamClient) for older XSIAM
        tenants that do not report productMode / deploymentMode in /about.
        """
        about = self.about
        product_mode = about.product_mode
        deployment_mode = about.deployment_mode

        # Fast path: modern tenants report product/deployment mode explicitly.
        if product_mode in ("xsiam", "xsoar") and deployment_mode in ("saas", "xsiam"):
            return True

        # Fallback: older XSIAM tenants may not report productMode.
        # Try the /ioc-rules endpoint which is XSIAM-exclusive.
        try:
            self.get_ioc_rules()
            return True
        except ApiException:
            pass

        logger.debug(f"{self} is not a {self.server_type} server")
        return False

    @property
    def server_type(self) -> ServerType:
        return ServerType.PLATFORM

    @property
    def marketplace(self) -> MarketplaceVersions:
        return MarketplaceVersions.PLATFORM

    # ------------------------------------------------------------------
    # Methods overridden from XsiamClient to restore XsoarClient behaviour
    # for XSOAR SaaS tenants connected via PlatformClient.
    # ------------------------------------------------------------------

    def poll_incident_state(self, *args, **kwargs):
        """
        Polls for the state of an XSOAR incident.

        Overrides XsiamClient which raises NotImplementedError.
        On a PlatformClient the tenant may be XSOAR SaaS, so incident polling
        must remain available.  Delegates directly to XsoarClient.poll_incident_state.
        """
        from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import (
            XsoarClient,
        )

        return XsoarClient.poll_incident_state(self, *args, **kwargs)

    def delete_incidents(
        self,
        incident_ids: Union[str, List[str]],
        filters: Dict[str, Any] = None,
        _all: bool = False,
        response_type: str = "object",
    ):
        """
        Deletes incidents on the connected tenant.

        Overrides XsiamClient which raises NotImplementedError (XSIAM does not
        support incident deletion).  On a PlatformClient the tenant may be XSOAR
        SaaS where deletion is valid, so we delegate to XsoarClient.delete_incidents.
        """
        from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import (
            XsoarClient,
        )

        return XsoarClient.delete_incidents(
            self, incident_ids, filters=filters, _all=_all, response_type=response_type
        )

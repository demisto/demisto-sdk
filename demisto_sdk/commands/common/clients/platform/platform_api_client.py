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
    """

    @property
    def is_server_type(self) -> bool:
        """
        Returns True for any SaaS-based tenant (xsiam or xsoar-saas deployment).
        """
        about = self.about
        product_mode = about.product_mode
        deployment_mode = about.deployment_mode

        is_platform = product_mode in ("xsiam", "xsoar") and deployment_mode in (
            "saas",
            "xsiam",
        )
        if not is_platform:
            logger.debug(f"{self} is not a {self.server_type} server")
        return is_platform

    @property
    def server_type(self) -> ServerType:
        return ServerType.PLATFORM

    @property
    def marketplace(self) -> MarketplaceVersions:
        return MarketplaceVersions.PLATFORM

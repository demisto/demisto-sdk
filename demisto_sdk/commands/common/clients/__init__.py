import os
from functools import lru_cache
from typing import Optional

import demisto_client
import requests
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version

from demisto_sdk.commands.common.clients.configs import (
    XsiamClientConfig,
    XsoarClientConfig,
    XsoarSaasClientConfig,
)
from demisto_sdk.commands.common.clients.xsiam.xsiam_api_client import XsiamClient
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import XsoarClient
from demisto_sdk.commands.common.clients.xsoar_saas.xsoar_saas_api_client import (
    XsoarSaasClient,
)
from demisto_sdk.commands.common.constants import (
    AUTH_ID,
    DEMISTO_BASE_URL,
    DEMISTO_KEY,
    MINIMUM_XSOAR_SAAS_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger


@lru_cache
def get_client_from_config(
    client_config: XsoarClientConfig, verify_ssl: bool = False
) -> XsoarClient:
    """
    Returns the correct Client (xsoar on prem, xsoar saas or xsiam) based on the clients config object

    Args:
        client_config: clients configuration
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not

    Returns:
        the correct api clients based on the clients config
    """
    base_url = client_config.base_api_url
    api_key = client_config.api_key
    auth_id = client_config.auth_id

    _client = demisto_client.configure(
        base_url=base_url,
        api_key=api_key.get_secret_value(),
        auth_id=auth_id,
        verify_ssl=verify_ssl,
    )

    if isinstance(client_config, XsiamClientConfig):
        return XsiamClient(client=_client, config=client_config)
    elif isinstance(client_config, XsoarSaasClientConfig):
        return XsoarSaasClient(client=_client, config=client_config)
    else:
        return XsoarClient(client=_client, config=client_config)


def get_client_from_marketplace(
    marketplace: MarketplaceVersions,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_id: Optional[str] = None,
    verify_ssl: bool = False,
) -> XsoarClient:
    """
    Returns the client based on the marketplace.

    Args:
        marketplace: the marketplace of the client
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not

    Returns:
        the correct client according to the marketplace provided
    """
    _base_api_url = base_url or os.getenv(DEMISTO_BASE_URL)
    _api_key = api_key or os.getenv(DEMISTO_KEY, "")
    _auth_id = auth_id or os.getenv(AUTH_ID)

    if marketplace in (MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR):
        config = XsoarClientConfig(base_api_url=_base_api_url, api_key=_api_key)
    elif marketplace == MarketplaceVersions.XSOAR_SAAS:
        config = XsoarSaasClientConfig(
            base_api_url=_base_api_url, api_key=_api_key, auth_id=_auth_id
        )
    else:
        config = XsiamClientConfig(
            base_api_url=_base_api_url, api_key=_api_key, auth_id=_auth_id
        )
    return get_client_from_config(config, verify_ssl=verify_ssl)


@lru_cache
def get_client_from_server_type(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_id: Optional[str] = None,
    verify_ssl: bool = False,
) -> XsoarClient:
    """
    Returns the client based on the server type by doing api requests to determine which server it is

    Args:
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not

    Returns:
        the correct client based on querying the type of the server
    """
    _base_api_url = base_url or os.getenv(DEMISTO_BASE_URL)
    _api_key = api_key or os.getenv(DEMISTO_KEY, "")
    _auth_id = auth_id or os.getenv(AUTH_ID)

    _client = demisto_client.configure(
        base_url=_base_api_url,
        api_key=_api_key,
        auth_id=_auth_id,
        verify_ssl=verify_ssl,
    )

    try:
        # /ioc-rules is only an endpoint in XSIAM.
        response, status_code, response_headers = _client.generic_request(
            "/ioc-rules", "GET"
        )
        if "text/html" in response_headers.get("Content-Type"):
            raise ApiException(
                status=400,
                reason=f"endpoint /ioc-rules does not exist in {_client.api_client.configuration.host}",
            )
        if status_code != requests.codes.ok:
            raise ApiException(status=status_code, reason=response)

        return XsiamClient(
            client=_client,
            config=XsiamClientConfig(
                base_api_url=_base_api_url, api_key=_api_key, auth_id=_auth_id
            ),
        )
    except ApiException as e:
        logger.debug(f"got exception when querying /ioc-rules: {e}")
        about_raw_response = XsoarClient.get_xsoar_about(_client)
        if server_version := about_raw_response.get("demistoVersion"):
            if Version(server_version) >= Version(MINIMUM_XSOAR_SAAS_VERSION):
                return XsoarSaasClient(
                    client=_client,
                    about_xsoar=about_raw_response,
                    config=XsoarSaasClientConfig(
                        base_api_url=_base_api_url, api_key=_api_key, auth_id=_auth_id
                    ),
                )
            return XsoarClient(
                client=_client,
                about_xsoar=about_raw_response,
                config=XsoarClientConfig(base_api_url=_base_api_url, api_key=_api_key),
            )
        raise RuntimeError("Could not determine the correct api client")

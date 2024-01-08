import os
from functools import lru_cache
from typing import Optional

import demisto_client
import pydantic

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
    DEMISTO_PASSWORD,
    DEMISTO_USERNAME,
    DEMISTO_VERIFY_SSL,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import string_to_bool


@lru_cache
def get_client_from_config(client_config: XsoarClientConfig) -> XsoarClient:
    """
    Returns the correct Client (xsoar on prem, xsoar saas or xsiam) based on the clients config object

    Args:
        client_config: clients configuration

    Returns:
        the correct api clients based on the clients config
    """
    if isinstance(client_config, XsiamClientConfig):
        return XsiamClient(config=client_config)
    elif isinstance(client_config, XsoarSaasClientConfig):
        return XsoarSaasClient(config=client_config)
    else:
        return XsoarClient(config=client_config)


def get_client_from_marketplace(
    marketplace: MarketplaceVersions,
    base_url: Optional[str] = os.getenv(DEMISTO_BASE_URL, ""),
    api_key: Optional[str] = os.getenv(DEMISTO_KEY, ""),
    auth_id: Optional[str] = os.getenv(AUTH_ID, ""),
    verify_ssl: bool = string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False)),
) -> XsoarClient:
    """
    Returns the client based on the marketplace.

    Args:
        marketplace: the marketplace of the client
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not
                    if verify_ssl = None, will take the SSL verification from DEMISTO_VERIFY_SSL env var

    Returns:
        the correct client according to the marketplace provided
    """
    if marketplace in (MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR):
        config = XsoarClientConfig(
            base_api_url=base_url, api_key=api_key, verify_ssl=verify_ssl
        )
    elif marketplace == MarketplaceVersions.XSOAR_SAAS:
        config = XsoarSaasClientConfig(
            base_api_url=base_url,
            api_key=api_key,
            auth_id=auth_id,
            verify_ssl=verify_ssl,
        )
    else:
        config = XsiamClientConfig(
            base_api_url=base_url,
            api_key=api_key,
            auth_id=auth_id,
            verify_ssl=verify_ssl,
        )
    return get_client_from_config(config)


@lru_cache
def get_client_from_server_type(
    base_url: Optional[str] = os.getenv(DEMISTO_BASE_URL, ""),
    api_key: Optional[str] = os.getenv(DEMISTO_KEY, ""),
    auth_id: Optional[str] = os.getenv(AUTH_ID, ""),
    username: Optional[str] = os.getenv(DEMISTO_USERNAME, ""),
    password: Optional[str] = os.getenv(DEMISTO_PASSWORD, ""),
    verify_ssl: bool = string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False)),
) -> XsoarClient:
    """
    Returns the client based on the server type by doing api requests to determine which server it is

    Args:
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        username: the username to authenticate, relevant only for xsoar on prem
        password: the password to authenticate, relevant only for xsoar on prem
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not,
                    if verify_ssl = None, will take the SSL verification from DEMISTO_VERIFY_SSL env var

    Returns:
        the correct client based on querying the type of the server
    """
    _client = demisto_client.configure(
        base_url=base_url,
        api_key=api_key,
        verify_ssl=verify_ssl,
        username=username,
        password=password,
    )

    about = XsoarClient.get_xsoar_about(_client)
    product_mode = about.get("productMode")
    deployment_mode = about.get("deploymentMode")
    server_version = about.get("demistoVersion")

    if XsiamClient.is_xsiam(_client, product_mode=product_mode):
        return XsiamClient(
            config=XsiamClientConfig(
                base_api_url=base_url,
                api_key=api_key,
                auth_id=auth_id,
                verify_ssl=verify_ssl,
                about=about,
            ),
            client=_client,
            about_xsoar=about,
        )

    if XsoarSaasClient.is_xsoar_saas(
        server_version, product_mode=product_mode, deployment_mode=deployment_mode
    ):
        try:
            return XsoarSaasClient(
                config=XsoarSaasClientConfig(
                    base_api_url=base_url,
                    api_key=api_key,
                    auth_id=auth_id,
                    verify_ssl=verify_ssl,
                ),
                client=_client,
                about=about,
            )
        except pydantic.ValidationError:
            # xsoar-on-prem that can have server version > 8.0.0
            return XsoarClient(
                config=XsoarClientConfig(
                    base_api_url=base_url,
                    api_key=api_key,
                    auth_id=auth_id,
                    user=username,
                    password=password,
                    verify_ssl=verify_ssl,
                ),
                client=_client,
                about=about,
            )

    if XsoarClient.is_xsoar_on_prem(
        server_version, product_mode=product_mode, deployment_mode=deployment_mode
    ):
        return XsoarClient(
            config=XsoarClientConfig(
                base_api_url=base_url,
                api_key=api_key,
                auth_id=auth_id,
                user=username,
                password=password,
                verify_ssl=verify_ssl,
            ),
            client=_client,
            about=about,
        )

    raise RuntimeError(f"Could not determine the correct api-client for {base_url}")

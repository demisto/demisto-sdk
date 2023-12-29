import os
from functools import lru_cache
from typing import Optional

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
    DEMISTO_VERIFY_SSL,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
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
    verify_ssl: bool = string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False)),
) -> XsoarClient:
    """
    Returns the client based on the server type by doing api requests to determine which server it is

    Args:
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not,
                    if verify_ssl = None, will take the SSL verification from DEMISTO_VERIFY_SSL env var

    Returns:
        the correct client based on querying the type of the server
    """
    try:
        return XsiamClient.from_server_type(
            XsiamClientConfig(
                base_api_url=base_url,
                api_key=api_key,
                auth_id=auth_id,
                verify_ssl=verify_ssl,
            )
        )
    except ValueError as error:
        logger.debug(f"{error=}")
        try:
            return XsoarSaasClient.from_server_type(
                XsoarSaasClientConfig(
                    base_api_url=base_url,
                    api_key=api_key,
                    auth_id=auth_id,
                    verify_ssl=verify_ssl,
                )
            )
        except pydantic.ValidationError:
            return XsoarClient(
                config=XsoarClientConfig(
                    base_api_url=base_url, api_key=api_key, verify_ssl=verify_ssl
                )
            )
        except ValueError as error:
            logger.debug(f"{error=}")
            try:
                return XsoarClient.from_server_type(
                    XsoarClientConfig(
                        base_api_url=base_url, api_key=api_key, verify_ssl=verify_ssl
                    )
                )
            except ValueError as error:
                logger.debug(f"{error=}")
                raise RuntimeError(
                    f"Could not determine the correct api-client for {base_url}"
                )

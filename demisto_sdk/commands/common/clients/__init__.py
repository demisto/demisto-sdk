import os
from functools import lru_cache
from typing import Optional

from _pytest.fixtures import SubRequest
from urllib3.exceptions import MaxRetryError

from demisto_sdk.commands.common.clients.configs import (
    XsiamClientConfig,
    XsoarClientConfig,
    XsoarSaasClientConfig,
)
from demisto_sdk.commands.common.clients.errors import (
    InvalidServerType,
)
from demisto_sdk.commands.common.clients.xsiam.xsiam_api_client import XsiamClient
from demisto_sdk.commands.common.clients.xsoar.xsoar_api_client import (
    ServerType,
    XsoarClient,
)
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
    PROJECT_ID,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import string_to_bool


@lru_cache
def get_client_from_config(
    client_config: XsoarClientConfig, raise_if_server_not_healthy: bool = True
) -> XsoarClient:
    """
    Returns the correct Client (xsoar on prem, xsoar saas or xsiam) based on the clients config object

    Args:
        client_config: clients configuration
        raise_if_server_not_healthy: whether to raise an exception if the server is not healthy

    Returns:
        the correct api clients based on the clients config
    """
    if isinstance(client_config, XsiamClientConfig):
        return XsiamClient(
            client_config,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )
    elif isinstance(client_config, XsoarSaasClientConfig):
        return XsoarSaasClient(
            client_config,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )
    else:
        return XsoarClient(
            client_config,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )


def get_client_from_marketplace(
    marketplace: MarketplaceVersions,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    verify_ssl: Optional[bool] = None,
    raise_if_server_not_healthy: bool = True,
) -> XsoarClient:
    """
    Returns the client based on the marketplace.

    Args:
        marketplace: the marketplace of the client
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        username: the username to authenticate, relevant only for xsoar on prem
        password: the password to authenticate, relevant only for xsoar on prem
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not
                    if verify_ssl = None, will take the SSL verification from DEMISTO_VERIFY_SSL env var
        raise_if_server_not_healthy: whether to raise an exception if the server is not healthy

    Returns:
        the correct client according to the marketplace provided
    """
    _base_url = base_url or os.getenv(DEMISTO_BASE_URL, "")
    _api_key = api_key or os.getenv(DEMISTO_KEY, "")
    _auth_id = auth_id or os.getenv(AUTH_ID)
    _username = username or os.getenv(DEMISTO_USERNAME, "")
    _password = password or os.getenv(DEMISTO_PASSWORD, "")
    _verify_ssl = (
        verify_ssl
        if verify_ssl is not None
        else string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False))
    )

    if marketplace in (MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR):
        config = XsoarClientConfig(
            base_api_url=_base_url, api_key=_api_key, verify_ssl=_verify_ssl
        )
    elif marketplace == MarketplaceVersions.XSOAR_SAAS:
        config = XsoarSaasClientConfig(
            base_api_url=_base_url,
            api_key=_api_key,
            auth_id=_auth_id,
            verify_ssl=_verify_ssl,
        )
    else:
        config = XsiamClientConfig(
            base_api_url=_base_url,
            api_key=_api_key,
            auth_id=_auth_id,
            verify_ssl=_verify_ssl,
        )
    return get_client_from_config(
        config, raise_if_server_not_healthy=raise_if_server_not_healthy
    )


@lru_cache
def get_client_from_server_type(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    project_id: Optional[str] = None,
    verify_ssl: Optional[bool] = None,
    raise_if_server_not_healthy: bool = True,
) -> XsoarClient:
    """
    Returns the client based on the server type by doing api requests to determine which server it is

    Args:
        base_url: the base URL, if not provided will take from DEMISTO_BASE_URL env var
        api_key: the api key, if not provided will take from DEMISTO_API_KEY env var
        auth_id: the auth ID, if not provided will take from XSIAM_AUTH_ID env var
        username: the username to authenticate, relevant only for xsoar on prem
        password: the password to authenticate, relevant only for xsoar on prem
        project_id: the project id of the current cloud machine.
        verify_ssl: whether in each request SSL should be verified, True if yes, False if not,
                    if verify_ssl = None, will take the SSL verification from DEMISTO_VERIFY_SSL env var
        raise_if_server_not_healthy: whether to raise an exception if the server is not healthy

    Returns:
        the correct client based on querying the type of the server
    """
    _base_url = base_url or os.getenv(DEMISTO_BASE_URL, "")
    _api_key = api_key or os.getenv(DEMISTO_KEY, "")
    _auth_id = auth_id or os.getenv(AUTH_ID)
    _username = username or os.getenv(DEMISTO_USERNAME, "")
    _password = password or os.getenv(DEMISTO_PASSWORD, "")
    _project_id = project_id or os.getenv(PROJECT_ID, "")
    _verify_ssl = (
        verify_ssl
        if verify_ssl is not None
        else string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False))
    )

    if not _auth_id and (_api_key or (_username and _password)):
        # if no auth-id is provided, it must be xsoar-on-prem
        logger.debug(
            f"Assuming {_base_url} is {ServerType.XSOAR} server as {AUTH_ID} is not defined"
        )
        return XsoarClient(
            config=XsoarClientConfig(
                base_api_url=_base_url,
                api_key=_api_key,
                user=_username,
                password=_password,
                verify_ssl=_verify_ssl,
            ),
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )

    should_validate_server_type = True
    logger.debug(f"Checking if {_base_url} is {ServerType.XSIAM}")

    try:
        return XsiamClient(
            config=XsiamClientConfig(
                base_api_url=_base_url,
                api_key=_api_key,
                auth_id=_auth_id,
                verify_ssl=_verify_ssl,
                project_id=_project_id,
            ),
            should_validate_server_type=should_validate_server_type,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )
    except (InvalidServerType, MaxRetryError):
        logger.debug(f"Checking if {_base_url} is {ServerType.XSOAR_SAAS}")

    try:
        return XsoarSaasClient(
            config=XsoarSaasClientConfig(
                base_api_url=_base_url,
                api_key=_api_key,
                auth_id=_auth_id,
                verify_ssl=_verify_ssl,
                project_id=_project_id,
            ),
            should_validate_server_type=should_validate_server_type,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )
    except (InvalidServerType, MaxRetryError):
        logger.debug(f"Checking if {_base_url} is {ServerType.XSOAR}")

    try:
        # if xsiam-auth-id is defined by mistake
        os.environ.pop(AUTH_ID, None)
        return XsoarClient(
            config=XsoarClientConfig(
                base_api_url=_base_url,
                api_key=_api_key,
                user=_username,
                password=_password,
                verify_ssl=_verify_ssl,
            ),
            should_validate_server_type=should_validate_server_type,
            raise_if_server_not_healthy=raise_if_server_not_healthy,
        )
    except Exception as error:
        logger.debug(
            f"The {_base_url} is not {ServerType.XSOAR} server, error: {error}"
        )
        logger.error(
            f"Could not determine the correct api-client for {_base_url}, "
            f"make sure the {DEMISTO_BASE_URL}, {DEMISTO_KEY}, {AUTH_ID} are defined properly"
        )
        raise


# =================== Playbook Flow Tests =================


def parse_str_to_dict(input_str: str):
    """Internal function to convert a string representing a dictionary into an actual dictionary.

    Args:
        input_str (str): A string in the format 'key1=value1,key2=value2'.

    Returns:
        dict: A dictionary with the parsed key-value pairs.
    """
    x = dict(pair.split("=") for pair in input_str.split(",") if "=" in pair)
    logger.info(x.get("base_url", "no base url"))
    return dict(pair.split("=") for pair in input_str.split(",") if "=" in pair)


def get_client_conf_from_pytest_request(request: SubRequest):
    # Manually parse command-line argument
    for arg in request.config.invocation_params.args:
        if isinstance(arg, str) and arg.startswith("--client_conf="):
            logger.debug("Parsing --client_conf argument")
            client_conf = arg.replace("--client_conf=", "")
            return parse_str_to_dict(client_conf)
    # If a client data was not provided, we proceed to use default.
    return None

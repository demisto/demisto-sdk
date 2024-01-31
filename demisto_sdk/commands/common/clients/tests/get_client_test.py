from typing import Type

import pytest
from demisto_client.demisto_api import DefaultApi
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients import (
    XsiamClient,
    XsiamClientConfig,
    XsoarClient,
    XsoarClientConfig,
    XsoarSaasClient,
    XsoarSaasClientConfig,
)
from demisto_sdk.commands.common.clients.errors import UnAuthorized, UnHealthyServer
from demisto_sdk.commands.common.constants import MarketplaceVersions


@pytest.fixture()
def base_mocker(mocker):
    mocker.patch.object(XsoarClient, "about", return_value={})
    mocker.patch.object(XsoarClient, "is_healthy", return_value=True)
    mocker.patch.object(XsoarSaasClient, "is_healthy", return_value=True)
    return mocker


@pytest.mark.parametrize(
    "config, expected_client_type",
    [
        (
            XsoarClientConfig(base_api_url="https://test.com", api_key="test"),
            XsoarClient,
        ),
        (
            XsoarSaasClientConfig(
                base_api_url="https://test.com", api_key="test", auth_id="1"
            ),
            XsoarSaasClient,
        ),
        (
            XsiamClientConfig(
                base_api_url="https://test.com", api_key="test", auth_id="2"
            ),
            XsiamClient,
        ),
    ],
)
def test_get_client_from_config(
    mocker,
    requests_mock,
    config: XsoarClientConfig,
    expected_client_type: Type[XsoarClient],
):
    """
    Given:
     - Case A: a predefined XsoarClientConfig
     - Case B: a predefined XsoarSaasClientConfig
     - Case C: a predefined XsiamClientConfig

    When:
     - running get_client_from_config function

    Then:
     - Case A: make sure Xsoarclient is returned
     - Case B: make sure XsoarSaasClient is returned
     - Case C: make sure XsiamClient is returned
    """
    from demisto_sdk.commands.common.clients import get_client_from_config

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = ""
    ):
        if path == "/about" and method == "GET":
            return {}, 200, {"Content-Type": "application/json"}
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    requests_mock.get(
        f"{config.base_api_url}/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )

    assert type(get_client_from_config(config)) == expected_client_type


@pytest.mark.parametrize(
    "base_api_url, marketplace, expected_client_type",
    [
        ("https://test1.com", MarketplaceVersions.XSOAR, XsoarClient),
        ("https://test2.com", MarketplaceVersions.XSOAR_ON_PREM, XsoarClient),
        ("https://test3.com", MarketplaceVersions.XSOAR_SAAS, XsoarSaasClient),
        ("https://test4.com", MarketplaceVersions.MarketplaceV2, XsiamClient),
    ],
)
def test_get_client_from_marketplace(
    mocker,
    requests_mock,
    base_api_url: str,
    marketplace: MarketplaceVersions,
    expected_client_type: Type[XsoarClient],
):
    """
    Given:
     - Case A + B: a predefined MarketplaceVersions.XSOAR_ON_PREM or MarketplaceVersions.XSOAR
     - Case C: a predefined MarketplaceVersions.XSOAR_SAAS
     - Case D: a predefined MarketplaceVersions.MarketplaceV2

    When:
     - running get_client_from_marketplace function

    Then:
     - Case A + B: make sure XsoarOnPremClient is returned
     - Case C: make sure XsoarSaasClient is returned
     - Case D: make sure XsiamClient is returned
    """
    from demisto_sdk.commands.common.clients import get_client_from_marketplace

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = ""
    ):
        if path == "/about" and method == "GET":
            return {}, 200, {"Content-Type": "application/json"}
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    requests_mock.get(
        f"{base_api_url}/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )

    assert (
        type(
            get_client_from_marketplace(
                marketplace, base_url=base_api_url, api_key="test", auth_id="1"
            )
        )
        == expected_client_type
    )


@pytest.mark.parametrize(
    "base_api_url, xsoar_version, expected_client_type",
    [
        ("https://test.com", "6.11.0", XsoarClient),
        ("https://test2.com", "8.4.0", XsoarSaasClient),
    ],
)
def test_get_xsoar_client_from_server_type_no_product_deployment_mode(
    mocker,
    requests_mock,
    base_api_url: str,
    xsoar_version: str,
    expected_client_type: Type[XsoarClient],
):
    """
    Given:
     - Case A: xsoar 6 version
     - Case B: xsoar 8 version
     - no product / deployment modes

    When:
     - running get_client_from_server_type function

    Then:
     - Case A: make sure XsoarOnPremClient is returned
     - Case B: make sure XsoarSaasClient is returned
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = ""
    ):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        elif path == "/about" and method == "GET":
            return (
                {"demistoVersion": xsoar_version},
                200,
                {"Content-Type": "application/json"},
            )
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )
    requests_mock.get(
        f"{base_api_url}/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    assert (
        type(
            get_client_from_server_type(
                base_url=base_api_url, api_key="test", auth_id="1"
            )
        )
        == expected_client_type
    )


def test_get_xsiam_client_from_server_type_no_product_deployment_mode(
    mocker, requests_mock
):
    """
    Given:
     - /ioc-rules endpoint that is valid
     - no product / deployment modes

    When:
     - running get_client_from_server_type function

    Then:
     - make sure XsiamClient is returned
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_request_side_effect(path: str, method: str, response_type: str = ""):
        if path == "/ioc-rules" and method == "GET":
            return None, 200, {"Content-Type": "application/json"}
        elif path == "/about" and method == "GET":
            return {}, 200, {"Content-Type": "application/json"}
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_request_side_effect
    )
    requests_mock.get(
        "https://test3.com/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    assert (
        type(
            get_client_from_server_type(
                base_url="https://test3.com", api_key="test", auth_id="1"
            )
        )
        == XsiamClient
    )


def test_get_client_from_server_type_unauthorized_exception(mocker):
    """
    Given:
     - unauthorized exception when querying /about

    When:
     - running get_client_from_server_type function

    Then:
     - make sure UnAuthorized exception is raised
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = ""
    ):
        if path == "/health/server" and method == "GET":
            raise ApiException(status=401, reason="error")

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )
    with pytest.raises(UnAuthorized):
        get_client_from_server_type(
            base_url="https://test4.com", api_key="test", auth_id="1"
        )


def test_get_client_from_server_type_base_url_is_not_api_url(mocker):
    """
    Given:
     - /ioc-rules endpoint that is not valid
     - /about that returns content-type of text/html

    When:
     - running get_client_from_server_type function

    Then:
     - make sure ValueError exception is raised
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/health/server":
            return "", 200, ""
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        if path == "/about" and method == "GET" and response_type == "object":
            return {}, 200, {"Content-Type": "text/html"}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )

    with pytest.raises(ValueError):
        get_client_from_server_type(
            base_url="https://test5.com", api_key="test", auth_id="1"
        )


@pytest.mark.parametrize(
    "base_api_url, product_deployment_modes, expected_client_type",
    [
        (
            "https://test6.com",
            {"productMode": "xsiam", "demistoVersion": "8.6.0"},
            XsiamClient,
        ),
        (
            "https://test7.com",
            {
                "productMode": "xsoar",
                "deploymentMode": "saas",
                "demistoVersion": "8.6.0",
            },
            XsoarSaasClient,
        ),
        (
            "https://test8.com",
            {
                "productMode": "xsoar",
                "deploymentMode": "opp",
                "demistoVersion": "6.13.0",
            },
            XsoarClient,
        ),
    ],
)
def test_get_client_from_server_type_with_product_deployment_mode(
    mocker,
    requests_mock,
    base_api_url: str,
    product_deployment_modes: dict,
    expected_client_type: Type[XsoarClient],
):
    """
    Given:
     - Case A: productMode=xsiam
     - Case B: productMode=xsoar, deploymentMode=saas
     - Case C: productMode=xsoar, deploymentMode=opp

    When:
     - running get_client_from_server_type function

    Then:
     - Case A: XsiamClient is returned
     - Case B: XsoarSaasClient is returned
     - Case C: XsoarClient is returned
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_request_side_effect(path: str, method: str, response_type: str = ""):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        elif path == "/about" and method == "GET":
            return product_deployment_modes, 200, {"Content-Type": "application/json"}
        elif path == "/health/server" and method == "GET":
            return "", 200, {}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_request_side_effect
    )
    requests_mock.get(
        f"{base_api_url}/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    assert (
        type(
            get_client_from_server_type(
                base_url=base_api_url, api_key="test", auth_id="1"
            )
        )
        == expected_client_type
    )


def test_get_client_from_server_type_no_product_deployment_mode_xsoar_on_prem_with_from_version_larger_than_8(
    mocker, requests_mock
):
    """
    Given:
     - xsoar-on-prem that has from version of 8
     - no auth id

    When:
     - running get_client_from_server_type function

    Then:
     - make sure XsoarClient is returned even when from version is > 8
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/health/server":
            return "", 200, ""
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        if path == "/about" and method == "GET" and response_type == "object":
            return (
                {"demistoVersion": "8.0.0"},
                200,
                {"Content-Type": "application/json"},
            )

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )
    requests_mock.get(
        "https://test9.com/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    assert (
        type(get_client_from_server_type(base_url="https://test9.com", api_key="test"))
        == XsoarClient
    )


def test_get_client_from_server_type_unhealthy_xsoar_server(mocker, requests_mock):
    """
    Given:
     - server which its xsoar part is not healthy

    When:
     - running get_client_from_server_type function

    Then:
     - make sure the UnHealthyServer is raised
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/health/server":
            return "", 434, ""
        if path == "/about":
            raise ApiException(status=500, reason="error")

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )
    mocker.patch("demisto_sdk.commands.common.tools.time.sleep")

    with pytest.raises(UnHealthyServer):
        get_client_from_server_type(
            base_url="https://test10.com", api_key="test", auth_id="1"
        )


def test_get_client_from_server_type_unhealthy_xdr_server(mocker, requests_mock):
    """
    Given:
     - server which its xdr part is not healthy

    When:
     - running get_client_from_server_type function

    Then:
     - make sure the UnHealthyServer is raised
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/health/server":
            return "", 200, ""
        if path == "/about":
            raise ApiException(status=500, reason="error")

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )
    mocker.patch("demisto_sdk.commands.common.tools.time.sleep")
    requests_mock.get(
        "https://test11.com/public_api/v1/healthcheck",
        json={"status": "not-available"},
        status_code=200,
    )

    with pytest.raises(UnHealthyServer):
        get_client_from_server_type(
            base_url="https://test11.com", api_key="test", auth_id="1"
        )


def test_get_xsoar_on_prem_client_from_server_type_with_auth_id(mocker, requests_mock):
    """
    Given:
     - xsoar 6.13.0 version
     - base url + auth-id + api-key provided

    When:
     - running get_client_from_server_type function

    Then:
     - make sure the XsoarClient is returned even when auth_id is defined (which is not needed)
    """

    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _xsoar_generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/health/server":
            return "", 200, ""
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        if path == "/about" and method == "GET" and response_type == "object":
            return (
                {"demistoVersion": "6.13.0"},
                200,
                {"Content-Type": "application/json"},
            )

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_xsoar_generic_request_side_effect
    )
    requests_mock.get(
        "https://test12.com/public_api/v1/healthcheck",
        json={"status": "available"},
        status_code=200,
    )

    assert (
        type(
            get_client_from_server_type(
                base_url="https://test12.com", api_key="test", auth_id="1"
            )
        )
        == XsoarClient
    )

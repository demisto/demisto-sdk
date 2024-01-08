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
from demisto_sdk.commands.common.clients.errors import UnAuthorized
from demisto_sdk.commands.common.constants import MarketplaceVersions


@pytest.fixture()
def api_requests_mocker(mocker):
    mocker.patch.object(XsoarClient, "get_xsoar_about", return_value={})
    mocker.patch.object(XsiamClient, "is_xsiam_server_healthy", return_value=True)
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
    api_requests_mocker,
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
    api_requests_mocker,
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
    api_requests_mocker,
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

    def _generic_request_side_effect(path: str, method: str):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")

    api_requests_mocker.patch.object(
        XsoarClient, "get_xsoar_about", return_value={"demistoVersion": xsoar_version}
    )
    api_requests_mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
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
    api_requests_mocker,
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

    def _generic_request_side_effect(path: str, method: str):
        if path == "/ioc-rules" and method == "GET":
            return None, 200, {"Content-Type": "application/json"}

    api_requests_mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )
    assert (
        type(
            get_client_from_server_type(
                base_url="https://test3.com", api_key="test", auth_id="1"
            )
        )
        == XsiamClient
    )


def test_get_client_from_server_type_unauthorized_exception(api_requests_mocker):
    """
    Given:
     - /ioc-rules endpoint that is not valid
     - unauthorized exception when querying /about

    When:
     - running get_client_from_server_type function

    Then:
     - make sure UnAuthorized exception is raised
    """
    from demisto_sdk.commands.common.clients import get_client_from_server_type

    def _generic_request_side_effect(path: str, method: str):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")

    api_requests_mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )
    api_requests_mocker.patch.object(
        XsoarClient, "get_xsoar_about", side_effect=UnAuthorized("error")
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

    def _generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        if path == "/about" and method == "GET" and response_type == "object":
            return {}, 200, {"Content-Type": "text/html"}

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )

    with pytest.raises(ValueError):
        get_client_from_server_type(
            base_url="https://test5.com", api_key="test", auth_id="1"
        )


@pytest.mark.parametrize(
    "base_api_url, product_deployment_modes, expected_client_type",
    [
        ("https://test6.com", {"productMode": "xsiam"}, XsiamClient),
        (
            "https://test7.com",
            {"productMode": "xsoar", "deploymentMode": "saas"},
            XsoarSaasClient,
        ),
        (
            "https://test8.com",
            {"productMode": "xsoar", "deploymentMode": "opp"},
            XsoarClient,
        ),
    ],
)
def test_get_client_from_server_type_with_product_deployment_mode(
    api_requests_mocker,
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

    def _generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        raise ApiException(status=500, reason="error")

    api_requests_mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )

    api_requests_mocker.patch.object(
        XsoarClient, "get_xsoar_about", return_value=product_deployment_modes
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
    mocker,
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

    def _generic_request_side_effect(
        path: str, method: str, response_type: str = "object"
    ):
        if path == "/ioc-rules" and method == "GET":
            raise ApiException(status=500, reason="error")
        if path == "/about" and method == "GET" and response_type == "object":
            return (
                {"demistoVersion": "8.0.0"},
                200,
                {"Content-Type": "application/json"},
            )

    mocker.patch.object(
        DefaultApi, "generic_request", side_effect=_generic_request_side_effect
    )

    assert (
        type(get_client_from_server_type(base_url="https://test9.com", api_key="test"))
        == XsoarClient
    )

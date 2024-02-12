import pytest
from pydantic import ValidationError

from demisto_sdk.commands.common.clients import (
    XsiamClientConfig,
    XsoarClientConfig,
    XsoarSaasClientConfig,
)


def test_init_xsoar_client_config_with_api_key():
    assert XsoarClientConfig(base_api_url="https://test1.com", api_key="test")


def test_init_xsoar_client_config_username_password():
    assert XsoarClientConfig(
        base_api_url="https://test1.com", user="test", password="test"
    )


def test_init_xsoar_client_config_no_api_key_and_user_and_password():
    with pytest.raises(ValueError):
        XsoarClientConfig(base_api_url="https://test1.com")


def test_init_xsoar_client_config_no_values():
    with pytest.raises(ValidationError):
        XsoarClientConfig()


def test_init_xsoar_client_config_with_invalid_url_with_api_key():
    with pytest.raises(ValidationError):
        XsoarClientConfig(base_api_url="test", api_key="test")


def test_init_xsoar_saas_client_config_with_api_key_auth_id():
    assert XsoarSaasClientConfig(
        base_api_url="https://test1.com", api_key="test", auth_id="1"
    )


def test_init_xsoar_saas_client_config_with_api_key_without_auth_id():
    with pytest.raises(ValueError):
        XsoarSaasClientConfig(base_api_url="https://test1.com", api_key="test")


def test_init_xsoar_saas_client_config_with_auth_id_without_api_key():
    with pytest.raises(ValueError):
        XsoarSaasClientConfig(base_api_url="https://test1.com", auth_id="1")


def test_init_xsiam_client_config_with_api_key_and_auth_id():
    assert XsiamClientConfig(
        base_api_url="https://test1.com", api_key="test", auth_id="1"
    )


def test_init_xsiam_client_config_with_api_key_and_auth_id_and_token():
    assert XsiamClientConfig(
        base_api_url="https://test1.com", api_key="test", auth_id="1", token="test"
    )


def test_init_xsiam_client_config_with_api_key_and_token_without_auth_id():
    with pytest.raises(ValueError):
        XsiamClientConfig(
            base_api_url="https://test1.com", api_key="test", token="test"
        )

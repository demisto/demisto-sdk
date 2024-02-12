import os
from typing import Any, Dict, Optional

from pydantic import AnyUrl, BaseModel, Field, SecretStr, root_validator

from demisto_sdk.commands.common.constants import (
    AUTH_ID,
    DEMISTO_BASE_URL,
    DEMISTO_KEY,
    DEMISTO_PASSWORD,
    DEMISTO_USERNAME,
    DEMISTO_VERIFY_SSL,
    XSIAM_COLLECTOR_TOKEN,
    XSIAM_TOKEN,
)
from demisto_sdk.commands.common.tools import string_to_bool


class XsoarClientConfig(BaseModel):
    """
    api client config for xsoar-on-prem
    """

    base_api_url: AnyUrl = Field(
        default=os.getenv(DEMISTO_BASE_URL), description="XSOAR Tenant Base API URL"
    )
    api_key: SecretStr = Field(
        default=SecretStr(os.getenv(DEMISTO_KEY, "")), description="XSOAR API Key"
    )
    user: str = Field(
        default=os.getenv(DEMISTO_USERNAME, ""), description="XSOAR Username"
    )
    password: SecretStr = Field(
        default=SecretStr(os.getenv(DEMISTO_PASSWORD, "")), description="XSOAR Password"
    )
    verify_ssl: bool = string_to_bool(os.getenv(DEMISTO_VERIFY_SSL, False))

    @root_validator()
    def validate_auth_params(cls, values: Dict[str, Any]):
        if not values.get("api_key") and not (
            values.get("user") and values.get("password")
        ):
            raise ValueError(
                "Either api_key or both user and password must be provided"
            )
        return values

    def __getattr__(self, item):
        if item in {"token", "collector_token", "auth_id", "user", "password"}:
            self.__dict__[item] = None

    def __hash__(self) -> int:
        return hash(
            (
                str(self.base_api_url),
                self.api_key.get_secret_value(),
                self.user,
                self.password.get_secret_value(),
                self.auth_id,
            )
        )

    def __eq__(self, other):
        return (
            str(self.base_api_url) == str(other.base_api_url)
            and self.api_key.get_secret_value() == other.api_key.get_secret_value()
            and self.user == other.user
            and self.password.get_secret_value() == other.password.get_secret_value()
            and self.auth_id == other.auth_id
        )


class XsoarSaasClientConfig(XsoarClientConfig):
    auth_id: str = Field(default=os.getenv(AUTH_ID), description="XSOAR/XSIAM Auth ID")

    @root_validator()
    def validate_auth_params(cls, values: Dict[str, Any]):
        if not values.get("api_key"):
            raise ValueError("api_key is required for xsoar-saas/xsiam")
        if not values.get("auth_id"):
            raise ValueError("auth_id is required for xsoar-saas/xsiam")
        return values


class XsiamClientConfig(XsoarSaasClientConfig):
    token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv(XSIAM_TOKEN, "")), description="XSIAM Token"
    )
    collector_token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv(XSIAM_COLLECTOR_TOKEN, "")),
        description="XSIAM HTTP Collector Token",
    )

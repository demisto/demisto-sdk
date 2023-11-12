import os
from typing import Optional

from pydantic import BaseModel, Field, SecretStr, validator
from pydantic.fields import ModelField

from demisto_sdk.commands.common.constants import (
    AUTH_ID,
    DEMISTO_API_KEY,
    DEMISTO_BASE_URL,
    XSIAM_COLLECTOR_TOKEN,
    XSIAM_TOKEN,
)


class XsoarClientConfig(BaseModel):

    base_api_url: str = Field(
        default=os.getenv(DEMISTO_BASE_URL), description="XSOAR Tenant Base API URL"
    )
    api_key: SecretStr = Field(
        default=SecretStr(os.getenv(DEMISTO_API_KEY, "")), description="XSOAR API Key"
    )

    @classmethod
    def validate_config(cls, v, field: ModelField):
        if not v:
            raise ValueError(
                f"XSOAR client configuration is not complete: value was not passed for {field.name} and"
                f" the associated environment variable for {field.name} is not set"
            )
        return v

    @validator("base_api_url", "api_key", always=True)
    def validate_base_url_and_api_key(cls, v, field: ModelField):
        return cls.validate_config(v, field)

    def __getattr__(self, item):
        if item in {"token", "collector_token", "auth_id"}:
            self.__dict__[item] = None

    def __hash__(self) -> int:
        return hash((self.base_api_url, self.api_key.get_secret_value(), self.auth_id))

    def __eq__(self, other: "XsoarClientConfig") -> bool:
        return (
            self.base_api_url == other.base_api_url
            and self.api_key.get_secret_value() == other.api_key.get_secret_value()
            and self.auth_id == other.auth_id
        )


class XsoarSaasClientConfig(XsoarClientConfig):
    auth_id: Optional[str] = Field(
        default=os.getenv(AUTH_ID), description="XSOAR/XSIAM Auth ID"
    )

    @validator("auth_id", always=True)
    def validate_auth_id(cls, v, field: ModelField):
        return cls.validate_config(v, field)


class XsiamClientConfig(XsoarSaasClientConfig):
    token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv(XSIAM_TOKEN, "")), description="XSIAM Token"
    )
    collector_token: Optional[SecretStr] = Field(
        default=SecretStr(os.getenv(XSIAM_COLLECTOR_TOKEN, "")),
        description="XSIAM HTTP Collector Token",
    )

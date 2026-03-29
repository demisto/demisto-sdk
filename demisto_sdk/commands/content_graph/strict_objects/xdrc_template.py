from typing import List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionJson,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class _StrictXDRCTemplate(BaseStrictModel):
    os_type: str = Field(
        ...,
        description="Operating system type this template targets. Must be one of: 'Windows', 'Linux', 'macOS'.",
    )
    profile_type: str = Field(
        ...,
        description="Type of XDRC profile this template creates. Defines the configuration category (e.g. 'Endpoint Security', 'Firewall').",
    )
    name: str = Field(
        ...,
        description="Display name of the XDRC template shown in the UI.",
    )
    content_global_id: str = Field(
        ...,
        description="Globally unique identifier for this template content. Used to track the template across platform versions.",
    )
    from_xdr_version: str = Field(
        ...,
        description="Minimum XDR agent version required to apply this template (e.g. '7.5.0').",
    )
    yaml_template: str = Field(
        ...,
        description="YAML-formatted configuration template content. Defines the actual configuration applied to endpoints.",
    )
    supportedModules: Optional[List[str]] = Field(
        None,
        alias="supportedModules",
        description="Optional list of platform modules that support this XDRC template. Restricts availability to specific modules.",
    )


StrictXDRCTemplate = create_model(
    model_name="StrictXDRCTemplate",
    base_models=(
        _StrictXDRCTemplate,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
    ),
)

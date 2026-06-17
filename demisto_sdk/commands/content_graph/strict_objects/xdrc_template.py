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
    os_type: str
    profile_type: str
    # NOTE: 'name' should exist in all XDR template content items, but is currently not supported
    # on XSIAM/Platform tenants.
    name: Optional[str] = None
    content_global_id: Optional[str] = None
    # NOTE: 'id' should exist in all XDR template content items, but is currently not supported
    # on XSIAM/Platform tenants.
    id: Optional[str] = None
    from_xdr_version: str
    yaml_template: str
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")


StrictXDRCTemplate = create_model(
    model_name="StrictXDRCTemplate",
    base_models=(
        _StrictXDRCTemplate,
        BaseOptionalVersionJson,
        NAME_DYNAMIC_MODEL,
    ),
)

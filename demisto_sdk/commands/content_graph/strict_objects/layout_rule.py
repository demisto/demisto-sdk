from typing import List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class FilterSchema(BaseStrictModel):
    SEARCH_FIELD: str
    SEARCH_TYPE: str
    SEARCH_VALUE: str


class AndSchema(BaseStrictModel):
    AND: Optional[List[Union["FilterSchema", "OrSchema", "AndSchema"]]] = None


class OrSchema(BaseStrictModel):
    OR: Optional[List[Union["FilterSchema", "OrSchema", "AndSchema"]]] = None


# Forward references to resolve circular dependencies
FilterSchema.update_forward_refs()
AndSchema.update_forward_refs()
OrSchema.update_forward_refs()


class AlertsFilter(BaseStrictModel):
    filter: Optional[Union[OrSchema, AndSchema]] = None


class _StrictLayoutRule(BaseStrictModel):
    rule_id: str
    rule_name: str
    layout_id: str
    from_version: str = Field(..., alias="fromVersion")
    description: Optional[str] = None
    alerts_filter: Optional[AlertsFilter] = None


StrictLayoutRule = create_model(
    model_name="StrictLayoutRule",
    base_models=(_StrictLayoutRule, DESCRIPTION_DYNAMIC_MODEL),
)

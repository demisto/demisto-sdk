from typing import List, Optional, Union

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)

SCHEMAS = Union["Filter", "Or", "And"]


class Filter(BaseStrictModel):
    SEARCH_FIELD: str
    SEARCH_TYPE: str
    SEARCH_VALUE: str


class And(BaseStrictModel):
    AND: Optional[List[SCHEMAS]] = None


class Or(BaseStrictModel):
    OR: Optional[List[SCHEMAS]] = None


# Forward references to resolve circular dependencies
Filter.update_forward_refs()
And.update_forward_refs()
Or.update_forward_refs()


class AlertsFilter(BaseStrictModel):
    filter: Optional[Union[Or, And]] = None


class _StrictLayoutRule(BaseStrictModel):
    rule_id: str
    rule_name: str
    layout_id: str
    from_version: str = Field(
        alias="fromVersion"
    )  # not using the base because it's required
    description: Optional[str] = None
    alerts_filter: Optional[AlertsFilter] = None


StrictLayoutRule = create_model(
    model_name="StrictLayoutRule",
    base_models=(_StrictLayoutRule, DESCRIPTION_DYNAMIC_MODEL),
)

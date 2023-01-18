import re
from logging import getLogger
from typing import List, Optional, Set, Union

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

logger = getLogger("demisto-sdk")


class Layout(ContentItem, content_type=ContentType.LAYOUT):  # type: ignore[call-arg]
    kind: Optional[str]
    tabs: Optional[List[str]]
    definition_id: Optional[str] = Field(alias="definitionId")
    group: str
    edit: bool
    indicators_details: bool
    indicators_quick_view: bool
    quick_view: bool
    close: bool
    details: bool
    details_v2: bool
    mobile: bool

    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def prepare_for_upload(
        self, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR, **kwargs
    ) -> dict:
        data = super().prepare_for_upload(marketplace, **kwargs)
        data = self._fix_from_and_to_server_version(data)

        if MarketplaceVersions.MarketplaceV2 in self.marketplaces:
            data = fix_widget_incident_to_alert(data)

        return data

    def _fix_from_and_to_server_version(self, data: dict) -> dict:
        # On Layouts, we manually add the `fromServerVersion`, `toServerVersion` fields, see CIAC-5195.
        data["fromServerVersion"] = self.fromversion
        data["toServerVersion"] = self.toversion
        return data


def fix_widget_incident_to_alert(data: dict) -> dict:
    if not isinstance(data, dict):
        raise TypeError(f"expected dictionary, got {type(data)}")

    def _fix_recursively(datum: Union[list, dict]) -> Union[list, dict]:
        if isinstance(datum, list):
            return [_fix_recursively(item) for item in datum]

        elif isinstance(datum, dict):
            if (
                datum.get("id") == "relatedIncidents"
                and datum.get("name") == "Related Incidents"
            ):  # the kind of dictionary we want to fix
                datum["name"] = "Related Alerts"
                return datum
            else:  # not the kind we want to fix, use recursion instead.
                return {key: _fix_recursively(value) for key, value in datum.items()}

        else:
            return datum  # nothing to change

    result = _fix_recursively(data)

    if not isinstance(result, dict):
        """
        the inner function returns a value of the same type as its input,
        so a dict input should never return a non-dict. this part is just for safety (mypy).
        """
        raise ValueError(f"unexpected type for a fixed-dictionary output {type(data)}")

    return result

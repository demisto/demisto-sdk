from pathlib import Path
from typing import Callable, List, Optional, Union

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


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
    version: Optional[int] = 0

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        # marketplace is the marketplace for which the content is prepared.
        data = super().prepare_for_upload(current_marketplace, **kwargs)
        data = self._fix_from_and_to_server_version(data)

        if (
            current_marketplace == MarketplaceVersions.MarketplaceV2
            and self.group == "indicator"
        ):
            data = replace_layout_incident_alert(data)

        return data

    def _fix_from_and_to_server_version(self, data: dict) -> dict:
        # On Layouts, we manually add the `fromServerVersion`, `toServerVersion` fields, see CIAC-5195.
        data["fromServerVersion"] = self.fromversion
        data["toServerVersion"] = self.toversion
        return data

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_layout

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "group" in _dict and Path(path).suffix == ".json":
            if "cliName" not in _dict:
                if "id" not in _dict or (
                    isinstance(_dict["id"], str)
                    and not _dict["id"].startswith("incident")
                    and not _dict["id"].startswith("indicator")
                ):
                    return True
        return False


def replace_layout_incident_alert(data: dict) -> dict:
    """
    Changes {"name": "Related/Linked/Chiled Incidents", ... }
         to {"name": "Related/Linked/Chiled Alerts", ... }
    """

    if not isinstance(data, dict):
        raise TypeError(f"expected dictionary, got {type(data)}")

    def fix_recursively(datum: Union[list, dict]) -> Union[list, dict]:
        if isinstance(datum, dict):
            if datum.get("name_x2") is not None:
                # already has a xsiam name, then we have nothing to do
                return datum
            if (name := datum.get("name", ""), datum.get("type")) in {
                ("Child Incidents", "childInv"),
                ("Linked Incidents", "linkedIncidents"),
                ("Related Incidents", "relatedIncidents"),
            }:
                datum["name"] = name.replace("Incident", "Alert")
                return datum
            else:  # not the atomic dictionary that we intend to fix, use recursion instead.
                return {key: fix_recursively(value) for key, value in datum.items()}

        elif isinstance(datum, list):
            return [fix_recursively(item) for item in datum]

        else:
            return datum  # nothing to change

    if not isinstance(result := fix_recursively(data), dict):
        """
        the inner function returns a value of the same type as its input,
        so a dict input should never return a non-dict. this part is just for safety (mypy).
        """
        raise ValueError(f"unexpected type for a fixed-dictionary output {type(data)}")

    return result

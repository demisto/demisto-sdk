from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.list_unifier import ListUnifier
from demisto_sdk.commands.upload.tools import parse_upload_response

json = JSON_Handler()


class List(ContentItem, content_type=ContentType.LIST):  # type: ignore[call-arg]
    type: str
    is_unified: bool
    version: Optional[int] = 0
    internal: bool = Field(False)
    source: str = Field("")

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        with TemporaryDirectory("w") as f:
            dir_path = Path(f)
            self.dump(dir_path, marketplace=marketplace)

            response = client.generic_request(
                method="POST",
                path="lists/save",
                body=json.loads((dir_path / self.normalize_name).read_text()),
                response_type="object",
            )
            parse_upload_response(
                response, path=self.path, content_type=self.content_type
            )  # raises on error
            return response

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = (
            self.data
            if kwargs.get("unify_only")
            else super().prepare_for_upload(current_marketplace)
        )
        if self.is_unified:
            return data
        return ListUnifier.unify(self.path, data, marketplace=current_marketplace)

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            isinstance(_dict, dict)
            and {"data", "allRead", "truncated"}.intersection(_dict.keys())
            and path.suffix == ".json"
        ):
            return True
        return False

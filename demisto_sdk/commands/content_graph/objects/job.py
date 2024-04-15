from pathlib import Path
from tempfile import TemporaryDirectory

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Job(ContentItem, content_type=ContentType.JOB):  # type: ignore[call-arg]
    description: str = Field(alias="details")

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        with TemporaryDirectory("w") as f:
            dir_path = Path(f)
            self.dump(dir_path, marketplace=marketplace)

            return client.generic_request(
                method="POST",
                path="jobs/import",
                files={"file": str(self.path)},
                content_type="multipart/form-data",
            )

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if (
            isinstance(_dict, dict)
            and {
                "isAllFeeds",
                "selectedFeeds",
                "isFeed",
            }.issubset(_dict.keys())
            and path.suffix == ".json"
        ):
            return True
        return False

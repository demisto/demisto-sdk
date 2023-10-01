import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import demisto_client

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()
logger = logging.getLogger("demisto-sdk")


class List(ContentItem, content_type=ContentType.LIST):  # type: ignore[call-arg]
    type: str

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        with TemporaryDirectory("w") as f:
            dir_path = Path(f)
            self.dump(dir_path, marketplace=marketplace)

            client.generic_request(
                method="POST",
                path="lists/save",
                body=json.loads((dir_path / self.normalize_name).read_text()),
                response_type="object",
            )

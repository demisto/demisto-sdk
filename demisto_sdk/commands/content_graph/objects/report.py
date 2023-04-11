from typing import Callable, Optional, Set

import demisto_client

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Report(ContentItem, content_type=ContentType.REPORT):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def _client_upload_method(self, client: demisto_client) -> Optional[Callable]:
        return client.upload_report

from typing import Callable

import demisto_client

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class Report(ContentItem, content_type=ContentType.REPORT):  # type: ignore[call-arg]
    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.upload_report

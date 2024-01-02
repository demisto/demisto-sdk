from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser


class ConfJSONParser(BaseContentParser):
    content_type = ContentType.CONF_JSON  # TODO check whether required

    @property
    def object_id(self) -> str:
        return "conf.json"

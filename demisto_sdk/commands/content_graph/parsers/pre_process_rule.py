from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import (
    JSONContentItemParser,
)


class PreprocessRuleParser(
    JSONContentItemParser, content_type=ContentType.PREPROCESS_RULE
):
    pass

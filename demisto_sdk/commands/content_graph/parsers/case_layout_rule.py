from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.layout_rule import LayoutRuleParser


class CaseLayoutRuleParser(
    LayoutRuleParser, content_type=ContentType.CASE_LAYOUT_RULE
):
    pass

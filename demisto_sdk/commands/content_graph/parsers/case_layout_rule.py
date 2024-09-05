from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.layout_rule import LayoutRuleParser
from demisto_sdk.commands.content_graph.strict_objects.case_layout_rule import (
    StrictCaseLayoutRule,
)


class CaseLayoutRuleParser(LayoutRuleParser, content_type=ContentType.CASE_LAYOUT_RULE):
    def connect_to_dependencies(self) -> None:
        """Collects the playbook used in the trigger as a mandatory dependency."""
        if layout := self.json_data.get("layout_id"):
            self.add_dependency_by_id(layout, ContentType.CASE_LAYOUT)

    @property
    def strict_object(self):
        return StrictCaseLayoutRule

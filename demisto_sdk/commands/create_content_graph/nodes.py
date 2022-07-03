import os

from neomodel import StructuredRel, StructuredNode, StringProperty, ArrayProperty, BooleanProperty, \
    RelationshipFrom, RelationshipTo, config

from constants import Rel, ScriptTypes, Marketplaces
from typing import Dict, Any

config.DATABASE_URL = os.getenv('DATABASE_URL')


""" RELATIONSHIP MODELS """


class DepencencyRel(StructuredRel):
    mandatory = BooleanProperty(required=True)


""" MIXINS (PROPERTIES USED IN MULTIPLE NODE TYPES) """


class MarketplacesMixin(object):
    marketplaces = ArrayProperty(StringProperty(choices=Marketplaces.to_dict()))


class VersionedMixin(object):
    fromversion = StringProperty(required=True)
    toversion = StringProperty()


class DeprecatableMixin(object):
    deprecated = BooleanProperty(required=True)


class TestableMixin(object):
    tests = RelationshipTo('TestPlaybookNode', Rel.TESTED_BY.value)


class IntegrationScriptMixin(object):
    type = StringProperty(choices=ScriptTypes.to_dict(), required=True)
    docker_image = StringProperty()
    source = ArrayProperty(StringProperty())


""" GRAPH NODES """


class BaseContentNode(StructuredNode):
    id = StringProperty(required=True, unique_index=True)
    name = StringProperty(required=True)
    display_name = StringProperty()
    file_path = StringProperty()

    @classmethod
    def create_or_update(cls, data: Dict[str, Any]) -> 'BaseContentNode':
        return super(BaseContentNode, cls).create_or_update(data)[0]


class ContentItemNode(BaseContentNode, MarketplacesMixin, VersionedMixin, DeprecatableMixin):
    dependencies_ids = ArrayProperty(StringProperty())
    dependencies = RelationshipTo('BaseContentNode', Rel.DEPENDS_ON.value, model=DepencencyRel)


class PackNode(BaseContentNode, MarketplacesMixin, DeprecatableMixin):
    author = StringProperty(required=True)
    certification = StringProperty(required=True)
    current_version = StringProperty(required=True)
    source = ArrayProperty(StringProperty())
    tags = ArrayProperty(StringProperty())
    use_cases = ArrayProperty(StringProperty())
    categories = ArrayProperty(StringProperty(), required=True)

    content_items = RelationshipFrom('ContentItemNode', Rel.IN_PACK.value)


class CommandNode(BaseContentNode, DeprecatableMixin):
    pass


class ScriptNode(CommandNode, ContentItemNode, IntegrationScriptMixin, TestableMixin):
    pass


class IntegrationNode(ContentItemNode, IntegrationScriptMixin, TestableMixin):
    is_fetch = BooleanProperty()
    is_feed = BooleanProperty()

    commands = RelationshipFrom(CommandNode, Rel.IN_INTEGRATION.value)


class PlaybookNode(ContentItemNode, TestableMixin):
    pass


class TestPlaybookNode(PlaybookNode):
    pass


class ClassifierNode(ContentItemNode):
    pass


class DashboardNode(ContentItemNode):
    pass


class IncidentFieldNode(ContentItemNode):
    pass


class IncidentTypeNode(ContentItemNode):
    pass


class IndicatorFieldNode(ContentItemNode):
    pass


class IndicatorTypeNode(ContentItemNode):
    pass


class LayoutNode(ContentItemNode):
    pass


class WidgeNode(ContentItemNode):
    pass


class MapperNode(ContentItemNode):
    pass


class GenericTypeNode(ContentItemNode):
    pass


class GenericFieldNode(ContentItemNode):
    pass


class GenericModuleNode(ContentItemNode):
    pass


class GenericDefinitionNode(ContentItemNode):
    pass


class ListNode(ContentItemNode):
    pass


class ReportNode(ContentItemNode):
    pass


class JobNode(ContentItemNode):
    pass


class WizardNode(ContentItemNode):
    pass


class ParsingRuleNode(ContentItemNode):
    pass


class ModelingRuleNode(ContentItemNode):
    pass


class CorrelationRuleNode(ContentItemNode):
    pass


class XSIAMDashboardNode(ContentItemNode):
    pass


class XSIAMReportNode(ContentItemNode):
    pass


class TriggerNode(ContentItemNode):
    pass

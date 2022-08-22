from pathlib import Path
from typing import Dict, List, Optional
from TestSuite.pack import Pack
from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, Relationships
from demisto_sdk.commands.content_graph.parsers import dashboard
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser


TEST_DATA_PATH = Path(git_path()) / 'demisto_sdk' / 'commands' / 'content_graph' / 'parsers' / 'tests' / 'test_data'


json = JSON_Handler()
yaml = YAML_Handler()


def load_json(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    with open(full_path, mode='r') as f:
        return json.load(f)


def load_yaml(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    with open(full_path, mode='r') as f:
        return yaml.load(f)


class ContentItemParserVerifier:
    @staticmethod
    def verify_relationships_by_type(
        relationships: Relationships,
        relationship_type: Rel,
        expected_targets: Dict[ContentTypes, List[str]],
    ) -> None:
        target_node_ids = set([
            relationship.get('target')
            for relationship in relationships.get(relationship_type, [])
        ])
        expected_target_node_ids = set([
            f'{content_type}:{content_item}'
            for content_type, targets in expected_targets.items()
            for content_item in targets
        ])
        assert target_node_ids == expected_target_node_ids

    @staticmethod
    def verify_expected_relationships(
        relationships: Relationships,
        dependencies: Dict[ContentTypes, List[str]] = {},
        commands_or_scripts_executions: Dict[ContentTypes, List[str]] = {},
        tests: Dict[ContentTypes, List[str]] = {},
        imports: Dict[ContentTypes, List[str]] = {},
        integration_commands: Dict[ContentTypes, List[str]] = {},
    ) -> None:
        for args in (
            (Rel.USES, dependencies),
            (Rel.USES_COMMAND_OR_SCRIPT, commands_or_scripts_executions),
            (Rel.TESTED_BY, tests),
            (Rel.IMPORTS, imports),
            (Rel.HAS_COMMAND, integration_commands),
        ):
            rel, expected_targets = args
            ContentItemParserVerifier.verify_relationships_by_type(relationships, rel, expected_targets)

    @staticmethod
    def run(
        parser: ContentItemParser,
        expected_id: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_path: Optional[Path] = None,
        expected_content_type: Optional[ContentTypes] = None,
        expected_description: Optional[str] = None,
        expected_deprecated: Optional[bool] = None,
        expected_fromversion: Optional[str] = None,
        expected_toversion: Optional[str] = None,
        dependencies: Dict[ContentTypes, List[str]] = {},
        commands_or_scripts_executions: Dict[ContentTypes, List[str]] = {},
        tests: Dict[ContentTypes, List[str]] = {},
        imports: Dict[ContentTypes, List[str]] = {},
        integration_commands: Dict[ContentTypes, List[str]] = {},
        ) -> None:
            assert expected_id is None or parser.object_id == expected_id
            assert expected_name is None or parser.name == expected_name
            assert expected_path is None or parser.path == expected_path
            assert expected_content_type is None or parser.content_type == expected_content_type
            assert expected_description is None or parser.description == expected_description
            assert expected_deprecated is None or parser.deprecated == expected_deprecated
            assert expected_fromversion is None or parser.fromversion == expected_fromversion
            assert expected_toversion is None or parser.toversion == expected_toversion
            ContentItemParserVerifier.verify_expected_relationships(
                parser.relationships,
                dependencies=dependencies,
                commands_or_scripts_executions=commands_or_scripts_executions,
                tests=tests,
                imports=imports,
                integration_commands=integration_commands,
            )


class TestParsers:
    """
    Given:
        - A pack with a content item (for every content type).
    When:
        - Initializing the content item parser.
    Then:
        - Verify the generic content item properties are parsed correctly.
        - Verify the specific properties of the content item are parsed correctly.
        - Verify all relationships of the content item are collected correctly.
    """

    def test_classifier_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.classifier import ClassifierParser
        classifier = pack.create_classifier('TestClassifier', load_json('classifier.json'))
        classifier_path = Path(classifier.path)
        parser = ClassifierParser(classifier_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='Github_Classifier_v1',
            expected_name='Github Classifier',
            expected_path=classifier_path,
            expected_description='Github Classifier',
            expected_content_type=ContentTypes.CLASSIFIER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Github', 'DevSecOps New Git PR'],
                ContentTypes.SCRIPT: ['isEqualString', 'isNotEmpty', 'getField'],
            }
        )
        assert parser.type == 'classification'

    def test_correlation_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.correlation_rule import CorrelationRuleParser
        colrrelation_rule = pack.create_correlation_rule('TestCorrelationRule', load_yaml('correlation_rule.yml'))
        colrrelation_rule_path = Path(colrrelation_rule.path)
        parser = CorrelationRuleParser(colrrelation_rule_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='correlation_rule_id',
            expected_name='correlation_rule_name',
            expected_path=colrrelation_rule_path,
            expected_content_type=ContentTypes.CORRELATION_RULE,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_dashboard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.dashboard import DashboardParser
        dashboard = pack.create_dashboard('TestDashboard', load_json('dashboard.json'))
        dashboard_path = Path(dashboard.path)
        parser = DashboardParser(dashboard_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='Confluera Dashboard',
            expected_name='Confluera Dashboard',
            expected_path=dashboard_path,
            expected_content_type=ContentTypes.DASHBOARD,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.SCRIPT: ['DetectionsCount', 'DetectionsData'],
            },
        )

    def test_generic_definition_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.generic_definition import GenericDefinitionParser
        generic_definition = pack.create_generic_definition('TestGenericDefinition', load_yaml('generic_definition.json'))
        generic_definition_path = Path(generic_definition.path)
        parser = GenericDefinitionParser(generic_definition_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='ThreatIntelReport',
            expected_name='Threat Intel Report',
            expected_path=generic_definition_path,
            expected_content_type=ContentTypes.GENERIC_DEFINITION,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_generic_module_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.generic_module import GenericModuleParser
        generic_module = pack.create_generic_module('TestGenericModule', load_yaml('generic_module.json'))
        generic_module_path = Path(generic_module.path)
        parser = GenericModuleParser(generic_module_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='threatIntel',
            expected_name='Threat Intel',
            expected_path=generic_module_path,
            expected_content_type=ContentTypes.GENERIC_MODULE,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert parser.definition_ids == ['ThreatIntelReport']

    def test_generic_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.generic_type import GenericTypeParser
        generic_type = pack.create_generic_module('TestGenericType', load_yaml('generic_type.json'))
        generic_type_path = Path(generic_type.path)
        parser = GenericTypeParser(generic_type_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='ThreatIntelReport_Malware',
            expected_name='Malware',
            expected_path=generic_type_path,
            expected_content_type=ContentTypes.GENERIC_TYPE,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={ContentTypes.LAYOUT: ['Malware Report']},
        )
        assert parser.definition_id == 'ThreatIntelReport'

    def test_incident_field_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.incident_field import IncidentFieldParser
        incident_field = pack.create_incident_field('TestIncidentField', load_yaml('incident_field.json'))
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(incident_field_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='cve',
            expected_name='CVE',
            expected_path=incident_field_path,
            expected_content_type=ContentTypes.INCIDENT_FIELD,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Vulnerability', 'Malware'],
            },
        )
        assert parser.cli_name == 'cve'
        assert parser.field_type == 'shortText'
        assert parser.associated_to_all == False

    def test_incident_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.incident_type import IncidentTypeParser
        incident_type = pack.create_incident_field('TestIncidentType', load_json('incident_type.json'))
        incident_type_path = Path(incident_type.path)
        parser = IncidentTypeParser(incident_type_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='Traps',
            expected_name='Traps',
            expected_path=incident_type_path,
            expected_content_type=ContentTypes.INCIDENT_TYPE,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.LAYOUT: ['Traps'],
                ContentTypes.PLAYBOOK: ['Palo Alto Networks - Endpoint Malware Investigation']
            },
        )
        assert parser.playbook == 'Palo Alto Networks - Endpoint Malware Investigation'
        assert parser.hours == 0
        assert parser.days == 0
        assert parser.weeks == 0
        assert not parser.closure_script

    def test_indicator_field_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.indicator_field import IndicatorFieldParser
        indicator_field = pack.create_incident_field('TestIndicatorField', load_yaml('indicator_field.json'))
        indicator_field_path = Path(indicator_field.path)
        parser = IndicatorFieldParser(indicator_field_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='email',
            expected_name='Email',
            expected_path=indicator_field_path,
            expected_content_type=ContentTypes.INDICATOR_FIELD,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.INDICATOR_TYPE: ['User Profile'],
            },
        )
        assert parser.type == 'shortText'
        assert parser.cli_name == 'email'
        assert parser.associated_to_all == False

    def test_indicator_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.indicator_type import IndicatorTypeParser
        indicator_type = pack.create_indicator_type('TestIndicatorType', load_yaml('indicator_type.json'))
        indicator_type_path = Path(indicator_type.path)
        parser = IndicatorTypeParser(indicator_type_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='urlRep',
            expected_name='URL',
            expected_path=indicator_type_path,
            expected_content_type=ContentTypes.INDICATOR_TYPE,
            expected_fromversion='5.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.SCRIPT: ['URLReputation'],
                ContentTypes.COMMAND: ['url'],
                ContentTypes.LAYOUT: ['urlRep'],
            },
        )
        assert parser.regex.startswith('(?i)((?:(?:https?')
        assert not parser.reputation_script_name
        assert parser.enhancement_script_names == ['URLReputation']

    def test_integration_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser

    def test_job_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.job import JobParser

    def test_layout_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser

    def test_list_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.list import ListParser
        list = pack.create_list('TestList', load_json('list.json'))
        list_path = Path(list.path)
        parser = ListParser(list_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='checked integrations',
            expected_name='checked integrations',
            expected_path=list_path,
            expected_description='',
            expected_content_type=ContentTypes.LIST,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert parser.type == 'plain_text'

    def test_incoming_mapper_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser
        mapper = pack.create_mapper('TestIncomingMapper', load_json('incoming_mapper.json'))
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='GitHub Mapper',
            expected_name='GitHub Mapper',
            expected_path=mapper_path,
            expected_description='',
            expected_content_type=ContentTypes.MAPPER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['DevSecOps New Git PR'],
                ContentTypes.INCIDENT_FIELD: ['devsecopsrepositoryname', 'devsecopsrepositoryorganization'],
                ContentTypes.SCRIPT: ['substringTo'],
            }
        )
        assert parser.type == 'mapping-incoming'

    def test_outgoing_mapper_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser
        mapper = pack.create_mapper('TestOutgoingMapper', load_json('outgoing_mapper.json'))
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path)
        ContentItemParserVerifier.run(
            parser,
            expected_id='Azure DevOps Outgoing Mapper',
            expected_name='Azure DevOps Outgoing Mapper',
            expected_path=mapper_path,
            expected_description='',
            expected_content_type=ContentTypes.MAPPER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Azure DevOps'],
                ContentTypes.INCIDENT_FIELD: ['description', 'azuredevopsprojectname'],
                ContentTypes.SCRIPT: ['MapValuesTransformer'],
            }
        )
        assert parser.type == 'mapping-outgoing'

    def test_modeling_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser

    def test_parsing_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.parsing_rule import ParsingRuleParser

    def test_playbook_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser

    def test_report_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.report import ReportParser

    def test_script_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.script import ScriptParser

    def test_test_playbook_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.test_playbook import TestPlaybookParser

    def test_trigger_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.trigger import TriggerParser

    def test_widget_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.widget import WidgetParser

    def test_wizard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.wizard import WizardParser

    def test_xsiam_dashboard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.xsiam_dashboard import XSIAMDashboardParser

    def test_xsiam_report_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.parsers.xsiam_report import XSIAMReportParser

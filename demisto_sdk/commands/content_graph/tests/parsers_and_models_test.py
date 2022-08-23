import pytest

from pathlib import Path
from typing import Dict, List, Optional
from TestSuite.pack import Pack
from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, Relationships
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers import dashboard
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser, IncorrectParser, NotAContentItem


TEST_DATA_PATH = Path(git_path()) / 'demisto_sdk' / 'commands' / 'content_graph' / 'tests' / 'test_data'


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


class ContentItemRelationshipsVerifier:
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
    def verify_command_executions(
        relationships: Relationships,
        expected_commands: List[str],
    ) -> None:
        target_node_ids = set([
            relationship.get('target')
            for relationship in relationships.get(Rel.USES_COMMAND_OR_SCRIPT, [])
        ])
        expected_target_node_ids = set([command for command in expected_commands])
        assert target_node_ids == expected_target_node_ids

    @staticmethod
    def verify_integration_commands(
        relationships: Relationships,
        expected_commands: List[str],
    ) -> None:
        target_node_ids = set([
            relationship.get('target')
            for relationship in relationships.get(Rel.HAS_COMMAND, [])
        ])
        expected_target_node_ids = set([command for command in expected_commands])
        assert target_node_ids == expected_target_node_ids

    @staticmethod
    def run(
        relationships: Relationships,
        dependencies: Dict[ContentTypes, List[str]] = {},
        commands_or_scripts_executions: Dict[ContentTypes, List[str]] = {},
        tests: Dict[ContentTypes, List[str]] = {},
        imports: Dict[ContentTypes, List[str]] = {},
        integration_commands: Dict[ContentTypes, List[str]] = {},
        ) -> None:
        ContentItemRelationshipsVerifier.verify_relationships_by_type(relationships, Rel.USES, dependencies)
        ContentItemRelationshipsVerifier.verify_relationships_by_type(relationships, Rel.TESTED_BY, tests)
        ContentItemRelationshipsVerifier.verify_relationships_by_type(relationships, Rel.IMPORTS, imports)
        ContentItemRelationshipsVerifier.verify_command_executions(relationships, commands_or_scripts_executions)
        ContentItemRelationshipsVerifier.verify_integration_commands(relationships, integration_commands)


class ContentItemModelVerifier:
    @staticmethod
    def run(
        model: ContentItem,
        expected_id: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_path: Optional[Path] = None,
        expected_content_type: Optional[ContentTypes] = None,
        expected_description: Optional[str] = None,
        expected_deprecated: Optional[bool] = None,
        expected_fromversion: Optional[str] = None,
        expected_toversion: Optional[str] = None,
    ) -> None:
        assert expected_id is None or model.object_id == expected_id
        assert expected_name is None or model.name == expected_name
        assert expected_path is None or model.path == expected_path
        assert expected_content_type is None or model.content_type == expected_content_type
        assert expected_description is None or model.description == expected_description
        assert expected_deprecated is None or model.deprecated == expected_deprecated
        assert expected_fromversion is None or model.fromversion == expected_fromversion
        assert expected_toversion is None or model.toversion == expected_toversion

class TestParsers:
    """
    Given:
        - A pack with a content item (for every content type).
    When:
        - Creating the content item's parser and model.
    Then:
        - Verify all relationships of the content item are collected (if exist).
        - Verify the generic content item properties are parsed correctly.
        - Verify the specific properties of the content item are parsed correctly.
    """

    def test_classifier_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.classifier import Classifier
        from demisto_sdk.commands.content_graph.parsers.classifier import ClassifierParser
        classifier = pack.create_classifier('TestClassifier', load_json('classifier.json'))
        classifier_path = Path(classifier.path)
        parser = ClassifierParser(classifier_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Github', 'DevSecOps New Git PR'],
                ContentTypes.SCRIPT: ['isEqualString', 'isNotEmpty', 'getField'],
            }
        )
        model = Classifier.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Github_Classifier_v1',
            expected_name='Github Classifier',
            expected_path=classifier_path,
            expected_description='Github Classifier',
            expected_content_type=ContentTypes.CLASSIFIER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'classification'

    def test_correlation_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
        from demisto_sdk.commands.content_graph.parsers.correlation_rule import CorrelationRuleParser
        colrrelation_rule = pack.create_correlation_rule('TestCorrelationRule', load_yaml('correlation_rule.yml'))
        colrrelation_rule_path = Path(colrrelation_rule.path)
        parser = CorrelationRuleParser(colrrelation_rule_path)
        assert not parser.relationships
        model = CorrelationRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='correlation_rule_id',
            expected_name='correlation_rule_name',
            expected_path=colrrelation_rule_path,
            expected_content_type=ContentTypes.CORRELATION_RULE,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_dashboard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
        from demisto_sdk.commands.content_graph.parsers.dashboard import DashboardParser
        dashboard = pack.create_dashboard('TestDashboard', load_json('dashboard.json'))
        dashboard_path = Path(dashboard.path)
        parser = DashboardParser(dashboard_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['DetectionsCount', 'DetectionsData'],
            },
        )
        model = Dashboard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Confluera Dashboard',
            expected_name='Confluera Dashboard',
            expected_path=dashboard_path,
            expected_content_type=ContentTypes.DASHBOARD,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_generic_definition_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.generic_definition import GenericDefinition
        from demisto_sdk.commands.content_graph.parsers.generic_definition import GenericDefinitionParser
        generic_definition = pack.create_generic_definition('TestGenericDefinition', load_json('generic_definition.json'))
        generic_definition_path = Path(generic_definition.path)
        parser = GenericDefinitionParser(generic_definition_path)
        assert not parser.relationships
        model = GenericDefinition.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='ThreatIntelReport',
            expected_name='Threat Intel Report',
            expected_path=generic_definition_path,
            expected_content_type=ContentTypes.GENERIC_DEFINITION,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_generic_module_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule
        from demisto_sdk.commands.content_graph.parsers.generic_module import GenericModuleParser
        generic_module = pack.create_generic_module('TestGenericModule', load_json('generic_module.json'))
        generic_module_path = Path(generic_module.path)
        parser = GenericModuleParser(generic_module_path)
        assert not parser.relationships
        model = GenericModule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='threatIntel',
            expected_name='Threat Intel',
            expected_path=generic_module_path,
            expected_content_type=ContentTypes.GENERIC_MODULE,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert parser.definition_ids == ['ThreatIntelReport']

    def test_generic_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
        from demisto_sdk.commands.content_graph.parsers.generic_type import GenericTypeParser
        generic_type = pack.create_generic_module('TestGenericType', load_json('generic_type.json'))
        generic_type_path = Path(generic_type.path)
        parser = GenericTypeParser(generic_type_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={ContentTypes.LAYOUT: ['Malware Report']},
        )
        model = GenericType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='ThreatIntelReport_Malware',
            expected_name='Malware',
            expected_path=generic_type_path,
            expected_content_type=ContentTypes.GENERIC_TYPE,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.definition_id == 'ThreatIntelReport'

    def test_incident_field_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
        from demisto_sdk.commands.content_graph.parsers.incident_field import IncidentFieldParser
        incident_field = pack.create_incident_field('TestIncidentField', load_json('incident_field.json'))
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(incident_field_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Vulnerability', 'Malware'],
            },
        )
        model = IncidentField.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='cve',
            expected_name='CVE',
            expected_path=incident_field_path,
            expected_content_type=ContentTypes.INCIDENT_FIELD,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.cli_name == 'cve'
        assert model.field_type == 'shortText'
        assert model.associated_to_all == False

    def test_incident_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
        from demisto_sdk.commands.content_graph.parsers.incident_type import IncidentTypeParser
        incident_type = pack.create_incident_field('TestIncidentType', load_json('incident_type.json'))
        incident_type_path = Path(incident_type.path)
        parser = IncidentTypeParser(incident_type_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.LAYOUT: ['Traps'],
                ContentTypes.PLAYBOOK: ['Palo Alto Networks - Endpoint Malware Investigation']
            },
        )
        model = IncidentType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Traps',
            expected_name='Traps',
            expected_path=incident_type_path,
            expected_content_type=ContentTypes.INCIDENT_TYPE,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.playbook == 'Palo Alto Networks - Endpoint Malware Investigation'
        assert model.hours == 0
        assert model.days == 0
        assert model.weeks == 0
        assert not model.closure_script

    def test_indicator_field_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
        from demisto_sdk.commands.content_graph.parsers.indicator_field import IndicatorFieldParser
        indicator_field = pack.create_incident_field('TestIndicatorField', load_json('indicator_field.json'))
        indicator_field_path = Path(indicator_field.path)
        parser = IndicatorFieldParser(indicator_field_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INDICATOR_TYPE: ['User Profile'],
            },
        )
        model = IndicatorField.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='email',
            expected_name='Email',
            expected_path=indicator_field_path,
            expected_content_type=ContentTypes.INDICATOR_FIELD,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'shortText'
        assert model.cli_name == 'email'
        assert model.associated_to_all == False

    def test_indicator_type_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
        from demisto_sdk.commands.content_graph.parsers.indicator_type import IndicatorTypeParser
        indicator_type = pack.create_indicator_type('TestIndicatorType', load_json('indicator_type.json'))
        indicator_type_path = Path(indicator_type.path)
        parser = IndicatorTypeParser(indicator_type_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['URLReputation'],
                ContentTypes.COMMAND: ['url'],
                ContentTypes.LAYOUT: ['urlRep'],
            },
        )
        model = IndicatorType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='urlRep',
            expected_name='URL',
            expected_path=indicator_type_path,
            expected_content_type=ContentTypes.INDICATOR_TYPE,
            expected_fromversion='5.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.regex.startswith('(?i)((?:(?:https?')
        assert not model.reputation_script_name
        assert model.enhancement_script_names == ['URLReputation']

    def test_integration_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.integration import Integration
        from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
        integration = pack.create_integration()
        integration.create_default_integration('TestIntegration')
        integration.code.write('from MicrosoftApiModule import *')
        integration.yml.update({'tests': ['test_playbook']})
        integration_path = Path(integration.path)
        parser = IntegrationParser(integration_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            integration_commands=['test-command'],
            imports={
                ContentTypes.SCRIPT: ['MicrosoftApiModule']
            },
            tests={
                ContentTypes.TEST_PLAYBOOK: ['test_playbook']
            },
        )
        model = Integration.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='TestIntegration',
            expected_name='TestIntegration',
            expected_content_type=ContentTypes.INTEGRATION,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_unified_integration_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.integration import Integration
        from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
        integration = pack.create_integration(yml=load_yaml('unified_integration.yml'))
        integration_path = Path(integration.path)
        parser = IntegrationParser(integration_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            integration_commands=['malwr-submit', 'malwr-status', 'malwr-result', 'malwr-detonate'],
        )
        model = Integration.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='malwr',
            expected_name='malwr',
            expected_content_type=ContentTypes.INTEGRATION,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.category == 'Forensics & Malware Analysis'
        assert model.display_name == 'malwr'
        assert model.docker_image == 'demisto/bs4:1.0.0.7863'
        assert not model.is_fetch
        assert not model.is_feed
        assert model.type == 'python2'

    def test_job_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.job import Job
        from demisto_sdk.commands.content_graph.parsers.job import JobParser
        job = pack.create_job(is_feed=False, name='TestJob')
        job_path = Path(job.path)
        parser = JobParser(job_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.PLAYBOOK: ['job-TestJob_playbook'],
            },
        )
        model = Job.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='TestJob',
            expected_name='TestJob',
            expected_path=job_path,
            expected_content_type=ContentTypes.JOB,
            expected_fromversion='6.8.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_layout_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.layout import Layout
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser
        layout = pack.create_layout('TestLayout')
        layout_path = Path(layout.path)
        with pytest.raises(NotAContentItem):
            LayoutParser(layout_path)

    def test_layoutscontainer_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.layout import Layout
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser
        layout = pack.create_layoutcontainer('TestLayoutscontainer', load_json('layoutscontainer.json'))
        layout_path = Path(layout.path)
        parser = LayoutParser(layout_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INCIDENT_FIELD: [
                    'xdrdevicecontrolviolations',
                    'type',
                    'dbotsource',
                    'sourceinstance',
                    'severity',
                    'playbookid',
                    'sourcebrand',
                    'owner',
                ],
            },
        )
        model = Layout.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Cortex XDR Device Control Violations',
            expected_name='Cortex XDR Device Control Violations',
            expected_path=layout_path,
            expected_content_type=ContentTypes.LAYOUT,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_list_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.list import List
        from demisto_sdk.commands.content_graph.parsers.list import ListParser
        list = pack.create_list('TestList', load_json('list.json'))
        list_path = Path(list.path)
        parser = ListParser(list_path)
        assert not parser.relationships
        model = List.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='checked integrations',
            expected_name='checked integrations',
            expected_path=list_path,
            expected_description='',
            expected_content_type=ContentTypes.LIST,
            expected_fromversion='6.5.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'plain_text'

    def test_incoming_mapper_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.mapper import Mapper
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser
        mapper = pack.create_mapper('TestIncomingMapper', load_json('incoming_mapper.json'))
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['DevSecOps New Git PR'],
                ContentTypes.INCIDENT_FIELD: ['devsecopsrepositoryname', 'devsecopsrepositoryorganization'],
                ContentTypes.SCRIPT: ['substringTo'],
            }
        )
        model = Mapper.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='GitHub Mapper',
            expected_name='GitHub Mapper',
            expected_path=mapper_path,
            expected_description='',
            expected_content_type=ContentTypes.MAPPER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'mapping-incoming'

    def test_outgoing_mapper_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.mapper import Mapper
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser
        mapper = pack.create_mapper('TestOutgoingMapper', load_json('outgoing_mapper.json'))
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.INCIDENT_TYPE: ['Azure DevOps'],
                ContentTypes.INCIDENT_FIELD: ['description', 'azuredevopsprojectname'],
                ContentTypes.SCRIPT: ['MapValuesTransformer'],
            }
        )
        model = Mapper.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Azure DevOps Outgoing Mapper',
            expected_name='Azure DevOps Outgoing Mapper',
            expected_path=mapper_path,
            expected_description='',
            expected_content_type=ContentTypes.MAPPER,
            expected_fromversion='6.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'mapping-outgoing'

    def test_modeling_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
        from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
        modeling_rule = pack.create_modeling_rule('TestModelingRule', load_yaml('modeling_rule.yml'))
        modeling_rule_path = Path(modeling_rule.path)
        parser = ModelingRuleParser(modeling_rule_path)
        assert not parser.relationships
        model = ModelingRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='duo_modeling_rule',
            expected_name='Duo Modeling Rule',
            expected_content_type=ContentTypes.MODELING_RULE,
            expected_fromversion='6.8.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_parsing_rule_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
        from demisto_sdk.commands.content_graph.parsers.parsing_rule import ParsingRuleParser
        parsing_rule = pack.create_parsing_rule('TestParsingRule', load_yaml('parsing_rule.yml'))
        parsing_rule_path = Path(parsing_rule.path)
        parser = ParsingRuleParser(parsing_rule_path)
        assert not parser.relationships
        model = ParsingRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='_parsing_rule_id',
            expected_name='My Rule',
            expected_content_type=ContentTypes.PARSING_RULE,
            expected_fromversion='6.8.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_playbook_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.playbook import Playbook
        from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
        playbook = pack.create_playbook()
        playbook.create_default_playbook(name='sample')
        playbook_path = Path(playbook.path)
        parser = PlaybookParser(playbook_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['DeleteContext']
            },
        )
        model = Playbook.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='sample',
            expected_name='sample',
            expected_content_type=ContentTypes.PLAYBOOK,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert not model.is_test

    def test_report_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.report import Report
        from demisto_sdk.commands.content_graph.parsers.report import ReportParser
        report = pack.create_report('TestReport', load_json('report.json'))
        report_path = Path(report.path)
        parser = ReportParser(report_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['ProofpointTAPMostAttackedUsers', 'ProofpointTapTopClickers'],
            }
        )
        model = Report.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='ProofpointTAPWeeklyReport',
            expected_name='Proofpoint TAP Weekly Report',
            expected_path=report_path,
            expected_content_type=ContentTypes.REPORT,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_script_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.script import Script
        from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
        script = pack.create_script()
        script.create_default_script()
        script.code.write('demisto.executeCommand("dummy-command", dArgs)')
        script_path = Path(script.path)
        parser = ScriptParser(script_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            commands_or_scripts_executions=['dummy-command'],
        )
        model = Script.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='sample_script',
            expected_name='sample_script',
            expected_content_type=ContentTypes.SCRIPT,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == 'python3'
        assert model.docker_image == 'demisto/python3:3.8.3.8715'
        assert model.tags == ['transformer']
        assert not model.is_test

    def test_test_playbook_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
        from demisto_sdk.commands.content_graph.parsers.test_playbook import TestPlaybookParser
        test_playbook = pack.create_test_playbook()
        test_playbook.create_default_test_playbook(name='sample')
        test_playbook_path = Path(test_playbook.path)
        parser = TestPlaybookParser(test_playbook_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['DeleteContext']
            },
        )
        model = TestPlaybook.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='sample',
            expected_name='sample',
            expected_content_type=ContentTypes.TEST_PLAYBOOK,
            expected_fromversion='5.0.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.is_test

    def test_trigger_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.trigger import Trigger
        from demisto_sdk.commands.content_graph.parsers.trigger import TriggerParser
        trigger = pack.create_trigger('TestTrigger', load_json('trigger.json'))
        trigger_path = Path(trigger.path)
        parser = TriggerParser(trigger_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.PLAYBOOK: ['NGFW Scan'],
            }
        )
        model = Trigger.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='73545719a1bdeba6ba91f6a16044c021',
            expected_name='NGFW Scanning Alerts',
            expected_path=trigger_path,
            expected_content_type=ContentTypes.TRIGGER,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_widget_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.widget import Widget
        from demisto_sdk.commands.content_graph.parsers.widget import WidgetParser
        widget = pack.create_widget('TestWidget', load_json('widget.json'))
        widget_path = Path(widget.path)
        parser = WidgetParser(widget_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.SCRIPT: ['FeedIntegrationErrorWidget'],
            }
        )
        model = Widget.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='Feed Integrations Errors',
            expected_name='Feed Integrations Errors',
            expected_path=widget_path,
            expected_content_type=ContentTypes.WIDGET,
            expected_fromversion='6.1.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_wizard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.wizard import Wizard
        from demisto_sdk.commands.content_graph.parsers.wizard import WizardParser
        wizard = pack.create_wizard('TestWizard')
        wizard_path = Path(wizard.path)
        parser = WizardParser(wizard_path)
        ContentItemRelationshipsVerifier.run(
            parser.relationships,
            dependencies={
                ContentTypes.PACK: ['blabla'],  # todo
            }
        )
        model = Wizard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='TestWizard',
            expected_name='TestWizard',
            expected_path=wizard_path,
            expected_content_type=ContentTypes.WIZARD,
            expected_fromversion='6.8.0',
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_xsiam_dashboard_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
        from demisto_sdk.commands.content_graph.parsers.xsiam_dashboard import XSIAMDashboardParser
        xsiam_dashboard = pack.create_xsiam_dashboard('TestXSIAMDashboard', load_json('xsiam_dashboard.json'))
        xsiam_dashboard_path = Path(xsiam_dashboard.path)
        parser = XSIAMDashboardParser(xsiam_dashboard_path)
        assert not parser.relationships
        model = XSIAMDashboard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='ce27311ce69c41b1b4a84c7888b34852',
            expected_name='New Import test ',
            expected_path=xsiam_dashboard_path,
            expected_content_type=ContentTypes.XSIAM_DASHBOARD,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_xsiam_report_parser(self, pack: Pack):
        from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
        from demisto_sdk.commands.content_graph.parsers.xsiam_report import XSIAMReportParser
        xsiam_report = pack.create_xsiam_report('TestXSIAMReport', load_json('xsiam_report.json'))
        xsiam_report_path = Path(xsiam_report.path)
        parser = XSIAMReportParser(xsiam_report_path)
        assert not parser.relationships
        model = XSIAMReport.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id='sample',
            expected_name='sample',
            expected_path=xsiam_report_path,
            expected_content_type=ContentTypes.XSIAM_REPORT,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

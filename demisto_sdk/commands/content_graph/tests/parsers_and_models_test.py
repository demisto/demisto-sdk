from pathlib import Path
from typing import Dict, List, Optional, Set

import pytest

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack as PackModel
from demisto_sdk.commands.content_graph.objects.pre_process_rule import PreProcessRule
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    InvalidContentItemException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from demisto_sdk.commands.validate.tests.test_tools import (
    create_metadata_object,
)
from TestSuite.pack import Pack
from TestSuite.repo import Repo


def content_items_to_node_ids(
    content_items_dict: Dict[ContentType, List[str]]
) -> Set[str]:
    """A helper method that converts a dict of content items to a set of their node ids."""
    return {
        f"{content_type}:{content_item_id}"
        for content_type, content_items in content_items_dict.items()
        for content_item_id in content_items
    }


class RelationshipsVerifier:
    @staticmethod
    def verify_uses(
        relationships: Relationships,
        relationship_type: RelationshipType,
        expected_targets: Dict[str, ContentType],
    ) -> None:
        targets = {
            relationship.get("target"): relationship.get("target_type")
            for relationship in relationships.get(relationship_type, [])
        }
        assert targets == expected_targets

    @staticmethod
    def verify_command_executions(
        relationships: Relationships,
        expected_commands: List[str],
    ) -> None:
        targets = {
            relationship.get("target")
            for relationship in relationships.get(
                RelationshipType.USES_COMMAND_OR_SCRIPT, []
            )
        }
        expected_targets = {command for command in expected_commands}
        assert targets == expected_targets

    @staticmethod
    def verify_playbook_executions(
        relationships: Relationships,
        expected_playbooks: List[str],
    ) -> None:
        targets = {
            relationship.get("target")
            for relationship in relationships.get(RelationshipType.USES_PLAYBOOK, [])
        }
        expected_targets = {playbook for playbook in expected_playbooks}
        assert targets == expected_targets

    @staticmethod
    def verify_integration_commands(
        relationships: Relationships,
        expected_commands: List[str],
    ) -> None:
        targets = {
            relationship.get("target")
            for relationship in relationships.get(RelationshipType.HAS_COMMAND, [])
        }
        expected_targets = set(expected_commands)
        assert targets == expected_targets

    @staticmethod
    def verify_tests(
        relationships: Relationships,
        expected_tests: List[str],
    ) -> None:
        targets = {
            relationship.get("target")
            for relationship in relationships.get(RelationshipType.TESTED_BY, [])
        }
        expected_targets = set(expected_tests)
        assert targets == expected_targets

    @staticmethod
    def verify_imports(
        relationships: Relationships,
        expected_imports: List[str],
    ) -> None:
        targets = {
            relationship.get("target")
            for relationship in relationships.get(RelationshipType.IMPORTS, [])
        }
        expected_targets = set(expected_imports)
        assert targets == expected_targets

    @staticmethod
    def run(
        relationships: Relationships,
        dependency_ids: Dict[str, ContentType] = {},
        dependency_names: Dict[str, ContentType] = {},
        commands_or_scripts_executions: List[str] = [],
        playbook_executions: List[str] = [],
        tests: List[str] = [],
        imports: List[str] = [],
        integration_commands: List[str] = [],
    ) -> None:
        RelationshipsVerifier.verify_uses(
            relationships, RelationshipType.USES_BY_ID, dependency_ids
        )
        RelationshipsVerifier.verify_uses(
            relationships, RelationshipType.USES_BY_NAME, dependency_names
        )
        RelationshipsVerifier.verify_tests(relationships, tests)
        RelationshipsVerifier.verify_imports(relationships, imports)
        RelationshipsVerifier.verify_command_executions(
            relationships, commands_or_scripts_executions
        )
        RelationshipsVerifier.verify_playbook_executions(
            relationships, playbook_executions
        )
        RelationshipsVerifier.verify_integration_commands(
            relationships, integration_commands
        )


class ContentItemModelVerifier:
    @staticmethod
    def run(
        model: ContentItem,
        expected_id: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_path: Optional[Path] = None,
        expected_content_type: Optional[ContentType] = None,
        expected_description: Optional[str] = None,
        expected_deprecated: Optional[bool] = None,
        expected_fromversion: Optional[str] = None,
        expected_toversion: Optional[str] = None,
    ) -> None:
        assert expected_id is None or model.object_id == expected_id
        assert expected_name is None or model.name == expected_name
        assert expected_path is None or model.path == expected_path
        assert (
            expected_content_type is None or model.content_type == expected_content_type
        )
        assert expected_description is None or model.description == expected_description
        assert expected_deprecated is None or model.deprecated == expected_deprecated
        assert expected_fromversion is None or model.fromversion == expected_fromversion
        assert expected_toversion is None or model.toversion == expected_toversion


class PackModelVerifier:
    @staticmethod
    def run(
        model: PackModel,
        expected_id: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_path: Optional[Path] = None,
        expected_description: Optional[str] = None,
        expected_created: Optional[str] = None,
        expected_updated: Optional[str] = None,
        expected_legacy: Optional[bool] = None,
        expected_eulaLink: Optional[str] = None,
        expected_author_image: Optional[str] = None,
        expected_support: Optional[str] = None,
        expected_email: Optional[str] = None,
        expected_url: Optional[str] = None,
        expected_author: Optional[str] = None,
        expected_certification: Optional[str] = None,
        expected_hidden: Optional[bool] = None,
        expected_server_min_version: Optional[str] = None,
        expected_current_version: Optional[str] = None,
        expected_tags: Optional[List[str]] = None,
        expected_categories: Optional[List[str]] = None,
        expected_use_cases: Optional[List[str]] = None,
        expected_keywords: Optional[List[str]] = None,
        expected_price: Optional[int] = None,
        expected_premium: Optional[bool] = None,
        expected_vendor_id: Optional[str] = None,
        expected_vendor_name: Optional[str] = None,
        expected_preview_only: Optional[bool] = None,
        expected_marketplaces: Optional[List[MarketplaceVersions]] = None,
        expected_content_items: Dict[str, ContentType] = {},
        expected_deprecated: Optional[bool] = None,
    ) -> None:
        assert model.content_type == ContentType.PACK
        assert expected_id is None or model.object_id == expected_id
        assert expected_name is None or model.name == expected_name
        assert expected_path is None or model.path == expected_path
        assert expected_description is None or model.description == expected_description
        assert expected_created is None or model.created == expected_created
        assert expected_updated is None or model.updated == expected_updated
        assert expected_support is None or model.support == expected_support
        assert expected_legacy is None or model.legacy == expected_legacy
        assert expected_eulaLink is None or model.eulaLink == expected_eulaLink
        assert (
            expected_author_image is None or model.author_image == expected_author_image
        )
        assert expected_email is None or model.email == expected_email
        assert expected_deprecated is None or model.deprecated == expected_deprecated
        assert expected_url is None or model.url == expected_url
        assert expected_author is None or model.author == expected_author
        assert (
            expected_certification is None
            or model.certification == expected_certification
        )
        assert expected_hidden is None or model.hidden == expected_hidden
        assert (
            expected_server_min_version is None
            or model.server_min_version == expected_server_min_version
        )
        assert (
            expected_current_version is None
            or model.current_version == expected_current_version
        )
        assert expected_tags is None or model.tags == expected_tags
        assert expected_categories is None or model.categories == expected_categories
        assert expected_use_cases is None or model.use_cases == expected_use_cases
        assert expected_keywords is None or model.keywords == expected_keywords
        assert expected_price is None or model.price == expected_price
        assert expected_premium is None or model.premium == expected_premium
        assert expected_vendor_id is None or model.vendor_id == expected_vendor_id
        assert expected_vendor_name is None or model.vendor_name == expected_vendor_name
        assert (
            expected_preview_only is None or model.preview_only == expected_preview_only
        )
        assert (
            expected_marketplaces is None or model.marketplaces == expected_marketplaces
        )

        content_items = {
            content_item.object_id: content_item.content_type
            for content_item in model.content_items
        }
        assert content_items == expected_content_items

        for content_item in model.content_items:
            assert content_item.in_pack == model
            if content_item.content_type == ContentType.CLASSIFIER:
                assert content_item.ignored_errors == ["SC100"]


class PackRelationshipsVerifier:
    @staticmethod
    def run(
        relationships: Relationships,
        expected_content_items: Dict[str, ContentType] = {},
    ) -> None:
        content_items = {
            relationship.get("source_id"): relationship.get("source_type")
            for relationship in relationships.get(RelationshipType.IN_PACK, [])
        }
        assert content_items == expected_content_items


class TestParsersAndModels:
    def test_classifier_parser_below_min_marketplace_version(self, pack: Pack):
        """
        Given:
            - A pack with a classifier.
        When:
            - Classifier's toversion is 5.9.9.
            - Creating the content item's parser.
        Then:
            - Verify NotAContentItemException is raised, meaning we skip parsing the classifier.
        """
        from demisto_sdk.commands.content_graph.parsers.classifier import (
            ClassifierParser,
        )

        classifier = pack.create_classifier(
            "TestClassifier", load_json("classifier.json")
        )
        classifier.update({"toVersion": "5.9.9"})
        classifier_path = Path(classifier.path)
        with pytest.raises(NotAContentItemException):
            ClassifierParser(classifier_path, list(MarketplaceVersions))

    def test_classifier_parser(self, pack: Pack):
        """
        Given:
            - A pack with a classifier.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.classifier import Classifier
        from demisto_sdk.commands.content_graph.parsers.classifier import (
            ClassifierParser,
        )

        classifier = pack.create_classifier(
            "TestClassifier", load_json("classifier.json")
        )
        classifier_path = Path(classifier.path)
        parser = ClassifierParser(classifier_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "Github": ContentType.INCIDENT_TYPE,
                "DevSecOps New Git PR": ContentType.INCIDENT_TYPE,
                "isEqualString": ContentType.BASE_SCRIPT,
                "isNotEmpty": ContentType.BASE_SCRIPT,
                "getField": ContentType.BASE_SCRIPT,
            },
        )
        model = Classifier.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Github_Classifier_v1",
            expected_name="Github Classifier",
            expected_path=classifier_path,
            expected_description="Github Classifier",
            expected_content_type=ContentType.CLASSIFIER,
            expected_fromversion="6.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == "classification"

    def test_correlation_rule_parser(self, pack: Pack):
        """
        Given:
            - A pack with a correlation rule.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.correlation_rule import (
            CorrelationRule,
        )
        from demisto_sdk.commands.content_graph.parsers.correlation_rule import (
            CorrelationRuleParser,
        )

        colrrelation_rule = pack.create_correlation_rule(
            "TestCorrelationRule", load_yaml("correlation_rule.yml")
        )
        colrrelation_rule_path = Path(colrrelation_rule.path)
        parser = CorrelationRuleParser(
            colrrelation_rule_path, list(MarketplaceVersions)
        )
        assert not parser.relationships
        model = CorrelationRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="correlation_rule_id",
            expected_name="correlation_rule_name",
            expected_path=colrrelation_rule_path,
            expected_content_type=ContentType.CORRELATION_RULE,
            expected_fromversion=DEFAULT_CONTENT_ITEM_FROM_VERSION,
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_dashboard_parser(self, pack: Pack):
        """
        Given:
            - A pack with a dashboard.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
        from demisto_sdk.commands.content_graph.parsers.dashboard import DashboardParser

        dashboard = pack.create_dashboard("TestDashboard", load_json("dashboard.json"))
        dashboard_path = Path(dashboard.path)
        parser = DashboardParser(dashboard_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "DetectionsCount": ContentType.BASE_SCRIPT,
                "DetectionsData": ContentType.BASE_SCRIPT,
            },
        )
        model = Dashboard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Confluera Dashboard",
            expected_name="Confluera Dashboard",
            expected_path=dashboard_path,
            expected_content_type=ContentType.DASHBOARD,
            expected_fromversion="6.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_generic_definition_parser(self, pack: Pack):
        """
        Given:
            - A pack with a generic definition.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.generic_definition import (
            GenericDefinition,
        )
        from demisto_sdk.commands.content_graph.parsers.generic_definition import (
            GenericDefinitionParser,
        )

        generic_definition = pack.create_generic_definition(
            "TestGenericDefinition", load_json("generic_definition.json")
        )
        generic_definition_path = Path(generic_definition.path)
        parser = GenericDefinitionParser(
            generic_definition_path, list(MarketplaceVersions)
        )
        assert not parser.relationships
        model = GenericDefinition.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="ThreatIntelReport",
            expected_name="Threat Intel Report",
            expected_path=generic_definition_path,
            expected_content_type=ContentType.GENERIC_DEFINITION,
            expected_fromversion="6.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_generic_module_parser(self, pack: Pack):
        """
        Given:
            - A pack with a generic module.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.generic_module import (
            GenericModule,
        )
        from demisto_sdk.commands.content_graph.parsers.generic_module import (
            GenericModuleParser,
        )

        generic_module = pack.create_generic_module(
            "TestGenericModule", load_json("generic_module.json")
        )
        generic_module_path = Path(generic_module.path)
        parser = GenericModuleParser(generic_module_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = GenericModule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="threatIntel",
            expected_name="Threat Intel",
            expected_path=generic_module_path,
            expected_content_type=ContentType.GENERIC_MODULE,
            expected_fromversion="6.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert parser.definition_ids == ["ThreatIntelReport"]

    def test_generic_type_parser(self, pack: Pack):
        """
        Given:
            - A pack with a generic type.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.generic_type import GenericType
        from demisto_sdk.commands.content_graph.parsers.generic_type import (
            GenericTypeParser,
        )

        generic_type = pack.create_generic_module(
            "TestGenericType", load_json("generic_type.json")
        )
        generic_type_path = Path(generic_type.path)
        parser = GenericTypeParser(generic_type_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={"Malware Report": ContentType.LAYOUT},
        )
        model = GenericType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="ThreatIntelReport_Malware",
            expected_name="Malware",
            expected_path=generic_type_path,
            expected_content_type=ContentType.GENERIC_TYPE,
            expected_fromversion="6.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.definition_id == "ThreatIntelReport"

    def test_incident_field_parser(self, pack: Pack):
        """
        Given:
            - A pack with an incident field.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.incident_field import (
            IncidentField,
        )
        from demisto_sdk.commands.content_graph.parsers.incident_field import (
            IncidentFieldParser,
        )

        incident_field = pack.create_incident_field(
            "TestIncidentField", load_json("incident_field.json")
        )
        incident_field_path = Path(incident_field.path)
        parser = IncidentFieldParser(incident_field_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_names={
                "Vulnerability": ContentType.INCIDENT_TYPE,
                "Malware": ContentType.INCIDENT_TYPE,
            },
        )
        model = IncidentField.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="cve",
            expected_name="CVE",
            expected_path=incident_field_path,
            expected_content_type=ContentType.INCIDENT_FIELD,
            expected_fromversion="5.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.cli_name == "cve"
        assert model.field_type == "shortText"
        assert not model.associated_to_all

    def test_incident_type_parser(self, pack: Pack):
        """
        Given:
            - A pack with an incident type.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.incident_type import (
            IncidentType,
        )
        from demisto_sdk.commands.content_graph.parsers.incident_type import (
            IncidentTypeParser,
        )

        incident_type = pack.create_incident_field(
            "TestIncidentType", load_json("incident_type.json")
        )
        incident_type_path = Path(incident_type.path)
        parser = IncidentTypeParser(incident_type_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "Traps": ContentType.LAYOUT,
                "Palo Alto Networks - Endpoint Malware Investigation": ContentType.BASE_PLAYBOOK,
            },
        )
        model = IncidentType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Traps",
            expected_name="Traps",
            expected_path=incident_type_path,
            expected_content_type=ContentType.INCIDENT_TYPE,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.playbook == "Palo Alto Networks - Endpoint Malware Investigation"
        assert model.hours == 0
        assert model.days == 0
        assert model.weeks == 0
        assert not model.closure_script

    def test_indicator_field_parser(self, pack: Pack):
        """
        Given:
            - A pack with an indicator field.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.indicator_field import (
            IndicatorField,
        )
        from demisto_sdk.commands.content_graph.parsers.indicator_field import (
            IndicatorFieldParser,
        )

        indicator_field = pack.create_incident_field(
            "TestIndicatorField", load_json("indicator_field.json")
        )
        indicator_field_path = Path(indicator_field.path)
        parser = IndicatorFieldParser(indicator_field_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_names={
                "User Profile": ContentType.INDICATOR_TYPE,
            },
        )
        model = IndicatorField.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="email",
            expected_name="Email",
            expected_path=indicator_field_path,
            expected_content_type=ContentType.INDICATOR_FIELD,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.field_type == "shortText"
        assert model.cli_name == "email"
        assert not model.associated_to_all

    def test_indicator_type_parser(self, pack: Pack):
        """
        Given:
            - A pack with an indicator type.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.indicator_type import (
            IndicatorType,
        )
        from demisto_sdk.commands.content_graph.parsers.indicator_type import (
            IndicatorTypeParser,
        )

        indicator_type = pack.create_indicator_type(
            "TestIndicatorType", load_json("indicator_type.json")
        )
        indicator_type_path = Path(indicator_type.path)
        parser = IndicatorTypeParser(indicator_type_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "URLReputation": ContentType.BASE_SCRIPT,
                "url": ContentType.COMMAND,
                "urlRep": ContentType.LAYOUT,
            },
        )
        model = IndicatorType.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="urlRep",
            expected_name="URL",
            expected_path=indicator_type_path,
            expected_content_type=ContentType.INDICATOR_TYPE,
            expected_fromversion="5.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.regex.startswith("(?i)((?:(?:https?")
        assert not model.reputation_script_name
        assert model.enhancement_script_names == ["URLReputation"]

    def test_integration_parser(self, pack: Pack):
        """
        Given:
            - A pack with an integration.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.integration import Integration
        from demisto_sdk.commands.content_graph.parsers.integration import (
            IntegrationParser,
        )

        integration = pack.create_integration(yml=load_yaml("integration.yml"))
        integration.code.write("from MicrosoftApiModule import *")
        integration.yml.update({"tests": ["test_playbook"]})

        integration_path = Path(integration.path)
        parser = IntegrationParser(integration_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            integration_commands=["test-command"],
            imports=["MicrosoftApiModule"],
            tests=["test_playbook"],
        )
        model = Integration.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="TestIntegration",
            expected_name="TestIntegration",
            expected_content_type=ContentType.INTEGRATION,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.is_fetch_events is False
        assert model.is_fetch_assets is True

    def test_unified_integration_parser(self, pack: Pack):
        """
        Given:
            - A pack with a unified integration.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.integration import Integration
        from demisto_sdk.commands.content_graph.parsers.integration import (
            IntegrationParser,
        )

        integration = pack.create_integration(yml=load_yaml("unified_integration.yml"))
        integration_path = Path(integration.path)
        parser = IntegrationParser(integration_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            integration_commands=[
                "malwr-submit",
                "malwr-status",
                "malwr-result",
                "malwr-detonate",
            ],
        )
        model = Integration.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="malwr",
            expected_name="malwr",
            expected_content_type=ContentType.INTEGRATION,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.category == "Forensics & Malware Analysis"
        assert model.display_name == "malwr"
        assert model.docker_image == "demisto/bs4:1.0.0.7863"
        assert not model.is_fetch
        assert not model.is_feed
        assert model.type == "python"
        assert model.subtype == "python2"

    def test_job_parser(self, pack: Pack):
        """
        Given:
            - A pack with a job.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.job import Job
        from demisto_sdk.commands.content_graph.parsers.job import JobParser

        job = pack.create_job(is_feed=False, name="TestJob")
        job_path = Path(job.path)
        parser = JobParser(job_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "job-TestJob_playbook": ContentType.BASE_PLAYBOOK,
            },
        )
        model = Job.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="TestJob",
            expected_name="TestJob",
            expected_path=job_path,
            expected_content_type=ContentType.JOB,
            expected_fromversion="6.8.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_layout_parser(self, pack: Pack):
        """
        Given:
            - A pack with a layout.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects import Layout
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser

        layout = pack.create_layout("TestLayout")
        layout_path = Path(layout.path)
        parser = LayoutParser(layout_path, list(MarketplaceVersions))
        model = Layout.from_orm(parser)

        ContentItemModelVerifier.run(
            model,
            expected_id="TestLayout",
            expected_name="TestLayout",
            expected_path=layout_path,
            expected_content_type=ContentType.LAYOUT,
            expected_fromversion="6.8.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_layoutscontainer_parser(self, pack: Pack):
        """
        Given:
            - A pack with a layout.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.layout import Layout
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser

        layout = pack.create_layoutcontainer(
            "TestLayoutscontainer", load_json("layoutscontainer.json")
        )
        layout_path = Path(layout.path)
        parser = LayoutParser(layout_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "xdrdevicecontrolviolations": ContentType.INCIDENT_FIELD,
                "type": ContentType.INCIDENT_FIELD,
                "dbotsource": ContentType.INCIDENT_FIELD,
                "sourceinstance": ContentType.INCIDENT_FIELD,
                "severity": ContentType.INCIDENT_FIELD,
                "playbookid": ContentType.INCIDENT_FIELD,
                "sourcebrand": ContentType.INCIDENT_FIELD,
                "owner": ContentType.INCIDENT_FIELD,
            },
        )
        model = Layout.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Cortex XDR Device Control Violations",
            expected_name="Cortex XDR Device Control Violations",
            expected_path=layout_path,
            expected_content_type=ContentType.LAYOUT,
            expected_fromversion="6.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    @pytest.mark.parametrize("override_group", ("incident", "indicator"))
    @pytest.mark.parametrize(
        "marketplace",
        (
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
        ),
    )
    def test_layoutscontainer_parser_fixes(
        self, pack: Pack, marketplace: MarketplaceVersions, override_group: str
    ):
        """
        Given:
            - A pack with a layout.
            - The marketplace for which the item is prepared.
        When:
            - Preparing for upload.
        Then:
            - Verify a `Related Incidents` field's name is changed to `Related Alerts`
                if and only if marketpalce==marketplacev2 and group=="indicator"
        """
        from demisto_sdk.commands.content_graph.objects.layout import Layout
        from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser

        layout = pack.create_layoutcontainer(
            "TestLayoutscontainer", load_json("layoutscontainer.json")
        )
        model = Layout.from_orm(
            LayoutParser(Path(layout.path), list(MarketplaceVersions))
        )
        model.group = override_group
        ready_for_upload = model.prepare_for_upload(current_marketplace=marketplace)
        checked_dict = ready_for_upload["detailsV2"]["tabs"][5]

        # these two are for sanity, to make sure we're checking the right value (and the test file hasn't been changed)
        assert checked_dict["id"] == "relatedIncidents"
        assert checked_dict["type"] == "relatedIncidents"
        assert ("Alerts" in checked_dict["name"]) == (
            override_group == "indicator"
            and marketplace == MarketplaceVersions.MarketplaceV2
        )

    def test_list_parser(self, pack: Pack):
        """
        Given:
            - A pack with a list.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.list import List as ListObject
        from demisto_sdk.commands.content_graph.parsers.list import ListParser

        list_ = pack.create_list("TestList", load_json("list.json"))
        list_path = Path(list_.path)
        parser = ListParser(list_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = ListObject.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="checked integrations",
            expected_name="checked integrations",
            expected_path=list_path,
            expected_description="",
            expected_content_type=ContentType.LIST,
            expected_fromversion="6.5.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == "plain_text"

    def test_incoming_mapper_parser(self, pack: Pack):
        """
        Given:
            - A pack with an incoming mapper.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.mapper import Mapper
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser

        mapper = pack.create_mapper(
            "TestIncomingMapper", load_json("incoming_mapper.json")
        )
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "substringTo": ContentType.BASE_SCRIPT,
            },
            dependency_names={
                "DevSecOps New Git PR": ContentType.INCIDENT_TYPE,
                "DevSecOps Repository Name": ContentType.INCIDENT_FIELD,
                "DevSecOps Repository Organization": ContentType.INCIDENT_FIELD,
            },
        )
        model = Mapper.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="GitHub Mapper",
            expected_name="GitHub Mapper",
            expected_path=mapper_path,
            expected_description="",
            expected_content_type=ContentType.MAPPER,
            expected_fromversion="6.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == "mapping-incoming"

    def test_outgoing_mapper_parser(self, pack: Pack):
        """
        Given:
            - A pack with an outgoing mapper.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.mapper import Mapper
        from demisto_sdk.commands.content_graph.parsers.mapper import MapperParser

        mapper = pack.create_mapper(
            "TestOutgoingMapper", load_json("outgoing_mapper.json")
        )
        mapper_path = Path(mapper.path)
        parser = MapperParser(mapper_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "description": ContentType.INCIDENT_FIELD,
                "azuredevopsprojectname": ContentType.INCIDENT_FIELD,
                "MapValuesTransformer": ContentType.BASE_SCRIPT,
            },
            dependency_names={
                "Azure DevOps": ContentType.INCIDENT_TYPE,
            },
        )
        model = Mapper.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Azure DevOps Outgoing Mapper",
            expected_name="Azure DevOps Outgoing Mapper",
            expected_path=mapper_path,
            expected_description="",
            expected_content_type=ContentType.MAPPER,
            expected_fromversion="6.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == "mapping-outgoing"

    def test_modeling_rule_parser(self, pack: Pack):
        """
        Given:
            - A pack with a modeling rule.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.modeling_rule import (
            ModelingRule,
        )
        from demisto_sdk.commands.content_graph.parsers.modeling_rule import (
            ModelingRuleParser,
        )

        modeling_rule = pack.create_modeling_rule(
            "TestModelingRule", load_yaml("modeling_rule.yml")
        )
        modeling_rule_path = Path(modeling_rule.path)
        parser = ModelingRuleParser(modeling_rule_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = ModelingRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="duo_modeling_rule",
            expected_name="Duo Modeling Rule",
            expected_content_type=ContentType.MODELING_RULE,
            expected_fromversion="6.10.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_assets_modeling_rule_parser(self, pack: Pack):
        """
        Given:
            - A pack with an assets modeling rule.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.assets_modeling_rule import (
            AssetsModelingRule,
        )
        from demisto_sdk.commands.content_graph.parsers.assets_modeling_rule import (
            AssetsModelingRuleParser,
        )

        assets_modeling_rule = pack.create_assets_modeling_rule(
            "TestAssetsModelingRule"
        )
        modeling_rule_path = Path(assets_modeling_rule.path)
        parser = AssetsModelingRuleParser(modeling_rule_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = AssetsModelingRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="assets-modeling-rule",
            expected_name="Assets Modeling Rule",
            expected_content_type=ContentType.ASSETS_MODELING_RULE,
            expected_fromversion="6.8.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_parsing_rule_parser(self, pack: Pack):
        """
        Given:
            - A pack with a parsing rule.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
        from demisto_sdk.commands.content_graph.parsers.parsing_rule import (
            ParsingRuleParser,
        )

        parsing_rule = pack.create_parsing_rule(
            "TestParsingRule", load_yaml("parsing_rule.yml")
        )
        parsing_rule_path = Path(parsing_rule.path)
        parser = ParsingRuleParser(parsing_rule_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = ParsingRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="_parsing_rule_id",
            expected_name="My Rule",
            expected_content_type=ContentType.PARSING_RULE,
            expected_fromversion="6.10.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_playbook_parser(self, pack: Pack):
        """
        Given:
            - A pack with a playbook.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
              In particular, make sure redundant backslashes are removed from the playbook's description.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.playbook import Playbook
        from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser

        playbook = pack.create_playbook()
        playbook.create_default_playbook(name="sample")
        playbook.yml.update({"description": "test\\ test2\\\n \\  test3\n   - test4  "})
        playbook_path = Path(playbook.path)
        parser = PlaybookParser(playbook_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "DeleteContext": ContentType.BASE_SCRIPT,
            },
        )
        model = Playbook.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="sample",
            expected_name="sample",
            expected_content_type=ContentType.PLAYBOOK,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
            expected_description="test test2 test3\n   - test4 ",
        )
        assert not model.is_test

    def test_report_parser(self, pack: Pack):
        """
        Given:
            - A pack with a report.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.report import Report
        from demisto_sdk.commands.content_graph.parsers.report import ReportParser

        report = pack.create_report("TestReport", load_json("report.json"))
        report_path = Path(report.path)
        parser = ReportParser(report_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "ProofpointTAPMostAttackedUsers": ContentType.BASE_SCRIPT,
                "ProofpointTapTopClickers": ContentType.BASE_SCRIPT,
            },
        )
        model = Report.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="ProofpointTAPWeeklyReport",
            expected_name="Proofpoint TAP Weekly Report",
            expected_path=report_path,
            expected_content_type=ContentType.REPORT,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_script_parser(self, pack: Pack):
        """
        Given:
            - A pack with a script.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.script import Script
        from demisto_sdk.commands.content_graph.parsers.script import ScriptParser

        script = pack.create_script()
        script.create_default_script()
        script.code.write('demisto.executeCommand("dummy-command", dArgs)')
        script_path = Path(script.path)
        parser = ScriptParser(script_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            commands_or_scripts_executions=["dummy-command"],
        )
        model = Script.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="sample_script",
            expected_name="sample_script",
            expected_content_type=ContentType.SCRIPT,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.type == "python"
        assert model.subtype == "python3"
        assert model.docker_image == "demisto/python3:3.8.3.8715"
        assert model.tags == ["transformer"]
        assert not model.is_test
        assert not model.skip_prepare

    def test_test_playbook_parser(self, pack: Pack):
        """
        Given:
            - A pack with a test playbook.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.test_playbook import (
            TestPlaybook,
        )
        from demisto_sdk.commands.content_graph.parsers.test_playbook import (
            TestPlaybookParser,
        )

        test_playbook = pack.create_test_playbook()
        test_playbook.create_default_test_playbook(name="sample")
        test_playbook_path = Path(test_playbook.path)
        parser = TestPlaybookParser(test_playbook_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "DeleteContext": ContentType.BASE_SCRIPT,
            },
        )
        model = TestPlaybook.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="sample",
            expected_name="sample",
            expected_content_type=ContentType.TEST_PLAYBOOK,
            expected_fromversion="5.0.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert model.is_test

    def test_trigger_parser(self, pack: Pack):
        """
        Given:
            - A pack with a trigger.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.trigger import Trigger
        from demisto_sdk.commands.content_graph.parsers.trigger import TriggerParser

        trigger = pack.create_trigger("TestTrigger", load_json("trigger.json"))
        trigger_path = Path(trigger.path)
        parser = TriggerParser(trigger_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "NGFW Scan": ContentType.BASE_PLAYBOOK,
            },
        )
        model = Trigger.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="73545719a1bdeba6ba91f6a16044c021",
            expected_name="NGFW Scanning Alerts",
            expected_path=trigger_path,
            expected_content_type=ContentType.TRIGGER,
            expected_fromversion="6.10.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_layout_rule_parser(self, pack: Pack):
        """
        Given:
            - A pack with a layout rule.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule
        from demisto_sdk.commands.content_graph.parsers.layout_rule import (
            LayoutRuleParser,
        )

        rule = pack.create_layout_rule("rule_test")
        rule_path = Path(rule.path)
        parser = LayoutRuleParser(rule_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "test_layout": ContentType.LAYOUT,
            },
        )
        model = LayoutRule.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="rule_test",
            expected_name="rule_test.json",
            expected_path=rule_path,
            expected_content_type=ContentType.LAYOUT_RULE,
            expected_fromversion="6.10.0",
        )

    def test_widget_parser(self, pack: Pack):
        """
        Given:
            - A pack with a widget.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify all relationships of the content item are collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.widget import Widget
        from demisto_sdk.commands.content_graph.parsers.widget import WidgetParser

        widget = pack.create_widget("TestWidget", load_json("widget.json"))
        widget_path = Path(widget.path)
        parser = WidgetParser(widget_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            dependency_ids={
                "FeedIntegrationErrorWidget": ContentType.BASE_SCRIPT,
            },
        )
        model = Widget.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="Feed Integrations Errors",
            expected_name="Feed Integrations Errors",
            expected_path=widget_path,
            expected_content_type=ContentType.WIDGET,
            expected_fromversion="6.1.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )

    def test_wizard_parser(self, pack: Pack):
        """
        Given:
            - A pack with a wizard.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.wizard import Wizard
        from demisto_sdk.commands.content_graph.parsers.wizard import WizardParser

        wizard_json = load_json("wizard.json")
        wizard = pack.create_wizard(
            "TestWizard",
            categories_to_packs={
                c["name"]: c["packs"] for c in wizard_json["dependency_packs"]
            },
            fetching_integrations=[
                i["name"] for i in wizard_json["wizard"]["fetching_integrations"]
            ],
            set_playbooks=wizard_json["wizard"]["set_playbook"],
            supporting_integrations=[
                i["name"] for i in wizard_json["wizard"]["supporting_integrations"]
            ],
        )
        wizard_path = Path(wizard.path)
        parser = WizardParser(wizard_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = Wizard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="TestWizard",
            expected_name="TestWizard",
            expected_path=wizard_path,
            expected_content_type=ContentType.WIZARD,
            expected_fromversion="6.8.0",
            expected_toversion=DEFAULT_CONTENT_ITEM_TO_VERSION,
        )
        assert set(model.packs) == {
            "CrowdStrikeFalcon",
            "MicrosoftDefenderAdvancedThreatProtection",
            "CortexXDR",
        }
        assert set(model.integrations) == {
            "WildFire-v2",
            "Microsoft Defender Advanced Threat Protection",
        }
        assert set(model.playbooks) == {
            "Malware Investigation & Response Incident Handler"
        }

    def test_xsiam_dashboard_parser(self, pack: Pack):
        """
        Given:
            - A pack with an xsiam dashboard.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import (
            XSIAMDashboard,
        )
        from demisto_sdk.commands.content_graph.parsers.xsiam_dashboard import (
            XSIAMDashboardParser,
        )

        xsiam_dashboard = pack.create_xsiam_dashboard(
            "TestXSIAMDashboard", load_json("xsiam_dashboard.json")
        )
        xsiam_dashboard_path = Path(xsiam_dashboard.path)
        parser = XSIAMDashboardParser(xsiam_dashboard_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = XSIAMDashboard.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="ce27311ce69c41b1b4a84c7888b34852",
            expected_name="New Import test ",
            expected_path=xsiam_dashboard_path,
            expected_content_type=ContentType.XSIAM_DASHBOARD,
            expected_fromversion="8.1.0",
            expected_toversion="8.3.0",
        )

    def test_xsiam_report_parser(self, pack: Pack):
        """
        Given:
            - A pack with an xsiam report.
        When:
            - Creating the content item's parser and model.
        Then:
            - Verify no relationships were collected.
            - Verify the generic content item properties are parsed correctly.
            - Verify the specific properties of the content item are parsed correctly.
        """
        from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
        from demisto_sdk.commands.content_graph.parsers.xsiam_report import (
            XSIAMReportParser,
        )

        xsiam_report = pack.create_xsiam_report(
            "TestXSIAMReport", load_json("xsiam_report.json")
        )
        xsiam_report_path = Path(xsiam_report.path)
        parser = XSIAMReportParser(xsiam_report_path, list(MarketplaceVersions))
        assert not parser.relationships
        model = XSIAMReport.from_orm(parser)
        ContentItemModelVerifier.run(
            model,
            expected_id="sample",
            expected_name="sample",
            expected_path=xsiam_report_path,
            expected_content_type=ContentType.XSIAM_REPORT,
            expected_fromversion="8.1.0",
            expected_toversion="8.3.0",
        )

    def test_preprocess_parser(self):
        pre_process_rule = BaseContent.from_path(
            Path(
                f"{git_path()}/demisto_sdk/tests/test_files/content_slim/Packs/Sample01/PreProcessRules/preprocessrule-Drop.json"
            )
        )
        assert isinstance(pre_process_rule, PreProcessRule)
        assert pre_process_rule.name == "Drop"
        assert pre_process_rule.object_id == "preprocessrule-Drop-id"

    def test_pack_parser(self, mocker, repo: Repo):
        """
        Given:
            - A pack with several content items.
        When:
            - Creating the pack parser and model.
        Then:
            - Verify all pack's relationships from all its content items are collected.
            - Verify the content items are modeled correctly.
            - Verify the pack is modeled correctly.
        """
        from demisto_sdk.commands.content_graph.objects.pack import Pack as PackModel

        mocker.patch.object(tools, "get_content_path", return_value=Path(repo.path))

        pack = repo.create_pack("HelloWorld")
        pack.pack_metadata.write_json(load_json("pack_metadata.json"))
        pack.create_incident_field("sample", load_json("incident_field.json"))
        pack.create_incident_type("sample", load_json("incident_type.json"))
        pack.create_indicator_field("sample", load_json("indicator_field.json"))
        pack.create_indicator_type("sample", load_json("indicator_type.json"))

        pack.create_classifier("sample", load_json("classifier.json"))
        with open(f"{pack.path}/.pack-ignore", "w") as f:
            f.write("[file:classifier-sample.json]\nignore=SC100")

        pack_path = Path(pack.path)
        parser = PackParser(pack_path)
        expected_content_items = {
            "Github_Classifier_v1": ContentType.CLASSIFIER,
            "cve": ContentType.INCIDENT_FIELD,
            "Traps": ContentType.INCIDENT_TYPE,
            "email": ContentType.INDICATOR_FIELD,
            "urlRep": ContentType.INDICATOR_TYPE,
        }
        PackRelationshipsVerifier.run(
            parser.relationships,
            expected_content_items=expected_content_items,
        )
        model = PackModel.from_orm(parser)
        PackModelVerifier.run(
            model,
            expected_id="HelloWorld",
            expected_name="HelloWorld",
            expected_path=pack_path,
            expected_description="This is the Hello World integration for getting started.",
            expected_created="2020-03-10T08:37:18Z",
            expected_author_image="content/packs/HelloWorld/Author_image.png",
            expected_legacy=True,
            expected_eulaLink="https://github.com/demisto/content/blob/master/LICENSE",
            expected_support="community",
            expected_url="https://www.paloaltonetworks.com/cortex",
            expected_author="Cortex XSOAR",
            expected_certification="verified",
            expected_hidden=False,
            expected_current_version="1.2.12",
            expected_tags=["TIM"],
            expected_categories=["Utilities"],
            expected_use_cases=["Identity And Access Management"],
            expected_keywords=["common"],
            expected_marketplaces=[
                MarketplaceVersions.MarketplaceV2,
                MarketplaceVersions.XSOAR,
                MarketplaceVersions.XSOAR_SAAS,
            ],
            expected_content_items=expected_content_items,
            expected_deprecated=False,
        )

    def test_repo_parser(self, mocker, repo: Repo):
        """
        Given:
            - A repository with two packs.
        When:
            - Creating the repository parser and model.
        Then:
            - Verify the repository is modeled correctly.
        """
        from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
        from demisto_sdk.commands.content_graph.parsers.repository import (
            RepositoryParser,
        )

        pack1 = repo.create_pack("sample1")
        pack1.pack_metadata.write_json(load_json("pack_metadata.json"))
        pack2 = repo.create_pack("sample2")
        pack2.pack_metadata.write_json(load_json("pack_metadata.json"))
        mocker.patch.object(PackParser, "parse_ignored_errors", return_value={})
        parser = RepositoryParser(Path(repo.path))
        parser.parse()
        model = ContentDTO.from_orm(parser)
        pack_ids = {pack.object_id for pack in model.packs}
        assert pack_ids == {"sample1", "sample2"}

    def test_lazy_properties_in_the_model(self, mocker, pack):
        """
        Given:
            - an integration
        When:
            - creating integration model
        Then:
            - Verify that the lazy property (python_version) is not loaded into the model when parsing it
            - Verify that only when the lazy property (python_version) is called directly its added into the model
        """

        from packaging.version import Version

        from demisto_sdk.commands.content_graph.objects.integration import Integration
        from demisto_sdk.commands.content_graph.parsers.integration import (
            IntegrationParser,
        )

        expected_python_version = "3.10.11"
        mocker.patch(
            "demisto_sdk.commands.common.docker_helper._get_python_version_from_dockerhub_api",
            return_value=Version(expected_python_version),
        )

        integration = pack.create_integration(yml=load_yaml("integration.yml"))
        integration.code.write("from MicrosoftApiModule import *")
        integration.yml.update({"tests": ["test_playbook"]})

        integration_path = Path(integration.path)
        parser = IntegrationParser(integration_path, list(MarketplaceVersions))
        RelationshipsVerifier.run(
            parser.relationships,
            integration_commands=["test-command"],
            imports=["MicrosoftApiModule"],
            tests=["test_playbook"],
        )
        model = Integration.from_orm(parser)
        # make sure that the python_version is not in the model because it was not called directly
        assert "python_version" not in str(model)

        assert model.python_version == expected_python_version
        # make sure that only after we called directly to the lazy property of the model, its loaded into the model
        assert "python_version" in str(model)


class TestFindContentType:
    def test_integration_outside_content_path(self, git_repo):
        """
        Given:
            - An integration YAML file outside the content repository path.
        When:
            - Running from_path() on the integration YAML file.
        Then:
            - Verify that the returned Parser is IntegrationParser.
        """
        from demisto_sdk.commands.content_graph.parsers import IntegrationParser

        integration_python_str = "integration.py"
        integration_yaml_str = "integration.yml"
        integration_yaml_path = git_repo.path / Path(integration_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/integration.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=integration_yaml_str, file_content=content)
        git_repo.make_file(file_name=integration_python_str, file_content="Test")

        assert isinstance(
            ContentItemParser.from_path(Path(integration_yaml_path)), IntegrationParser
        )

    def test_integration_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An integration YAML file outside the content repository path.
        When:
            - Running by_schema() on the integration YAML file path, mocking the integration match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Integration

        integration_python_str = "integration.py"
        integration_yaml_str = "integration.yml"
        integration_yaml_path = git_repo.path / Path(integration_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/integration.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=integration_yaml_str, file_content=content)
        git_repo.make_file(file_name=integration_python_str, file_content="Test")
        mocker.patch.object(Integration, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(integration_yaml_path))

    def test_integration_outside_content_path_on_python_path(self, git_repo):
        """
        Given:
            - An integration Python and YAML files outside the content repository path.
        When:
            - Running from_path() on the integration Python file.
        Then:
            - Ensure InvaliadContentItemException is raised.
        """
        integration_python_str = "integration.py"
        integration_yaml_str = "integration.yml"
        integration_python_path = git_repo.path / Path(integration_python_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/integration.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=integration_yaml_str, file_content=content)
        git_repo.make_file(file_name=integration_python_str, file_content="Test")
        with pytest.raises(InvalidContentItemException):
            ContentItemParser.from_path(Path(integration_python_path))

    def test_integration_outside_content_path_missing_python_file(self, git_repo):
        """
        Given:
            - An integration YAML file outside the content repository path.
        When:
            - Running from_path() on the integration YAML file without existing Python file.
        Then:
            - Ensure InvaliadContentItemException is raised.
        """
        integration_yaml_str = "integration.yml"
        integration_yaml_path = git_repo.path / Path(integration_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/integration.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=integration_yaml_str, file_content=content)
        with pytest.raises(InvalidContentItemException):
            ContentItemParser.from_path(Path(integration_yaml_path))

    def test_script_outside_content_path(self, git_repo):
        """
        Given:
            - An script YAML file outside the content repository path.
        When:
            - Running from_path() on the script YAML file.
        Then:
            - Verify that the returned Parser is ScriptParser.
        """
        from demisto_sdk.commands.content_graph.parsers import ScriptParser

        script_python_str = "script.py"
        script_yaml_str = "script.yml"
        script_yaml_path = git_repo.path / Path(script_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/script.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=script_yaml_str, file_content=content)
        git_repo.make_file(file_name=script_python_str, file_content="Test")

        assert isinstance(
            ContentItemParser.from_path(Path(script_yaml_path)), ScriptParser
        )

    def test_script_outside_content_path_on_python_path(self, git_repo):
        """
        Given:
            - An script Python and YAML files outside the content repository path.
        When:
            - Running from_path() on the script Python file.
        Then:
            - Ensure InvaliadContentItemException is raised.
        """
        script_python_str = "script.py"
        script_yaml_str = "script.yml"
        script_python_path = git_repo.path / Path(script_python_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/script.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=script_yaml_str, file_content=content)
        git_repo.make_file(file_name=script_python_str, file_content="Test")
        with pytest.raises(InvalidContentItemException):
            ContentItemParser.from_path(Path(script_python_path))

    def test_script_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An script YAML file outside the content repository path.
        When:
            - Running by_schema() on the script YAML file path, mocking the script match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Script

        script_python_str = "script.py"
        script_yaml_str = "script.yml"
        script_yaml_path = git_repo.path / Path(script_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/script.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=script_yaml_str, file_content=content)
        git_repo.make_file(file_name=script_python_str, file_content="Test")
        mocker.patch.object(Script, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(script_yaml_path))

    def test_script_outside_content_path_missing_python_file(self, git_repo):
        """
        Given:
            - An script YAML file outside the content repository path.
        When:
            - Running from_path() on the script YAML file without existing Python file.
        Then:
            - Ensure InvaliadContentItemException is raised.
        """
        script_yaml_str = "script.yml"
        script_yaml_path = git_repo.path / Path(script_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/script.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=script_yaml_str, file_content=content)
        with pytest.raises(InvalidContentItemException):
            ContentItemParser.from_path(Path(script_yaml_path))

    def test_playbook_outside_content_path(self, git_repo):
        """
        Given:
            - An playbook YAML file outside the content repository path.
        When:
            - Running from_path() on the playbook YAML file.
        Then:
            - Verify that the returned Parser is PlaybookParser.
        """
        from demisto_sdk.commands.content_graph.parsers import PlaybookParser

        playbook_yaml_str = "playbook.yml"
        playbook_yaml_path = git_repo.path / Path(playbook_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/playbook.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=playbook_yaml_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(playbook_yaml_path)), PlaybookParser
        )

    def test_playbook_outside_content_path_on_read_me_path(self, git_repo):
        """
        Given:
            - An playbook ReadMe and YAML file outside the content repository path.
        When:
            - Running from_path() on the playbook ReadMe file.
        Then:
            - Ensure InvaliadContentItemException is raised.
        """
        playbook_read_me_str = "playbook.py"
        playbook_yaml_str = "playbook.yml"
        playbook_read_me_path = git_repo.path / Path(playbook_read_me_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/playbook.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=playbook_yaml_str, file_content=content)
        git_repo.make_file(file_name=playbook_read_me_str, file_content="Test")
        with pytest.raises(InvalidContentItemException):
            ContentItemParser.from_path(Path(playbook_read_me_path))

    def test_playbook_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An playbook YAML file outside the content repository path.
        When:
            - Running by_schema() on the playbook YAML file path, mocking the playbook match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Playbook

        playbook_read_me_str = "playbook.py"
        playbook_yaml_str = "playbook.yml"
        playbook_yaml_path = git_repo.path / Path(playbook_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/playbook.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=playbook_yaml_str, file_content=content)
        git_repo.make_file(file_name=playbook_read_me_str, file_content="Test")
        mocker.patch.object(Playbook, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(playbook_yaml_path))

    def test_correlation_rule_outside_content_path(self, git_repo):
        """
        Given:
            - An correlation rule YAML file outside the content repository path.
        When:
            - Running from_path() on the correlation rule YAML file.
        Then:
            - Verify that the returned Parser is CorrelationRuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import CorrelationRuleParser

        correlationrule_yml_str = "correlation_rule.yml"
        correlationrule_yml_path = git_repo.path / Path(correlationrule_yml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/correlation_rule.yml",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=correlationrule_yml_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(correlationrule_yml_path)),
            CorrelationRuleParser,
        )

    def test_correlation_rule_match_fails_on_other_content_types(
        self, mocker, git_repo
    ):
        """
        Given:
            - An correlation rule YAML file outside the content repository path.
        When:
            - Running by_schema() on the correlation rule YAML file path, mocking the correlation rule match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import CorrelationRule

        correlationrule_yml_str = "correlation_rule.yml"
        correlationrule_yml_path = git_repo.path / Path(correlationrule_yml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/correlation_rule.yml",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=correlationrule_yml_str, file_content=content)
        mocker.patch.object(CorrelationRule, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(correlationrule_yml_path))

    def test_classifier_outside_content_path(self, git_repo):
        """
        Given:
            - An classifier JSON file outside the content repository path.
        When:
            - Running from_path() on the classifier JSON file.
        Then:
            - Verify that the returned Parser is ClassifierParser.
        """
        from demisto_sdk.commands.content_graph.parsers import ClassifierParser

        classifier_json_str = "classifier.json"
        classifier_json_path = git_repo.path / Path(classifier_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/classifier.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=classifier_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(classifier_json_path)), ClassifierParser
        )

    def test_classifier_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An classifier JSON file outside the content repository path.
        When:
            - Running by_schema() on the classifier JSON file path, mocking the classifier match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Classifier

        classifier_json_str = "classifier.json"
        classifier_json_path = git_repo.path / Path(classifier_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/classifier.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=classifier_json_str, file_content=content)

        mocker.patch.object(Classifier, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(classifier_json_path))

    def test_dashboard_outside_content_path(self, git_repo):
        """
        Given:
            - An dashboard JSON file outside the content repository path.
        When:
            - Running from_path() on the dashboard JSON file.
        Then:
            - Verify that the returned Parser is DashboardParser.
        """
        from demisto_sdk.commands.content_graph.parsers import DashboardParser

        dashboard_json_str = "dashboard.json"
        dashboard_json_path = git_repo.path / Path(dashboard_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/dashboard.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=dashboard_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(dashboard_json_path)), DashboardParser
        )

    def test_dashboard_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An dashboard JSON file outside the content repository path.
        When:
            - Running by_schema() on the dashboard JSON file path, mocking the dashboard match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Dashboard

        dashboard_json_str = "dashboard.json"
        dashboard_json_path = git_repo.path / Path(dashboard_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/dashboard.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=dashboard_json_str, file_content=content)

        mocker.patch.object(Dashboard, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(dashboard_json_path))

    def test_generic_definition_outside_content_path(self, git_repo):
        """
        Given:
            - An generic definition JSON file outside the content repository path.
        When:
            - Running from_path() on the generic definition JSON file.
        Then:
            - Verify that the returned Parser is GenericDefinitionParser.
        """
        from demisto_sdk.commands.content_graph.parsers import GenericDefinitionParser

        generic_definition_json_str = "generic_definition.json"
        generic_definition_json_path = git_repo.path / Path(generic_definition_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_definition.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_definition_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(generic_definition_json_path)),
            GenericDefinitionParser,
        )

    def test_generic_definition_match_fails_on_other_content_types(
        self, mocker, git_repo
    ):
        """
        Given:
            - An generic definition JSON file outside the content repository path.
        When:
            - Running by_schema() on the generic definition JSON file path, mocking the generic definition match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import GenericDefinition

        generic_definition_json_str = "generic_definition.json"
        generic_definition_json_path = git_repo.path / Path(generic_definition_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_definition.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_definition_json_str, file_content=content)

        mocker.patch.object(GenericDefinition, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(generic_definition_json_path))

    def test_generic_field_outside_content_path(self, git_repo):
        """
        Given:
            - An generic field JSON file outside the content repository path.
        When:
            - Running from_path() on the generic field JSON file.
        Then:
            - Verify that the returned Parser is GenericFieldParser.
        """
        from demisto_sdk.commands.content_graph.parsers import GenericFieldParser

        generic_field_json_str = "generic_field.json"
        generic_field_json_path = git_repo.path / Path(generic_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_field.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_field_json_path, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(generic_field_json_path)),
            GenericFieldParser,
        )

    def test_generic_field_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An generic field JSON file outside the content repository path.
        When:
            - Running by_schema() on the generic field JSON file path, mocking the generic field match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import GenericField

        generic_field_json_str = "generic_field.json"
        generic_field_json_path = git_repo.path / Path(generic_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_field.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_field_json_str, file_content=content)

        mocker.patch.object(GenericField, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(generic_field_json_path))

    def test_generic_module_outside_content_path(self, git_repo):
        """
        Given:
            - An generic module JSON file outside the content repository path.
        When:
            - Running from_path() on the generic module JSON file.
        Then:
            - Verify that the returned Parser is GenericModuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import GenericModuleParser

        generic_module_json_str = "generic_module.json"
        generic_module_json_path = git_repo.path / Path(generic_module_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_module.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_module_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(generic_module_json_path)),
            GenericModuleParser,
        )

    def test_generic_module_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An generic module JSON file outside the content repository path.
        When:
            - Running by_schema() on the generic module JSON file path, mocking the generic module match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import GenericModule

        generic_module_json_str = "generic_module.json"
        generic_module_json_path = git_repo.path / Path(generic_module_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_module.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_module_json_str, file_content=content)

        mocker.patch.object(GenericModule, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(generic_module_json_path))

    def test_generic_type_outside_content_path(self, git_repo):
        """
        Given:
            - An generic type JSON file outside the content repository path.
        When:
            - Running from_path() on the generic type JSON file.
        Then:
            - Verify that the returned Parser is GenericModuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import GenericTypeParser

        generic_type_json_str = "generic_type.json"
        generic_type_json_path = git_repo.path / Path(generic_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_type.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_type_json_path, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(generic_type_json_path)),
            GenericTypeParser,
        )

    def test_generic_type_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An generic type JSON file outside the content repository path.
        When:
            - Running by_schema() on the generic type JSON file path, mocking the generic type match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import GenericType

        generic_type_json_str = "generic_type.json"
        generic_type_json_path = git_repo.path / Path(generic_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/generic_type.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=generic_type_json_path, file_content=content)

        mocker.patch.object(GenericType, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(generic_type_json_path))

    def test_incident_field_outside_content_path(self, git_repo):
        """
        Given:
            - An incident field JSON file outside the content repository path.
        When:
            - Running from_path() on the incident field JSON file.
        Then:
            - Verify that the returned Parser is IncidentFieldParser.
        """
        from demisto_sdk.commands.content_graph.parsers import IncidentFieldParser

        incident_field_json_str = "incident_field.json"
        incident_field_json_path = git_repo.path / Path(incident_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/incident_field.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=incident_field_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(incident_field_json_path)),
            IncidentFieldParser,
        )

    def test_incident_field_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An incident field JSON file outside the content repository path.
        When:
            - Running by_schema() on the incident field JSON file path, mocking the incident field match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import IncidentField

        incident_field_json_str = "incident_field.json"
        incident_field_json_path = git_repo.path / Path(incident_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/incident_field.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=incident_field_json_str, file_content=content)

        mocker.patch.object(IncidentField, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(incident_field_json_path))

    def test_incident_type_outside_content_path(self, git_repo):
        """
        Given:
            - An incident type JSON file outside the content repository path.
        When:
            - Running from_path() on the incident type JSON file.
        Then:
            - Verify that the returned Parser is IncidentTypeParser.
        """
        from demisto_sdk.commands.content_graph.parsers import IncidentTypeParser

        incident_type_json_str = "incident_type.json"
        incident_type_json_path = git_repo.path / Path(incident_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/incident_type.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=incident_type_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(incident_type_json_path)),
            IncidentTypeParser,
        )

    def test_incident_type_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An incident type JSON file outside the content repository path.
        When:
            - Running by_schema() on the incident type JSON file path, mocking the incident type match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import IncidentType

        incident_type_json_str = "incident_type.json"
        incident_type_json_path = git_repo.path / Path(incident_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/incident_type.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=incident_type_json_str, file_content=content)

        mocker.patch.object(IncidentType, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(incident_type_json_path))

    def test_indicator_field_outside_content_path(self, git_repo):
        """
        Given:
            - An indicator field JSON file outside the content repository path.
        When:
            - Running from_path() on the indicator field JSON file.
        Then:
            - Verify that the returned Parser is IndicatorFieldParser.
        """
        from demisto_sdk.commands.content_graph.parsers import IndicatorFieldParser

        indicator_field_json_str = "indicator_field.json"
        indicator_field_json_path = git_repo.path / Path(indicator_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/indicator_field.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=indicator_field_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(indicator_field_json_path)),
            IndicatorFieldParser,
        )

    def test_indicator_field_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An indicator field JSON file outside the content repository path.
        When:
            - Running by_schema() on the indicator field JSON file path, mocking the indicator field match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import IndicatorField

        indicator_field_json_str = "indicator_field.json"
        indicator_field_json_path = git_repo.path / Path(indicator_field_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/indicator_field.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=indicator_field_json_str, file_content=content)

        mocker.patch.object(IndicatorField, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(indicator_field_json_path))

    def test_indicator_type_outside_content_path(self, git_repo):
        """
        Given:
            - An indicator type JSON file outside the content repository path.
        When:
            - Running from_path() on the indicator type JSON file.
        Then:
            - Verify that the returned Parser is IndicatorTypeParser.
        """
        from demisto_sdk.commands.content_graph.parsers import IndicatorTypeParser

        indicator_type_json_str = "indicator_type.json"
        indicator_type_json_path = git_repo.path / Path(indicator_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/indicator_type.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=indicator_type_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(indicator_type_json_path)),
            IndicatorTypeParser,
        )

    def test_indicator_type_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An indicator type JSON file outside the content repository path.
        When:
            - Running by_schema() on the indicator type JSON file path, mocking the indicator type match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import IndicatorType

        indicator_type_json_str = "indicator_type.json"
        indicator_type_json_path = git_repo.path / Path(indicator_type_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/indicator_type.json",
            "r",
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=indicator_type_json_str, file_content=content)

        mocker.patch.object(IndicatorType, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(indicator_type_json_path))

    def test_layout_outside_content_path(self, git_repo):
        """
        Given:
            - An layout JSON file outside the content repository path.
        When:
            - Running from_path() on the layout JSON file.
        Then:
            - Verify that the returned Parser is LayoutParser.
        """
        from demisto_sdk.commands.content_graph.parsers import LayoutParser

        layout_json_str = "layout.json"
        layout_json_path = git_repo.path / Path(layout_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/layout.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=layout_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(layout_json_path)), LayoutParser
        )

    def test_layout_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An layout JSON file outside the content repository path.
        When:
            - Running by_schema() on the layout JSON file path, mocking the layout match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Layout

        layout_json_str = "layout.json"
        layout_json_path = git_repo.path / Path(layout_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/layout.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=layout_json_str, file_content=content)

        mocker.patch.object(Layout, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(layout_json_path))

    def test_layout_rule_outside_content_path(self, git_repo):
        """
        Given:
            - An layout rule JSON file outside the content repository path.
        When:
            - Running from_path() on the layout rule JSON file.
        Then:
            - Verify that the returned Parser is LayoutRuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import LayoutRuleParser

        layout_rule_json_str = "layout_rule.json"
        layout_rule_json_path = git_repo.path / Path(layout_rule_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/layout_rule.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=layout_rule_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(layout_rule_json_path)), LayoutRuleParser
        )

    def test_layout_rule_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An layout rule JSON file outside the content repository path.
        When:
            - Running by_schema() on the layout rule JSON file path, mocking the layout rule match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import LayoutRule

        layout_rule_json_str = "layout_rule.json"
        layout_rule_json_path = git_repo.path / Path(layout_rule_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/layout_rule.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=layout_rule_json_str, file_content=content)

        mocker.patch.object(LayoutRule, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(layout_rule_json_path))

    def test_mapper_outside_content_path(self, git_repo):
        """
        Given:
            - An mapper JSON file outside the content repository path.
        When:
            - Running from_path() on the mapper rule JSON file.
        Then:
            - Verify that the returned Parser is MapperParser.
        """
        from demisto_sdk.commands.content_graph.parsers import MapperParser

        mapper_json_str = "mapper.json"
        mapper_json_path = git_repo.path / Path(mapper_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/mapper.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=mapper_json_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(mapper_json_path)), MapperParser
        )

    def test_mapper_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An mapper JSON file outside the content repository path.
        When:
            - Running by_schema() on the mapper JSON file path, mocking the mapper match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import Mapper

        mapper_json_str = "mapper.json"
        mapper_json_path = git_repo.path / Path(mapper_json_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/mapper.json", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=mapper_json_str, file_content=content)

        mocker.patch.object(Mapper, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(mapper_json_path))

    def test_modeling_rule_outside_content_path(self, git_repo):
        """
        Given:
            - An modeling rule YAML file outside the content repository path.
        When:
            - Running from_path() on the modeling rule YAML file.
        Then:
            - Verify that the returned Parser is ModelingRuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import ModelingRuleParser

        modeling_rule_yaml_str = "modeling_rule.yml"
        modeling_rule_yaml_path = git_repo.path / Path(modeling_rule_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/modeling_rule.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=modeling_rule_yaml_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(modeling_rule_yaml_path)),
            ModelingRuleParser,
        )

    def test_modeling_rule_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An modeling rule JSON file outside the content repository path.
        When:
            - Running by_schema() on the modeling rule JSON file path, mocking the modeling rule match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import ModelingRule

        modeling_rule_yaml_str = "modeling_rule.yml"
        modeling_rule_yaml_path = git_repo.path / Path(modeling_rule_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/modeling_rule.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=modeling_rule_yaml_str, file_content=content)

        mocker.patch.object(ModelingRule, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(modeling_rule_yaml_path))

    def test_parsing_rule_outside_content_path(self, git_repo):
        """
        Given:
            - An parsing rule YAML file outside the content repository path.
        When:
            - Running from_path() on the parsing rule YAML file.
        Then:
            - Verify that the returned Parser is ParsingRuleParser.
        """
        from demisto_sdk.commands.content_graph.parsers import ParsingRuleParser

        parsing_rule_yaml_str = "parsing_rule.yml"
        parsing_rule_yaml_path = git_repo.path / Path(parsing_rule_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/parsing_rule.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=parsing_rule_yaml_str, file_content=content)

        assert isinstance(
            ContentItemParser.from_path(Path(parsing_rule_yaml_path)), ParsingRuleParser
        )

    def test_parsing_rule_match_fails_on_other_content_types(self, mocker, git_repo):
        """
        Given:
            - An parsing rule JSON file outside the content repository path.
        When:
            - Running by_schema() on the parsing rule JSON file path, mocking the parsing rule match method to False.
        Then:
            - Ensure other match() content types methods return False.
            - Ensure ValueError is raised.
        """
        from demisto_sdk.commands.content_graph.common import ContentType
        from demisto_sdk.commands.content_graph.objects import ParsingRule

        parsing_rule_yaml_str = "parsing_rule.yml"
        parsing_rule_yaml_path = git_repo.path / Path(parsing_rule_yaml_str)
        with open(
            "demisto_sdk/commands/content_graph/tests/test_data/parsing_rule.yml", "r"
        ) as f:
            content = f.read()
        git_repo.make_file(file_name=parsing_rule_yaml_str, file_content=content)
        mocker.patch.object(ParsingRule, "match", return_value=False)
        with pytest.raises(ValueError):
            ContentType.by_schema(Path(parsing_rule_yaml_path))


@pytest.mark.parametrize(
    "name,type_,expected_change",
    (
        ("Child Incidents", "childInv", True),
        ("Child Incident", "childInv", False),  # name should be Child Incidents
        ("", "childInv", False),
        ("Incidents", "", False),
        ("Linked Incidents", "linkedIncidents", True),
        (
            "Related Incidents",
            "linkedIncidents",
            False,
        ),  # type should be relatedIncidents
        ("Related Incidents", "relatedIncidents", True),
        ("Related Incidents", "", False),
        ("Related Incident", "relatedIncidents", False),
    ),
)
def test_fix_layout_incident_to_alert(
    name: str,
    type_: str,
    expected_change: bool,
):
    """
    Given:
        - A layout body
    When:
        - change_incident_to_alert is called
    Then:
        - Make sure it replaces values as expected
    """
    from demisto_sdk.commands.content_graph.objects.layout import (
        replace_layout_incident_alert,
    )

    expected_name = name.replace("Incident", "Alert") if expected_change else name

    assert replace_layout_incident_alert({"name": name, "type": type_}) == {
        "name": expected_name,
        "type": type_,
    }


@pytest.mark.parametrize(
    "marketplace, expected_market_place_set",
    [
        (
            {MarketplaceVersions.XSOAR},
            {MarketplaceVersions.XSOAR, MarketplaceVersions.XSOAR_SAAS},
        ),
        ({MarketplaceVersions.MarketplaceV2}, {MarketplaceVersions.MarketplaceV2}),
        ({MarketplaceVersions.XPANSE}, {MarketplaceVersions.XPANSE}),
        (
            {MarketplaceVersions.XSOAR_ON_PREM},
            {MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR},
        ),
        (
            {MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.XSOAR_SAAS},
            {
                MarketplaceVersions.XSOAR_ON_PREM,
                MarketplaceVersions.XSOAR_SAAS,
                MarketplaceVersions.XSOAR,
            },
        ),
        (
            {MarketplaceVersions.XSOAR_ON_PREM, MarketplaceVersions.MarketplaceV2},
            {
                MarketplaceVersions.XSOAR_ON_PREM,
                MarketplaceVersions.MarketplaceV2,
                MarketplaceVersions.XSOAR,
            },
        ),
        ({}, {}),
    ],
)
def test_updated_marketplaces_set(marketplace, expected_market_place_set):
    """
    Given:
        - XSOAR marketplace
        - XSIAM marketplace
        - XPANSE marketplace
        - XSOAR_ON_PREM marketplace
        - XSOAR_ON_PREM AND XSIAM
        - empty marketplace set

    When:
        - Parsing the content item to determine if the content item should enter the marketplace

    Then:
        - Check that XSOAR_SAAS was also added to the marketplace_set
        - Check the only XSAIM marketplace is on the list
        - Check the only XPANSE marketplace is on the list
        - Check that XSOAR_ON_PREM and XSOAR was added to the marketplace_set
        - Check that XSAIM remains and XSOAR marketplace is added
        - remains empty

    """
    from demisto_sdk.commands.content_graph.parsers.content_item import (
        ContentItemParser,
    )

    assert (
        expected_market_place_set
        == ContentItemParser.update_marketplaces_set_with_xsoar_values(marketplace)
    )


def test_argument_object__default_description():
    # validate that the 'description' attribute of the Argument object is set to an empty string by default
    from demisto_sdk.commands.content_graph.objects.integration_script import Argument

    arg = Argument(name="test")
    assert arg.description == ""


def test_output_object__default_description():
    # validate that the 'description' attribute of the Output object is set to an empty string by default
    from demisto_sdk.commands.content_graph.objects.integration import Output

    output = Output()
    assert output.description == ""


def test_parameter_object__default_type():
    # validate that the 'type' attribute of the Parameter object is set to 0 by default
    from demisto_sdk.commands.content_graph.objects.integration import Parameter

    param = Parameter(name="test")
    assert param.type == 0


def test_get_related_text_file():
    """
    Given
    - a pack content object with a readme file.

    When
    - calling the readme attribute.

    Then
    - Ensure that the readme content was returned.
    """
    pack = create_metadata_object(readme_text="This is a test")
    assert pack.readme.file_content == "This is a test"

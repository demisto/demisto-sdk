from pathlib import Path
from typing import Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    AGENTIX_ACTIONS_DIR,
    ASSETS_MODELING_RULES_DIR,
    CASE_FIELDS_DIR,
    CASE_LAYOUT_RULES_DIR,
    CASE_LAYOUTS_DIR,
    CORRELATION_RULES_DIR,
    DEFAULT_IMAGE_BASE64,
    LAYOUT_RULES_DIR,
    MODELING_RULES_DIR,
    PARSING_RULES_DIR,
    TRIGGER_DIR,
    XDRC_TEMPLATE_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
)
from TestSuite.agentix_action import AgentixAction
from TestSuite.case_field import CaseField
from TestSuite.case_layout import CaseLayout
from TestSuite.case_layout_rule import CaseLayoutRule
from TestSuite.classifier import Classifier
from TestSuite.content_list import ContentList
from TestSuite.correlation_rule import CorrelationRule
from TestSuite.dashboard import Dashboard
from TestSuite.file import File
from TestSuite.generic_definition import GenericDefinition
from TestSuite.generic_field import GenericField
from TestSuite.generic_module import GenericModule
from TestSuite.generic_type import GenericType
from TestSuite.incident_field import IncidentField
from TestSuite.incident_type import IncidentType
from TestSuite.indicator_field import IndicatorField
from TestSuite.indicator_type import IndicatorType
from TestSuite.integration import Integration
from TestSuite.job import Job
from TestSuite.json_based import JSONBased
from TestSuite.layout import Layout
from TestSuite.layout_rule import LayoutRule
from TestSuite.mapper import Mapper
from TestSuite.playbook import Playbook
from TestSuite.report import Report
from TestSuite.rule import Rule
from TestSuite.script import Script
from TestSuite.secrets import Secrets
from TestSuite.test_suite_base import TestSuiteBase
from TestSuite.test_tools import suite_join_path
from TestSuite.text_based import TextBased
from TestSuite.trigger import Trigger
from TestSuite.widget import Widget
from TestSuite.wizard import Wizard
from TestSuite.xdrc_template import XDRCTemplate
from TestSuite.xsiam_dashboard import XSIAMDashboard
from TestSuite.xsiam_report import XSIAMReport
from TestSuite.yml import YAML


class Pack(TestSuiteBase):
    """A class that mocks a pack inside to content repo

    Note:
        Do not include the `self` parameter in the ``Args`` section.

    Args:
        packs_dir: A Path to the root of Packs dir
        name: name of the pack to create

    Attributes:
        path (str): A path to the content pack.
        secrets (Secrets): Exception error code.
        integrations: A list contains any created integration
        scripts:  A list contains any created Script

    """

    def __init__(self, packs_dir: Path, name: str, repo):
        # Initiate lists:
        self.name = name
        self.object_id = name
        self.node_id = name
        self._repo = repo
        self.repo_path = repo.path
        self.integrations: List[Integration] = list()
        self.scripts: List[Script] = list()
        self.classifiers: List[Classifier] = list()
        self.mappers: List[Mapper] = list()
        self.dashboards: List[Dashboard] = list()
        self.incident_types: List[IncidentType] = list()
        self.incident_fields: List[IncidentField] = list()
        self.indicator_fields: List[IndicatorField] = list()
        self.indicator_types: List[IndicatorType] = list()
        self.generic_fields: List[GenericField] = list()
        self.generic_types: List[GenericType] = list()
        self.generic_modules: List[GenericModule] = list()
        self.generic_definitions: List[GenericDefinition] = list()
        self.layouts: List[Layout] = list()
        self.layoutcontainers: List[JSONBased] = list()
        self.reports: List[Report] = list()
        self.widgets: List[Widget] = list()
        self.lists: List[ContentList] = list()
        self.playbooks: List[Playbook] = list()
        self.test_playbooks: List[Playbook] = list()
        self.test_use_cases: List[TextBased] = list()
        self.release_notes: List[TextBased] = list()
        self.release_notes_config: List[JSONBased] = list()
        self.jobs: List[Job] = list()
        self.parsing_rules: List[Rule] = list()
        self.modeling_rules: List[Rule] = list()
        self.correlation_rules: List[YAML] = list()
        self.xsiam_dashboards: List[XSIAMDashboard] = list()
        self.xsiam_reports: List[XSIAMReport] = list()
        self.triggers: List[Trigger] = list()
        self.wizards: List[Wizard] = list()
        self.xdrc_templates: List[XDRCTemplate] = list()
        self.layout_rules: List[LayoutRule] = list()
        self.assets_modeling_rules: List[Rule] = list()
        self.case_fields: List[CaseField] = list()
        self.case_layouts: List[CaseLayout] = list()
        self.case_layout_rules: List[CaseLayoutRule] = list()
        self.agentix_actions: List[AgentixAction] = list()

        self.agentix_actions: List[AgentixAction] = list()

        # Create base pack
        self._pack_path = packs_dir / self.name
        self._pack_path.mkdir(exist_ok=True)
        self.path = self._pack_path

        # Create repo structure
        self._integrations_path = self._pack_path / "Integrations"
        self._integrations_path.mkdir(exist_ok=True)

        self._scripts_path = self._pack_path / "Scripts"
        self._scripts_path.mkdir(exist_ok=True)

        self._playbooks_path = self._pack_path / "Playbooks"
        self._playbooks_path.mkdir(exist_ok=True)

        self._test_playbooks_path = self._pack_path / "TestPlaybooks"
        self._test_playbooks_path.mkdir(exist_ok=True)

        self._test_use_cases_path = self._pack_path / "TestUseCases"
        self._test_use_cases_path.mkdir(exist_ok=True)

        self._classifiers_path = self._pack_path / "Classifiers"
        self._classifiers_path.mkdir(exist_ok=True)

        self._mappers_path = self._classifiers_path

        self._dashboards_path = self._pack_path / "Dashboards"
        self._dashboards_path.mkdir(exist_ok=True)

        self._incidents_field_path = self._pack_path / "IncidentFields"
        self._incidents_field_path.mkdir(exist_ok=True)

        self._incident_types_path = self._pack_path / "IncidentTypes"
        self._incident_types_path.mkdir(exist_ok=True)

        self._indicator_fields = self._pack_path / "IndicatorFields"
        self._indicator_fields.mkdir(exist_ok=True)

        self._indicator_types = self._pack_path / "IndicatorTypes"
        self._indicator_types.mkdir(exist_ok=True)

        self._generic_fields_path = self._pack_path / "GenericFields"
        self._generic_fields_path.mkdir(exist_ok=True)

        self._generic_types_path = self._pack_path / "GenericTypes"
        self._generic_types_path.mkdir(exist_ok=True)

        self._generic_modules_path = self._pack_path / "GenericModules"
        self._generic_modules_path.mkdir(exist_ok=True)

        self._generic_definitions_path = self._pack_path / "GenericDefinitions"
        self._generic_definitions_path.mkdir(exist_ok=True)

        self._layout_path = self._pack_path / "Layouts"
        self._layout_path.mkdir(exist_ok=True)

        self._report_path = self._pack_path / "Reports"
        self._report_path.mkdir(exist_ok=True)

        self._widget_path = self._pack_path / "Widgets"
        self._widget_path.mkdir(exist_ok=True)

        self._wizard_path = self._pack_path / "Wizards"
        self._wizard_path.mkdir(exist_ok=True)

        self._release_notes = self._pack_path / "ReleaseNotes"
        self._release_notes.mkdir(exist_ok=True)

        self._lists_path = self._pack_path / "Lists"
        self._lists_path.mkdir(exist_ok=True)

        self._parsing_rules_path = self._pack_path / PARSING_RULES_DIR
        self._parsing_rules_path.mkdir(exist_ok=True)

        self._modeling_rules_path = self._pack_path / MODELING_RULES_DIR
        self._modeling_rules_path.mkdir(exist_ok=True)

        self._correlation_rules_path = self._pack_path / CORRELATION_RULES_DIR
        self._correlation_rules_path.mkdir(exist_ok=True)

        self._xsiam_dashboards_path = self._pack_path / XSIAM_DASHBOARDS_DIR
        self._xsiam_dashboards_path.mkdir(exist_ok=True)

        self._xsiam_reports_path = self._pack_path / XSIAM_REPORTS_DIR
        self._xsiam_reports_path.mkdir(exist_ok=True)

        self._triggers_path = self._pack_path / TRIGGER_DIR
        self._triggers_path.mkdir(exist_ok=True)

        self._xdrc_templates_path = self._pack_path / XDRC_TEMPLATE_DIR
        self._xdrc_templates_path.mkdir(exist_ok=True)

        self.secrets = Secrets(self._pack_path)

        self.pack_ignore = TextBased(self._pack_path, ".pack-ignore")

        self.readme = TextBased(self._pack_path, "README.md")

        self.pack_metadata = JSONBased(self._pack_path, "pack_metadata", "")
        self.pack_metadata.update(
            {
                "name": self.name,
                "description": "here be description",
                "support": "xsoar",
                "url": "https://paloaltonetworks.com",
                "author": "Cortex XSOAR",
                "currentVersion": "1.0.0",
                "tags": [],
                "categories": [],
                "useCases": [],
                "keywords": [],
            }
        )
        self.version_config = JSONBased(self._pack_path, "version_config", "")
        self.author_image = File(
            tmp_path=self._pack_path / "Author_image.png", repo_path=repo.path
        )
        self.author_image.write(DEFAULT_IMAGE_BASE64)

        self._jobs_path = self._pack_path / "Jobs"
        self._jobs_path.mkdir(exist_ok=True)

        self._xsiam_layout_rules_path = self._pack_path / LAYOUT_RULES_DIR
        self._xsiam_layout_rules_path.mkdir(exist_ok=True)

        self._case_layout_rules_path = self._pack_path / CASE_LAYOUT_RULES_DIR
        self._case_layout_rules_path.mkdir(exist_ok=True)

        self._case_layouts_path = self._pack_path / CASE_LAYOUTS_DIR
        self._case_layouts_path.mkdir(exist_ok=True)

        self._case_fields_path = self._pack_path / CASE_FIELDS_DIR
        self._case_fields_path.mkdir(exist_ok=True)

        self.contributors: Optional[TextBased] = None

        self._assets_modeling_rules_path = self._pack_path / ASSETS_MODELING_RULES_DIR
        self._assets_modeling_rules_path.mkdir(exist_ok=True)

        self._agentix_actions_path = self._pack_path / AGENTIX_ACTIONS_DIR

        super().__init__(self._pack_path)

    def create_integration(
        self,
        name: Optional[str] = None,
        code: Optional[str] = None,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
        description: Optional[str] = None,
        changelog: Optional[str] = None,
        image: Optional[bytes] = None,
        docker_image: Optional[str] = None,
        create_unified=False,
        commands_txt: Optional[str] = None,
        test: Optional[str] = None,
        unit_test_name: Optional[str] = None,
    ) -> Integration:
        if name is None:
            name = f"integration_{len(self.integrations)}"
        if yml is None:
            yml = {
                "commonfields": {"id": name, "version": -1},
                "name": name,
                "display": name,
                "description": description or f"this is an integration {name}",
                "category": "category",
                "script": {
                    "type": "python",
                    "subtype": "python3",
                    "script": "",
                    "commands": [],
                    "dockerimage": docker_image,
                },
                "configuration": [],
            }
        if image is None:
            with open(
                suite_join_path("assets/default_integration", "sample_image.png"), "rb"
            ) as image_file:
                image = image_file.read()
        integration = Integration(
            self._integrations_path,
            name,
            self._repo,
            create_unified=create_unified,
            _type=yml.get("script", {}).get("type", "python"),
            unit_test_name=unit_test_name,
        )
        integration.build(
            code, yml, readme, description, changelog, image, commands_txt, test
        )
        self.integrations.append(integration)
        return integration

    def create_script(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        code: Optional[str] = None,
        readme: str = "",
        description: str = "",
        changelog: str = "",
        image: bytes = b"",
        docker_image: Optional[str] = None,
        create_unified=False,
        skip_prepare=[],
    ) -> Script:
        if name is None:
            name = f"script{len(self.scripts)}"
        if yml is None:
            yml = {
                "commonfields": {"id": name, "version": -1},
                "name": name,
                "comment": f"this is script {name}",
                "type": "python",
                "subtype": "python3",
                "dockerimage": docker_image,
                "script": "-",
                "skipprepare": skip_prepare,
            }
        script = Script(
            self._scripts_path,
            name,
            self._repo,
            create_unified=create_unified,
            _type=yml.get("type", "python"),
        )
        script.build(code, yml, readme, description, changelog, image)
        self.scripts.append(script)
        return script

    def create_test_script(self) -> Script:
        script = self.create_script("sample_script")
        script.create_default_script()
        return script

    def _create_json_based(
        self, name, prefix: str, content: dict = None, dir_path: Path = None
    ) -> JSONBased:
        if content is None:
            content = {}
        if dir_path:
            obj = JSONBased(dir_path, name, prefix)
        else:
            obj = JSONBased(self._pack_path, name, prefix)
        obj.write_json(content)
        return obj

    def _create_yaml_based(
        self,
        name,
        dir_path,
        content: dict = {},
    ) -> YAML:
        yaml_name = f"{name}.yml"
        yaml_path = Path(dir_path, yaml_name)
        obj = YAML(yaml_path, self.repo_path)
        obj.write_dict(content)
        return obj

    def _create_text_based(
        self, name, content: str = "", dir_path: Path = None
    ) -> TextBased:
        if dir_path:
            obj = TextBased(dir_path, name)
        else:
            obj = TextBased(self._pack_path, name)
        obj.write_text(content)
        return obj

    def create_classifier(self, name: str = None, content: dict = None) -> Classifier:
        if not name:
            name = f"classifier{len(self.classifiers)}"
        classifier = Classifier(name, self._classifiers_path, content)
        self.classifiers.append(classifier)
        return classifier

    def create_mapper(self, name: str = None, content: dict = None) -> Mapper:
        if not name:
            name = f"classifier-mapper{len(self.mappers)}"
        mapper = Mapper(name, self._mappers_path, content)
        self.mappers.append(mapper)
        return mapper

    def create_dashboard(self, name: str = None, content: dict = None) -> Dashboard:
        if not name:
            name = f"dashboard{len(self.dashboards)}"
        dashboard = Dashboard(name, self._dashboards_path, content)
        self.dashboards.append(dashboard)
        return dashboard

    def create_incident_field(
        self, name: str = None, content: dict = None
    ) -> IncidentField:
        if not name:
            name = f"incidentfield{len(self.incident_fields)}"
        incident_field = IncidentField(name, self._incidents_field_path, content)

        self.incident_fields.append(incident_field)
        return incident_field

    def create_incident_type(
        self, name: str = None, content: dict = None
    ) -> IncidentType:
        if not name:
            name = f"incidenttype{len(self.incident_types)}"
        incident_type = IncidentType(name, self._incident_types_path, content)
        self.incident_types.append(incident_type)
        return incident_type

    def create_indicator_field(
        self, name: str = None, content: dict = None
    ) -> IndicatorField:
        if not name:
            name = f"indicatorfield{len(self.indicator_fields)}"
        indicator_field = IndicatorField(name, self._indicator_fields, content)
        self.indicator_fields.append(indicator_field)
        return indicator_field

    def create_indicator_type(
        self, name: str = None, content: dict = None
    ) -> IndicatorType:
        if not name:
            name = f"reputation{len(self.indicator_types)}"
        indicator_type = IndicatorType(name, self._indicator_types, content)
        self.indicator_types.append(indicator_type)
        return indicator_type

    def create_generic_field(self, name, content: dict = None) -> GenericField:
        dir_path = self._generic_fields_path / name
        dir_path.mkdir()
        generic_field = GenericField(name, dir_path, content)
        self.generic_fields.append(generic_field)
        return generic_field

    def create_generic_type(self, name, content: dict = None) -> GenericType:
        dir_path = self._generic_types_path / name
        dir_path.mkdir()
        generic_type = GenericType(name, dir_path, content)
        self.generic_types.append(generic_type)
        return generic_type

    def create_generic_module(
        self, name: str = None, content: dict = None
    ) -> GenericModule:
        if not name:
            name = f"genericmodule{len(self.generic_modules)}"

        generic_module = GenericModule(name, self._generic_modules_path, content)
        self.generic_modules.append(generic_module)
        return generic_module

    def create_generic_definition(
        self, name: str = None, content: dict = None
    ) -> GenericDefinition:
        if not name:
            name = f"genericdefinition{len(self.generic_definitions)}"
        generic_definition = GenericDefinition(
            name, self._generic_definitions_path, content
        )
        self.generic_definitions.append(generic_definition)
        return generic_definition

    def create_job(
        self,
        is_feed: bool,
        name: Optional[str] = None,
        selected_feeds: Optional[List[str]] = None,
        details: str = "",
    ) -> Job:
        job = Job(
            pure_name=name or f"job{len(self.jobs)}",
            jobs_dir_path=self._jobs_path,
            is_feed=is_feed,
            selected_feeds=selected_feeds,
            details=details,
        )
        self.create_playbook(name=job.playbook_name).create_default_playbook(
            name=job.playbook_name
        )
        self.jobs.append(job)
        return job

    def create_layout(self, name: str = None, content: dict = None) -> Layout:
        if not name:
            name = f"layout{len(self.layouts)}"
        layout = Layout(name, self._layout_path, content)
        self.layouts.append(layout)
        return layout

    def create_layoutcontainer(self, name, content: Optional[dict] = None) -> JSONBased:
        if not content:
            content = {"group": "default"}
        prefix = "layoutscontainer"
        layoutcontainer = self._create_json_based(
            name, prefix, content, dir_path=self._layout_path
        )
        self.layoutcontainers.append(layoutcontainer)
        return layoutcontainer

    def create_report(self, name: str = None, content: dict = None) -> Report:
        if not name:
            name = f"report{len(self.reports)}"
        report = Report(name, self._report_path, content)
        self.reports.append(report)
        return report

    def create_widget(self, name: str = None, content: dict = None) -> Widget:
        if not name:
            name = f"widget{len(self.widgets)}"

        widget = Widget(name, self._widget_path, content)
        self.widgets.append(widget)
        return widget

    def create_wizard(
        self,
        name: str = None,
        categories_to_packs: Optional[Dict[str, List[dict]]] = None,
        fetching_integrations: Optional[List[str]] = None,
        set_playbooks: Optional[List[dict]] = None,
        supporting_integrations: Optional[List[str]] = None,
    ) -> Wizard:
        if name is None:
            name = f"wizard{len(self.wizards)}"
        wizard = Wizard(
            name=name,
            wizards_dir_path=self._wizard_path,
            categories_to_packs=categories_to_packs,
            fetching_integrations=fetching_integrations,
            set_playbooks=set_playbooks,
            supporting_integrations=supporting_integrations,
        )
        if not all(
            [
                categories_to_packs,
                fetching_integrations,
                set_playbooks,
                supporting_integrations,
            ]
        ):
            wizard.set_default_wizard_values()
        wizard.create_wizard()
        self.wizards.append(wizard)
        return wizard

    def create_list(self, name: str = None, content: dict = None) -> ContentList:
        if not name:
            name = f"list{len(self.lists)}"
        content_list = ContentList(name, self._lists_path, content)
        self.lists.append(content_list)
        return content_list

    def create_playbook(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
    ) -> Playbook:
        if name is None:
            name = f"playbook-{len(self.playbooks)}"
        playbook = Playbook(self._playbooks_path, name, self._repo)
        playbook.build(
            yml,
            readme,
        )
        self.playbooks.append(playbook)
        return playbook

    def create_test_playbook(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
        changelog: Optional[str] = None,
    ) -> Playbook:
        if name is None:
            name = f"playbook-{len(self.test_playbooks)}"
        playbook = Playbook(
            self._test_playbooks_path, name, self._repo, is_test_playbook=True
        )
        playbook.build(
            yml,
            readme,
        )
        self.test_playbooks.append(playbook)
        return playbook

    def create_test_use_case(self, name: str, content: str = ""):
        pb_test_use_case = self._create_text_based(
            f"{name}.py", content, dir_path=self._test_use_cases_path
        )
        self.test_use_cases.append(pb_test_use_case)
        return pb_test_use_case

    def create_release_notes(
        self, version: str, content: str = "", is_bc: bool = False
    ):
        rn = self._create_text_based(
            f"{version}.md", content, dir_path=self._release_notes
        )
        self.release_notes.append(rn)
        if is_bc:
            self.create_release_notes_config(version, {"breakingChanges": True})
        return rn

    def create_release_notes_config(self, version: str, content: dict):
        rn_config = self._create_json_based(
            f"{version}", "", content, dir_path=self._release_notes
        )
        self.release_notes_config.append(rn_config)
        return rn_config

    def create_doc_file(self, name: str = "image") -> File:
        doc_file_dir = self._pack_path / "doc_files"
        doc_file_dir.mkdir()
        return File(doc_file_dir / f"{name}.png", self._repo.path)

    def create_contributors_file(self, content) -> TextBased:
        contributors = self._create_text_based("CONTRIBUTORS.json", content)
        self.contributors = contributors
        return contributors

    def create_parsing_rule(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        rules: Optional[str] = None,
        samples: Optional[list] = None,
    ) -> Rule:
        if not name:
            name = f"parsingrule_{len(self.parsing_rules)}"
        if not yml:
            yml = {
                "id": "parsing-rule",
                "name": "Parsing Rule",
                "fromversion": "6.8.0",
                "tags": ["tag"],
                "rules": "",
                "samples": "",
            }
        if not rules:
            rules = '[INGEST:vendor="vendor", product="product", target_dataset="dataset", no_hit=drop]'

        rule = Rule(
            tmpdir=self._parsing_rules_path,
            name=name,
            repo=self._repo,
        )
        rule.build(
            yml=yml,
            rules=rules,
            samples=samples,
        )
        self.parsing_rules.append(rule)
        return rule

    def create_modeling_rule(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        rules: Optional[str] = None,
        schema: Optional[dict] = None,
    ) -> Rule:
        if not name:
            name = f"modelingrule_{len(self.modeling_rules)}"
        if not yml:
            yml = {
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.8.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        if not rules:
            rules = '[MODEL: dataset="dataset", model="Model", version=0.1]'

        if not schema:
            schema = {"test_audit_raw": {"name": {"type": "string", "is_array": False}}}

        rule = Rule(
            tmpdir=self._modeling_rules_path,
            name=name,
            repo=self._repo,
        )
        rule.build(yml=yml, rules=rules, schema=schema)
        self.modeling_rules.append(rule)
        return rule

    def create_assets_modeling_rule(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        rules: Optional[str] = None,
        schema: Optional[dict] = None,
    ) -> Rule:
        if not name:
            name = f"assetsmodelingrule_{len(self.assets_modeling_rules)}"
        if not yml:
            yml = {
                "id": "assets-modeling-rule",
                "name": "Assets Modeling Rule",
                "fromversion": "6.8.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        if not rules:
            rules = '[MODEL: dataset="assets_dataset", model="Model", version=0.1]'

        if not schema:
            schema = {
                "test_assets_audit_raw": {"name": {"type": "string", "is_array": False}}
            }

        rule = Rule(
            tmpdir=self._assets_modeling_rules_path,
            name=name,
            repo=self._repo,
        )
        rule.build(yml=yml, rules=rules, schema=schema)
        self.assets_modeling_rules.append(rule)
        return rule

    def create_correlation_rule(
        self, name: str = None, content: dict = None
    ) -> CorrelationRule:
        if not name:
            name = f"correlationrule{len(self.correlation_rules)}"
        correlation_rule = CorrelationRule(
            name, self._correlation_rules_path, self.repo_path, content
        )
        self.correlation_rules.append(correlation_rule)
        return correlation_rule

    def create_xsiam_dashboard(
        self, name: str = None, content: dict = None
    ) -> XSIAMDashboard:
        if not name:
            name = f"XSIAMDashboard{len(self.xsiam_dashboards)}"
        xsiam_dashboard = XSIAMDashboard(name, self._xsiam_dashboards_path, content)
        self.xsiam_dashboards.append(xsiam_dashboard)
        return xsiam_dashboard

    def create_xsiam_report(
        self, name: str = None, content: dict = None
    ) -> XSIAMReport:
        if not name:
            name = f"XSIAMReport{len(self.xsiam_reports)}"
        xsiam_report = XSIAMReport(name, self._xsiam_reports_path, content)
        self.xsiam_reports.append(xsiam_report)
        return xsiam_report

    def create_trigger(self, name: str = None, content: dict = None) -> Trigger:
        if not name:
            name = f"trigger_{len(self.triggers)}"
        trigger = Trigger(name, self._triggers_path, content)
        self.triggers.append(trigger)
        return trigger

    def create_xdrc_template(
        self, name, json_content: dict = None, yaml_content: dict = None
    ) -> XDRCTemplate:
        xdrc_template_dir: Path = self._xdrc_templates_path / f"{self.name}_{name}"
        xdrc_template_dir.mkdir()
        xdrc_template = XDRCTemplate(
            name, xdrc_template_dir, json_content, yaml_content
        )
        self.xdrc_templates.append(xdrc_template)
        return xdrc_template

    def create_layout_rule(self, name: str = None, content: dict = None) -> LayoutRule:
        if not name:
            name = f"layout_rule{len(self.layout_rules)}"
        layout_rule = LayoutRule(name, self._xsiam_layout_rules_path, content)
        self.layout_rules.append(layout_rule)
        return layout_rule

    def create_case_layout_rule(
        self, name: str = None, content: dict = None
    ) -> CaseLayoutRule:
        if not name:
            name = f"case_layout_rule{len(self.case_layout_rules)}"
        case_layout_rule = CaseLayoutRule(name, self._case_layout_rules_path, content)
        self.case_layout_rules.append(case_layout_rule)
        return case_layout_rule

    def create_case_layout(self, name: str = None, content: dict = None) -> CaseLayout:
        if not name:
            name = f"case_layout{len(self.case_layouts)}"
        case_layout = CaseLayout(name, self._case_layouts_path, content)
        self.case_layouts.append(case_layout)
        return case_layout

    def create_case_field(self, name: str = None, content: dict = None) -> CaseField:
        if not name:
            name = f"casefield{len(self.incident_fields)}"
        case_field = CaseField(name, self._case_fields_path, content)

        self.case_fields.append(case_field)
        return case_field

    def set_data(self, **key_path_to_val):
        self.pack_metadata.set_data(**key_path_to_val)

    def create_agentix_action(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
    ) -> AgentixAction:
        if name is None:
            name = f"agentix_action-{len(self.agentix_actions)}"
        agentix_action = AgentixAction(self._agentix_actions_path, name, self._repo)
        agentix_action.build(
            yml,
        )
        self.agentix_actions.append(agentix_action)
        return agentix_action

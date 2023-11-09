from pathlib import Path
from typing import Dict, List, Optional

from demisto_sdk.commands.common.constants import (
    ASSETS_MODELING_RULES_DIR,
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
from TestSuite.correlation_rule import CorrelationRule
from TestSuite.file import File
from TestSuite.integration import Integration
from TestSuite.job import Job
from TestSuite.json_based import JSONBased
from TestSuite.layout_rule import LayoutRule
from TestSuite.playbook import Playbook
from TestSuite.rule import Rule
from TestSuite.script import Script
from TestSuite.secrets import Secrets
from TestSuite.test_tools import suite_join_path
from TestSuite.text_based import TextBased
from TestSuite.trigger import Trigger
from TestSuite.wizard import Wizard
from TestSuite.xdrc_template import XDRCTemplate
from TestSuite.xsiam_dashboard import XSIAMDashboard
from TestSuite.xsiam_report import XSIAMReport
from TestSuite.yml import YAML


class Pack:
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
        self._repo = repo
        self.repo_path = repo.path
        self.integrations: List[Integration] = list()
        self.scripts: List[Script] = list()
        self.classifiers: List[JSONBased] = list()
        self.mappers: List[JSONBased] = list()
        self.dashboards: List[JSONBased] = list()
        self.incident_types: List[JSONBased] = list()
        self.incident_fields: List[JSONBased] = list()
        self.indicator_fields: List[JSONBased] = list()
        self.indicator_types: List[JSONBased] = list()
        self.generic_fields: List[JSONBased] = list()
        self.generic_types: List[JSONBased] = list()
        self.generic_modules: List[JSONBased] = list()
        self.generic_definitions: List[JSONBased] = list()
        self.layouts: List[JSONBased] = list()
        self.layoutcontainers: List[JSONBased] = list()
        self.reports: List[JSONBased] = list()
        self.widgets: List[JSONBased] = list()
        self.lists: List[JSONBased] = list()
        self.playbooks: List[Playbook] = list()
        self.test_playbooks: List[Playbook] = list()
        self.release_notes: List[TextBased] = list()
        self.release_notes_config: List[JSONBased] = list()
        self.jobs: List[Job] = list()
        self.parsing_rules: List[Rule] = list()
        self.modeling_rules: List[Rule] = list()
        self.correlation_rules: List[YAML] = list()
        self.xsiam_dashboards: List[JSONBased] = list()
        self.xsiam_reports: List[JSONBased] = list()
        self.triggers: List[JSONBased] = list()
        self.wizards: List[Wizard] = list()
        self.xdrc_templates: List[XDRCTemplate] = list()
        self.layout_rules: List[LayoutRule] = list()
        self.assets_modeling_rules: List[Rule] = list()

        # Create base pack
        self._pack_path = packs_dir / self.name
        self._pack_path.mkdir()
        self.path = str(self._pack_path)

        # Create repo structure
        self._integrations_path = self._pack_path / "Integrations"
        self._integrations_path.mkdir()

        self._scripts_path = self._pack_path / "Scripts"
        self._scripts_path.mkdir()

        self._playbooks_path = self._pack_path / "Playbooks"
        self._playbooks_path.mkdir()

        self._test_playbooks_path = self._pack_path / "TestPlaybooks"
        self._test_playbooks_path.mkdir()

        self._classifiers_path = self._pack_path / "Classifiers"
        self._classifiers_path.mkdir()

        self._mappers_path = self._classifiers_path

        self._dashboards_path = self._pack_path / "Dashboards"
        self._dashboards_path.mkdir()

        self._incidents_field_path = self._pack_path / "IncidentFields"
        self._incidents_field_path.mkdir()

        self._incident_types_path = self._pack_path / "IncidentTypes"
        self._incident_types_path.mkdir()

        self._indicator_fields = self._pack_path / "IndicatorFields"
        self._indicator_fields.mkdir()

        self._indicator_types = self._pack_path / "IndicatorTypes"
        self._indicator_types.mkdir()

        self._generic_fields_path = self._pack_path / "GenericFields"
        self._generic_fields_path.mkdir()

        self._generic_types_path = self._pack_path / "GenericTypes"
        self._generic_types_path.mkdir()

        self._generic_modules_path = self._pack_path / "GenericModules"
        self._generic_modules_path.mkdir()

        self._generic_definitions_path = self._pack_path / "GenericDefinitions"
        self._generic_definitions_path.mkdir()

        self._layout_path = self._pack_path / "Layouts"
        self._layout_path.mkdir()

        self._report_path = self._pack_path / "Reports"
        self._report_path.mkdir()

        self._widget_path = self._pack_path / "Widgets"
        self._widget_path.mkdir()

        self._wizard_path = self._pack_path / "Wizards"
        self._wizard_path.mkdir()

        self._release_notes = self._pack_path / "ReleaseNotes"
        self._release_notes.mkdir()

        self._lists_path = self._pack_path / "Lists"
        self._lists_path.mkdir()

        self._parsing_rules_path = self._pack_path / PARSING_RULES_DIR
        self._parsing_rules_path.mkdir()

        self._modeling_rules_path = self._pack_path / MODELING_RULES_DIR
        self._modeling_rules_path.mkdir()

        self._correlation_rules_path = self._pack_path / CORRELATION_RULES_DIR
        self._correlation_rules_path.mkdir()

        self._xsiam_dashboards_path = self._pack_path / XSIAM_DASHBOARDS_DIR
        self._xsiam_dashboards_path.mkdir()

        self._xsiam_reports_path = self._pack_path / XSIAM_REPORTS_DIR
        self._xsiam_reports_path.mkdir()

        self._triggers_path = self._pack_path / TRIGGER_DIR
        self._triggers_path.mkdir()

        self._xdrc_templates_path = self._pack_path / XDRC_TEMPLATE_DIR
        self._xdrc_templates_path.mkdir()

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
        self.author_image = File(
            tmp_path=self._pack_path / "Author_image.png", repo_path=repo.path
        )
        self.author_image.write(DEFAULT_IMAGE_BASE64)

        self._jobs_path = self._pack_path / "Jobs"
        self._jobs_path.mkdir()

        self._xsiam_layout_rules_path = self._pack_path / LAYOUT_RULES_DIR
        self._xsiam_layout_rules_path.mkdir()

        self.contributors: Optional[TextBased] = None

        self._assets_modeling_rules_path = self._pack_path / ASSETS_MODELING_RULES_DIR
        self._assets_modeling_rules_path.mkdir()

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
            self._integrations_path, name, self._repo, create_unified=create_unified
        )
        integration.build(code, yml, readme, description, changelog, image)
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
            self._scripts_path, name, self._repo, create_unified=create_unified
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

    def create_classifier(self, name, content: dict = None) -> JSONBased:
        prefix = "classifier"
        classifier = self._create_json_based(
            name, prefix, content, dir_path=self._classifiers_path
        )
        self.classifiers.append(classifier)
        return classifier

    def create_mapper(self, name, content: dict = None) -> JSONBased:
        prefix = "classifier-mapper"
        mapper = self._create_json_based(
            name, prefix, content, dir_path=self._mappers_path
        )
        self.mappers.append(mapper)
        return mapper

    def create_dashboard(self, name, content: dict = None) -> JSONBased:
        prefix = "dashboard"
        dashboard = self._create_json_based(
            name, prefix, content, dir_path=self._dashboards_path
        )
        self.dashboards.append(dashboard)
        return dashboard

    def create_incident_field(
        self, name, content: dict = None, release_notes: bool = False
    ) -> JSONBased:
        prefix = "incidentfield"
        incident_field = self._create_json_based(
            name, prefix, content, dir_path=self._incidents_field_path
        )
        if release_notes:
            # release_notes = self._create_text_based(f'{incident_field}_CHANGELOG.md',
            # dir_path=self._incidents_field_path)
            # self.incident_fields.append(release_notes)
            pass
        self.incident_fields.append(incident_field)
        return incident_field

    def create_incident_type(self, name, content: dict = None) -> JSONBased:
        prefix = "incidenttype"
        incident_type = self._create_json_based(
            name, prefix, content, dir_path=self._incident_types_path
        )
        self.incident_types.append(incident_type)
        return incident_type

    def create_indicator_field(self, name, content: dict = None) -> JSONBased:
        prefix = "incidentfield"
        indicator_field = self._create_json_based(
            name, prefix, content, dir_path=self._indicator_fields
        )
        self.indicator_fields.append(indicator_field)
        return indicator_field

    def create_indicator_type(self, name, content: dict = None) -> JSONBased:
        prefix = "reputation"
        indicator_type = self._create_json_based(
            name, prefix, content, dir_path=self._indicator_types
        )
        self.indicator_types.append(indicator_type)
        return indicator_type

    def create_generic_field(self, name, content: dict = None) -> JSONBased:
        dir_path = self._generic_fields_path / name
        dir_path.mkdir()
        prefix = "genericfield"
        generic_field = self._create_json_based(
            name, prefix, content, dir_path=dir_path
        )
        self.generic_fields.append(generic_field)
        return generic_field

    def create_generic_type(self, name, content: dict = None) -> JSONBased:
        dir_path = self._generic_types_path / name
        dir_path.mkdir()
        prefix = "generictype"
        generic_type = self._create_json_based(name, prefix, content, dir_path=dir_path)
        self.generic_types.append(generic_type)
        return generic_type

    def create_generic_module(self, name, content: dict = None) -> JSONBased:
        prefix = "genericmodule"
        generic_module = self._create_json_based(
            name, prefix, content, dir_path=self._generic_modules_path
        )
        self.generic_modules.append(generic_module)
        return generic_module

    def create_generic_definition(self, name, content: dict = None) -> JSONBased:
        prefix = "genericdefinition"
        generic_definition = self._create_json_based(
            name, prefix, content, dir_path=self._generic_definitions_path
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
            pure_name=name or str(len(self.jobs)),
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

    def create_layout(self, name, content: dict = None) -> JSONBased:
        prefix = "layout"
        layout = self._create_json_based(
            name, prefix, content, dir_path=self._layout_path
        )
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

    def create_report(self, name, content: dict = None) -> JSONBased:
        prefix = "report"
        report = self._create_json_based(
            name, prefix, content, dir_path=self._report_path
        )
        self.reports.append(report)
        return report

    def create_widget(self, name, content: dict = None) -> JSONBased:
        prefix = "widget"
        widget = self._create_json_based(
            name, prefix, content, dir_path=self._widget_path
        )
        self.widgets.append(widget)
        return widget

    def create_wizard(
        self,
        name,
        categories_to_packs: Optional[Dict[str, List[dict]]] = None,
        fetching_integrations: Optional[List[str]] = None,
        set_playbooks: Optional[List[dict]] = None,
        supporting_integrations: Optional[List[str]] = None,
    ) -> Wizard:
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

    def create_list(self, name, content: dict = None) -> JSONBased:
        prefix = "list"
        list_item = self._create_json_based(
            name, prefix, content, dir_path=self._lists_path
        )
        self.lists.append(list_item)
        return list_item

    def create_playbook(
        self,
        name: Optional[str] = None,
        yml: Optional[dict] = None,
        readme: Optional[str] = None,
    ) -> Playbook:
        if name is None:
            name = f"playbook-{len(self.playbooks)}"
        if yml is None:
            yml = {
                "tasks": {},
            }
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
        if yml is None:
            yml = {
                "tasks": {},
            }
        playbook = Playbook(
            self._test_playbooks_path, name, self._repo, is_test_playbook=True
        )
        playbook.build(
            yml,
            readme,
        )
        self.test_playbooks.append(playbook)
        return playbook

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

    def create_correlation_rule(self, name, content: dict = None) -> CorrelationRule:
        correlation_rule = CorrelationRule(
            name, self._correlation_rules_path, self.repo_path, content
        )
        self.correlation_rules.append(correlation_rule)
        return correlation_rule

    def create_xsiam_dashboard(self, name, content: dict = None) -> XSIAMDashboard:
        xsiam_dashboard = XSIAMDashboard(name, self._xsiam_dashboards_path, content)
        self.xsiam_dashboards.append(xsiam_dashboard)
        return xsiam_dashboard

    def create_xsiam_report(self, name, content: dict = None) -> XSIAMReport:
        xsiam_report = XSIAMReport(name, self._xsiam_reports_path, content)
        self.xsiam_reports.append(xsiam_report)
        return xsiam_report

    def create_trigger(self, name, content: dict = None) -> Trigger:
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

    def create_layout_rule(self, name, content: dict = None) -> LayoutRule:
        layout_rule = LayoutRule(name, self._xsiam_layout_rules_path, content)
        self.layout_rules.append(layout_rule)
        return layout_rule

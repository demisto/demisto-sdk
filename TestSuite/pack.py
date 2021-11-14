from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from TestSuite.file import File
from TestSuite.integration import Integration
from TestSuite.json_based import JSONBased
from TestSuite.playbook import Playbook
from TestSuite.script import Script
from TestSuite.secrets import Secrets
from TestSuite.text_based import TextBased


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
        # Create base pack
        self._pack_path = packs_dir / name
        self._pack_path.mkdir()
        self.path = str(self._pack_path)

        # Create repo structure
        self._integrations_path = self._pack_path / 'Integrations'
        self._integrations_path.mkdir()

        self._scripts_path = self._pack_path / 'Scripts'
        self._scripts_path.mkdir()

        self._playbooks_path = self._pack_path / 'Playbooks'
        self._playbooks_path.mkdir()

        self._test_playbooks_path = self._pack_path / 'TestPlaybooks'
        self._test_playbooks_path.mkdir()

        self._classifiers_path = self._pack_path / 'Classifiers'
        self._classifiers_path.mkdir()

        self._mappers_path = self._classifiers_path

        self._dashboards_path = self._pack_path / 'Dashboards'
        self._dashboards_path.mkdir()

        self._incidents_field_path = self._pack_path / 'IncidentFields'
        self._incidents_field_path.mkdir()

        self._incident_types_path = self._pack_path / 'IncidentTypes'
        self._incident_types_path.mkdir()

        self._indicator_fields = self._pack_path / 'IndicatorFields'
        self._indicator_fields.mkdir()

        self._indicator_types = self._pack_path / 'IndicatorTypes'
        self._indicator_types.mkdir()

        self._generic_fields_path = self._pack_path / 'GenericFields'
        self._generic_fields_path.mkdir()

        self._generic_types_path = self._pack_path / 'GenericTypes'
        self._generic_types_path.mkdir()

        self._generic_modules_path = self._pack_path / 'GenericModules'
        self._generic_modules_path.mkdir()

        self._generic_definitions_path = self._pack_path / 'GenericDefinitions'
        self._generic_definitions_path.mkdir()

        self._layout_path = self._pack_path / 'Layouts'
        self._layout_path.mkdir()

        self._report_path = self._pack_path / 'Reports'
        self._report_path.mkdir()

        self._widget_path = self._pack_path / 'Widgets'
        self._widget_path.mkdir()

        self._release_notes = self._pack_path / 'ReleaseNotes'
        self._release_notes.mkdir()

        self._lists_path = self._pack_path / 'Lists'
        self._lists_path.mkdir()

        self.secrets = Secrets(self._pack_path)

        self.pack_ignore = TextBased(self._pack_path, '.pack-ignore')

        self.readme = TextBased(self._pack_path, 'README.md')

        self.pack_metadata = JSONBased(self._pack_path, 'pack_metadata', '')

        self.author_image = File(tmp_path=self._pack_path / 'Author_image.png', repo_path=repo.path)
        self.author_image.write(DEFAULT_IMAGE_BASE64)

    def create_integration(
            self,
            name: Optional[str] = None,
            code: Optional[str] = None,
            yml: Optional[dict] = None,
            readme: Optional[str] = None,
            description: Optional[str] = None,
            changelog: Optional[str] = None,
            image: Optional[bytes] = None
    ) -> Integration:
        if name is None:
            name = f'integration_{len(self.integrations)}'
        if yml is None:
            yml = {}
        integration = Integration(self._integrations_path, name, self._repo)
        integration.build(
            code,
            yml,
            readme,
            description,
            changelog,
            image
        )
        self.integrations.append(integration)
        return integration

    def create_script(
            self,
            name: Optional[str] = None,
            yml: Optional[dict] = None,
            code: str = '',
            readme: str = '',
            description: str = '',
            changelog: str = '',
            image: bytes = b''
    ) -> Script:
        if name is None:
            name = f'script{len(self.integrations)}'
        if yml is None:
            yml = {}
        script = Script(self._scripts_path, name, self._repo)
        script.build(
            code,
            yml,
            readme,
            description,
            changelog,
            image
        )
        self.scripts.append(script)
        return script

    def create_test_script(self) -> Script:
        script = self.create_script('sample_script')
        script.create_default_script()
        return script

    def _create_json_based(
            self,
            name,
            prefix: str,
            content: dict = None,
            dir_path: Path = None
    ) -> JSONBased:
        if content is None:
            content = {}
        if dir_path:
            obj = JSONBased(dir_path, name, prefix)
        else:
            obj = JSONBased(self._pack_path, name, prefix)
        obj.write_json(content)
        return obj

    def _create_text_based(
            self,
            name,
            content: str = '',
            dir_path: Path = None
    ) -> TextBased:
        if dir_path:
            obj = TextBased(dir_path, name)
        else:
            obj = TextBased(self._pack_path, name)
        obj.write_text(content)
        return obj

    def create_classifier(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'classifier'
        classifier = self._create_json_based(name, prefix, content, dir_path=self._classifiers_path)
        self.classifiers.append(classifier)
        return classifier

    def create_mapper(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'classifier-mapper'
        mapper = self._create_json_based(name, prefix, content, dir_path=self._mappers_path)
        self.mappers.append(mapper)
        return mapper

    def create_dashboard(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'dashboard'
        dashboard = self._create_json_based(name, prefix, content, dir_path=self._dashboards_path)
        self.dashboards.append(dashboard)
        return dashboard

    def create_incident_field(
            self,
            name,
            content: dict = None,
            release_notes: bool = False
    ) -> JSONBased:
        prefix = 'incidentfield'
        incident_field = self._create_json_based(name, prefix, content, dir_path=self._incidents_field_path)
        if release_notes:
            # release_notes = self._create_text_based(f'{incident_field}_CHANGELOG.md',
            # dir_path=self._incidents_field_path)
            # self.incident_fields.append(release_notes)
            pass
        self.incident_fields.append(incident_field)
        return incident_field

    def create_incident_type(
            self,
            name,
            content: dict = None) -> JSONBased:
        prefix = 'incidenttype'
        incident_type = self._create_json_based(name, prefix, content, dir_path=self._incident_types_path)
        self.incident_types.append(incident_type)
        return incident_type

    def create_indicator_field(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'incidentfield'
        indicator_field = self._create_json_based(name, prefix, content, dir_path=self._indicator_fields)
        self.indicator_fields.append(indicator_field)
        return indicator_field

    def create_indicator_type(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'reputation'
        indicator_type = self._create_json_based(name, prefix, content, dir_path=self._indicator_types)
        self.indicator_types.append(indicator_type)
        return indicator_type

    def create_generic_field(
            self,
            name,
            content: dict = None) -> JSONBased:
        dir_path = self._generic_fields_path / name
        dir_path.mkdir()
        prefix = 'genericfield'
        generic_field = self._create_json_based(name, prefix, content, dir_path=dir_path)
        self.generic_fields.append(generic_field)
        return generic_field

    def create_generic_type(
            self,
            name,
            content: dict = None) -> JSONBased:
        dir_path = self._generic_types_path / name
        dir_path.mkdir()
        prefix = 'generictype'
        generic_type = self._create_json_based(name, prefix, content, dir_path=dir_path)
        self.generic_types.append(generic_type)
        return generic_type

    def create_generic_module(
            self,
            name,
            content: dict = None) -> JSONBased:
        prefix = 'genericmodule'
        generic_module = self._create_json_based(name, prefix, content, dir_path=self._generic_modules_path)
        self.generic_modules.append(generic_module)
        return generic_module

    def create_generic_definition(
            self,
            name,
            content: dict = None) -> JSONBased:
        prefix = 'genericdefinition'
        generic_definition = self._create_json_based(name, prefix, content, dir_path=self._generic_definitions_path)
        self.generic_definitions.append(generic_definition)
        return generic_definition

    def create_layout(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'layout'
        layout = self._create_json_based(name, prefix, content, dir_path=self._layout_path)
        self.layouts.append(layout)
        return layout

    def create_layoutcontainer(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'layoutscontainer'
        layoutcontainer = self._create_json_based(name, prefix, content, dir_path=self._layout_path)
        self.layoutcontainers.append(layoutcontainer)
        return layoutcontainer

    def create_report(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'report'
        report = self._create_json_based(name, prefix, content, dir_path=self._report_path)
        self.reports.append(report)
        return report

    def create_widget(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'widget'
        widget = self._create_json_based(name, prefix, content, dir_path=self._widget_path)
        self.widgets.append(widget)
        return widget

    def create_list(
            self,
            name,
            content: dict = None
    ) -> JSONBased:
        prefix = 'list'
        list_item = self._create_json_based(name, prefix, content, dir_path=self._lists_path)
        self.lists.append(list_item)
        return list_item

    def create_playbook(
            self,
            name: Optional[str] = None,
            yml: Optional[dict] = None,
            readme: Optional[str] = None,
    ) -> Playbook:
        if name is None:
            name = f'playbook-{len(self.playbooks)}'
        if yml is None:
            yml = {}
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
            name = f'playbook-{len(self.test_playbooks)}'
        if yml is None:
            yml = {}
        playbook = Playbook(self._test_playbooks_path, name, self._repo, is_test_playbook=True)
        playbook.build(
            yml,
            readme,
        )
        self.test_playbooks.append(playbook)
        return playbook

    def create_release_notes(self, version: str, content: str = '', is_bc: bool = False):
        rn = self._create_text_based(f'{version}.md', content, dir_path=self._release_notes)
        self.release_notes.append(rn)
        if is_bc:
            self.create_release_notes_config(version, {'breakingChanges': True})
        return rn

    def create_release_notes_config(self, version: str, content: dict):
        rn_config = self._create_json_based(f'{version}', '', content, dir_path=self._release_notes)
        self.release_notes_config.append(rn_config)
        return rn_config

    def create_doc_file(self, name: str = 'image') -> File:
        doc_file_dir = self._pack_path / 'doc_files'
        doc_file_dir.mkdir()
        return File(doc_file_dir / f'{name}.png', self._repo.path)

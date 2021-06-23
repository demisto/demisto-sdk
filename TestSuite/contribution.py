import shutil
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import LAYOUT, LAYOUTS_CONTAINER
from TestSuite.integration import Integration
from TestSuite.json_based import JSONBased
from TestSuite.playbook import Playbook
from TestSuite.script import Script
from TestSuite.text_based import TextBased


class Contribution:
    """A class that mocks a contribution zip file downloaded from a demisto server

    Note:
        Do not include the `self` parameter in the ``Args`` section.

    Args:
        name: name of the contribution (used in metadata.json file)

    Attributes:
        path (str): A path to the contribution zip file.
        integrations: A list contains any created integration
        scripts:  A list contains any created Script

    """

    def __init__(self, tmpdir: Path, name: str, repo):
        # Initiate lists:
        self._repo = repo
        self.repo_path = repo.path
        self.target_dir = tmpdir
        self.integrations: List[Integration] = list()
        self.scripts: List[Script] = list()
        self.playbooks: List[Playbook] = list()
        self.classifiers: List[JSONBased] = list()
        self.mapper: List[JSONBased] = list()
        self.dashboards: List[JSONBased] = list()
        self.incident_types: List[JSONBased] = list()
        self.incident_field: List[JSONBased] = list()
        self.indicator_field: List[JSONBased] = list()
        self.layouts: List[JSONBased] = list()
        self.layouts_containers: List[JSONBased] = list()

        self.name = name
        self.created_zip_filepath = ''

        # Create contribution structure
        self._integrations_path = self.target_dir / 'integration'
        self._integrations_path.mkdir()

        self._scripts_path = self.target_dir / 'automation'
        self._scripts_path.mkdir()

        self._playbooks_path = self.target_dir / 'playbook'
        self._playbooks_path.mkdir()

        self._classifiers_path = self.target_dir / 'classifier'
        self._classifiers_path.mkdir()

        self._mappers_path = self._classifiers_path

        self._dashboards_path = self.target_dir / 'dashboard'
        self._dashboards_path.mkdir()

        self._incident_fields_path = self.target_dir / 'incidentfield'
        self._incident_fields_path.mkdir()

        self._incident_types_path = self.target_dir / 'incidenttype'
        self._incident_types_path.mkdir()

        self._indicator_fields_path = self.target_dir / 'indicatorfield'
        self._indicator_fields_path.mkdir()

        self._reports_path = self.target_dir / 'report'
        self._reports_path.mkdir()

        self._reputations_path = self.target_dir / 'reputation'
        self._reputations_path.mkdir()

        self._layouts_path = self.target_dir / 'layout'
        self._layouts_path.mkdir()

        self._layoutscontainer_path = self.target_dir / 'layoutscontainer'
        self._layoutscontainer_path.mkdir()

    def create_integration(
            self,
            name: Optional[str] = None,
            unified: Optional[bool] = True
    ):
        if name is None:
            name = f'integration{len(self.integrations)}'
        integration = Integration(self._integrations_path, name, self._repo, unified)
        integration.create_default_integration()
        self.integrations.append(integration)
        return integration

    def create_script(
            self,
            name: Optional[str] = None,
            unified: Optional[bool] = True):
        if name is None:
            name = f'script{len(self.scripts)}'
        script = Script(self._scripts_path, name, self._repo, unified)
        script.create_default_script()
        self.scripts.append(script)
        return script

    def create_playbook(
            self,
            name: Optional[str] = None):
        if name is None:
            name = f'playbook{len(self.playbooks)}'
        playbook = Playbook(self._playbooks_path, name, self._repo)
        playbook.create_default_playbook()
        self.playbooks.append(playbook)
        return playbook

    def create_test_script(self):
        script = self.create_script('sample_script')
        script.create_default_script()
        return script

    def _create_json_based(
            self,
            name,
            prefix: str,
            content: dict = None,
            dir_path: Path = None
    ):
        if content is None:
            content = {}
        if dir_path:
            obj = JSONBased(dir_path, name, prefix)
        else:
            obj = JSONBased(self.target_dir, name, prefix)
        obj.write_json(content)
        return obj

    def _create_text_based(
            self,
            name,
            content: str = '',
            dir_path: Path = None
    ):
        if dir_path:
            obj = TextBased(dir_path, name)
        else:
            obj = TextBased(self.target_dir, name)
        obj.write_text(content)
        return obj

    def create_classifier(
            self,
            name,
            content: dict = None
    ):
        prefix = 'classifier'
        classifier = self._create_json_based(name, prefix, content, dir_path=self._classifiers_path)
        self.classifiers.append(classifier)
        return classifier

    def create_mapper(
            self,
            name,
            content: dict = None
    ):
        prefix = 'classifier-mapper'
        mapper = self._create_json_based(name, prefix, content, dir_path=self._mappers_path)
        self.mapper.append(mapper)
        return mapper

    def create_dashboard(
            self,
            name,
            content: dict = None
    ):
        prefix = 'dashboard'
        dashboard = self._create_json_based(name, prefix, content, dir_path=self._dashboards_path)
        self.dashboards.append(dashboard)
        return dashboard

    def create_layout(
            self,
            name,
            content: dict = None
    ):
        prefix = LAYOUT
        layout = self._create_json_based(name, prefix, content, dir_path=self._layouts_path)
        self.layouts.append(layout)
        return layout

    def create_layoutscontainer(
            self,
            name,
            content: dict = None
    ):
        prefix = LAYOUTS_CONTAINER
        layoutscontainer = self._create_json_based(name, prefix, content, dir_path=self._layoutscontainer_path)
        self.layouts_containers.append(layoutscontainer)
        return layoutscontainer

    def create_incident_field(
            self,
            name,
            content: dict = None,
            release_notes: bool = False
    ):
        prefix = 'incident-field'
        incident_field = self._create_json_based(name, prefix, content, dir_path=self._incident_fields_path)
        if release_notes:
            release_notes_file = self._create_text_based(f'{incident_field}_CHANGELOG.md',
                                                         dir_path=self._incident_fields_path)
            self.incident_field.append(release_notes_file)
        self.incident_field.append(incident_field)
        return incident_field

    def create_incident_type(
            self,
            name,
            content: dict = None):
        prefix = 'incident-type'
        incident_type = self._create_json_based(name, prefix, content, dir_path=self._incident_types_path)
        self.incident_types.append(incident_type)
        return incident_type

    def create_indicator_field(
            self,
            name,
            content: dict = None
    ):
        prefix = 'incident-field'
        indicator_field = self._create_json_based(name, prefix, content, dir_path=self._indicator_fields_path)
        self.indicator_field.append(indicator_field)

    def create_metadata_for_zip(self):
        fake_metadata = {
            "name": self.name,
            "description": "",
            "updated": "0001-01-01T00:00:00Z",
            "support": "internalContribution",
            "author": "Who Cares",
            "authorImage": "",
            "supportDetails": {
                "url": "",
                "email": "madeup@madeup.com"
            }
        }
        self.metadata = JSONBased(self.target_dir, 'metadata', '')
        self.metadata.write_json(fake_metadata)

    def create_zip(self, zip_dst: Optional[Path] = None, del_src_files: bool = True):
        self.create_classifier(name='fakeclassifier')
        self.create_dashboard(name='fakedashboard')
        self.create_layoutscontainer(name='fakelayoutscontainer')
        self.create_layout(name='fakelayout')
        self.create_incident_field(name='fakeincidentfield')
        self.create_incident_type(name='fakeincidenttype')
        self.create_indicator_field(name='fakeindicatorfield')
        self.create_mapper(name='fakemapper')
        self.create_integration()
        self.create_script()
        self.create_playbook(name='playbook-SamplePlaybook')
        self.create_metadata_for_zip()
        if zip_dst:
            self.created_zip_filepath = shutil.make_archive(
                str(zip_dst / self.name), 'zip', self.target_dir
            )
        else:
            self.created_zip_filepath = shutil.make_archive(
                str(self.target_dir.parent / self.name), 'zip', self.target_dir
            )
        if del_src_files:
            shutil.rmtree(self.target_dir)
